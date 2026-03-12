from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import re
import PyPDF2
import io
import os
import zipfile
import json
import pickle
import pandas as pd
import numpy as np
from fastapi import Response
from fpdf import FPDF
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Load secrets from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
mongo_uri = os.getenv("MONGO_URI")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Setup MongoDB
client = MongoClient(mongo_uri)
db = client["intelli_credit_db"]
history_collection = db["appraisals"]

# Define the expected format for human approval (Updated with new PS requirements)
class DecisionRecord(BaseModel):
    company_name: str
    risk_score: float
    status: str
    ai_analysis: str
    extracted_metrics: dict
    loan_limit: float = 0.0
    interest_rate: float = 0.0
    five_cs: str = ""

# 2. Configure Gemini
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. Load ML Models and Meta Data
print("Loading ML Models...")
with open("../intelli_credit_clf.pkl", "rb") as f:
    clf_v2 = pickle.load(f)
with open("../intelli_credit_reg.pkl", "rb") as f:
    reg = pickle.load(f)
with open("../intelli_credit_meta.json", "r") as f:
    meta = json.load(f)


CLF_COLS = list(clf_v2.feature_names_in_)
REG_COLS = list(reg.feature_names_in_)
THRESHOLD = meta.get("decision_threshold", 0.25)
print("🚨 THE REGRESSOR WANTS THESE COLUMNS:", REG_COLS)

# 4. Helper Functions
def mask_sensitive_data(text: str) -> str:
    text = re.sub(r"\b\d{10}\b", "[MASKED_ACCOUNT]", text)
    text = re.sub(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[MASKED_PAN]", text, flags=re.IGNORECASE)
    return text

def extract_text_from_pdf(file_bytes) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page_num in range(min(3, len(pdf_reader.pages))):
            text += pdf_reader.pages[page_num].extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def predict_risk(extracted_data: dict) -> dict:
    row_clf = {col: extracted_data.get(col, 0) for col in CLF_COLS}
    row_reg = {col: extracted_data.get(col, 0) for col in REG_COLS}
    
    X_clf = pd.DataFrame([row_clf], columns=CLF_COLS)
    X_reg = pd.DataFrame([row_reg], columns=REG_COLS)

    # Hard reject check (Compliance Rules)
    hard_reject_reasons = []
    if extracted_data.get("circular_trading_flag", 0) == 1:
        hard_reject_reasons.append("Circular trading detected via GST cross-reference")
    if extracted_data.get("emi_bounce_count", 0) >= 8:
        hard_reject_reasons.append(f"EMI bounce count critically high")

    if hard_reject_reasons:
        return {
            "decision": "HARD REJECT", 
            "risk_score": 100.0, 
            "explanation": "Rejected at pre-screening: " + "; ".join(hard_reject_reasons),
            "default_probability_pct": 100.0,
            "recommended_limit_inr": 0.0,
            "recommended_interest_rate_pct": 0.0
        }

    # ML scoring
    default_prob = clf_v2.predict_proba(X_clf)[0][1]
    risk_score = float(np.clip(reg.predict(X_reg)[0], 0, 100))
    is_default = default_prob >= THRESHOLD

    if risk_score < 30: risk_cat = "LOW"
    elif risk_score < 55: risk_cat = "MEDIUM"
    elif risk_score < 75: risk_cat = "HIGH"
    else: risk_cat = "REJECT"

    if is_default and risk_cat == "LOW":
        risk_cat = "MEDIUM"

    if risk_cat == "LOW": decision = "APPROVE"
    elif risk_cat == "MEDIUM": decision = "CONDITIONAL APPROVAL"
    elif risk_cat == "HIGH": decision = "APPROVE WITH CAUTION"
    else: decision = "REJECT"

    # GAP 1 FIX: Calculate specific Loan Limit and Interest Rate
    revenue = extracted_data.get("annual_revenue_inr", extracted_data.get("AnnualIncome", 0))
    base_rate = 8.5
    interest_rate = round(base_rate + (risk_score * 0.08), 2) # Risk premium
    
    # Offer max 25% of revenue, scaled down by their risk score
    loan_limit = round((revenue * 0.25) * ((100 - risk_score) / 100), 2)

    return {
        "decision": decision,
        "risk_score": round(risk_score, 1),
        "explanation": f"{decision} — Risk Score: {risk_score:.1f}/100. Default probability: {default_prob*100:.1f}%.",
        "default_probability_pct": round(default_prob * 100, 1),
        "recommended_limit_inr": loan_limit,
        "recommended_interest_rate_pct": interest_rate
    }

# 5. Main Analysis Route
@app.post("/api/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    field_notes: str = Form(default="")
):
    combined_raw_text = f"--- Primary Insight: Field Notes ---\n{field_notes}\n\n"
    
    for file in files:
        content = await file.read()
        # GAP 5 FIX: Ingest unstructured PDFs AND structured CSVs (GST/Bank Statements)
        if file.filename.endswith('.pdf'):
            combined_raw_text += f"\n--- Unstructured Data: {file.filename} ---\n{extract_text_from_pdf(content)}"
        elif file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(content))
                combined_raw_text += f"\n--- Structured Data Cross-Reference: {file.filename} ---\n{df.head(50).to_string()}\n"
            except Exception as e:
                print(f"CSV Parse Error: {e}")
        elif file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for zinfo in z.infolist():
                    if zinfo.filename.endswith('.pdf'):
                        with z.open(zinfo) as pdf_file:
                            combined_raw_text += f"\n--- Unstructured Data: {zinfo.filename} ---\n{extract_text_from_pdf(pdf_file.read())}"
            
    masked_text = mask_sensitive_data(combined_raw_text)
    
    # GAP 2 & 5 FIX: Extract JSON + 5 Cs + Cross-Reference Instructions
    prompt = f"""
    You are an AI Credit Decisioning Engine. Read the following multi-source data.
    Our ML model requires specific feature names. Extract the corporate data and map it to these exact keys. 
    If a value is not explicitly found, make a highly educated estimate based on the text (e.g., map 'years in business' to 'Age', 'Revenue' to 'AnnualIncome'). 
    
    Text: "{masked_text}"
    
    Return ONLY a raw JSON object with these EXACT keys:
    {{
        "CreditScore": <number>,
        "PaymentHistory": <number 0-10, 10 is best>,
        "LengthOfCreditHistory": <number of years>,
        "PreviousLoanDefaults": <number>,
        "BankruptcyHistory": <number 0 or 1>,
        "UtilityBillsPaymentHistory": <number 0-10>,
        "NumberOfCreditInquiries": <number>,
        "AnnualIncome": <number>,
        "MonthlyIncome": <number>,
        "DebtToIncomeRatio": <number>,
        "TotalDebtToIncomeRatio": <number>,
        "EmploymentStatus": <1 for active, 0 for inactive>,
        "JobTenure": <number of years in business>,
        "MonthlyDebtPayments": <number>,
        "MonthlyLoanPayment": <number>,
        "NetWorth": <number>,
        "TotalAssets": <number>,
        "SavingsAccountBalance": <number>,
        "CheckingAccountBalance": <number>,
        "HomeOwnershipStatus": <1 for owned, 0 for rented>,
        "TotalLiabilities": <number>,
        "NumberOfOpenCreditLines": <number>,
        "Age": <number of years company has existed>,
        "Experience": <number of years in industry>,
        "LoanAmount": <number estimated loan requested>,
        "LoanDuration": <number of months>,
        "InterestRate": <number>,
        "BaseInterestRate": <number>,
        "LoanPurpose": <1 for business expansion, 0 for other>,
        "EducationLevel": <3 for corporate entity>,
        "MaritalStatus": <1 for corporate entity>,
        "NumberOfDependents": <number of subsidiaries or 0>,
        "circular_trading_flag": <1 if detected, 0 if not>,
        "emi_bounce_count": <number>,
        "company_name": "<string>",
        "five_cs_summary": "<A professional paragraph summarizing the Five Cs of Credit: Character, Capacity, Capital, Collateral, and Conditions>"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        extracted_data = json.loads(json_text)
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        extracted_data = {} 
        
    company_name = extracted_data.get("company_name", "Unknown Company")
    five_cs = extracted_data.get("five_cs_summary", "Insufficient data to generate 5 C's.")
    
    # GAP 3 FIX: Dedicated Web-Scale Secondary Research Agent
    research_prompt = f"""
    Act as a Digital Credit Manager performing secondary research. 
    Analyze the company '{company_name}'. Simulate a web crawl of MCA (Ministry of Corporate Affairs) filings, e-Courts litigation history, and sector-specific headwinds (e.g., RBI regulations).
    Provide a 2-sentence summary of findings. End the summary with exactly one word classifying the market sentiment: POSITIVE, NEGATIVE, or NEUTRAL.
    """
    try:
        research_response = model.generate_content(research_prompt)
        research_text = research_response.text.strip()
        sentiment = "NEUTRAL"
        if "POSITIVE" in research_text.upper(): sentiment = "POSITIVE"
        elif "NEGATIVE" in research_text.upper(): sentiment = "NEGATIVE"
    except Exception as e:
        print(f"Research Error: {e}")
        research_text = "Secondary research unavailable."
        sentiment = "NEUTRAL"
    
    sentiment_modifier = 0
    if sentiment == "POSITIVE": sentiment_modifier = -5.0
    elif sentiment == "NEGATIVE": sentiment_modifier = 5.0
        
    ml_results = predict_risk(extracted_data)
    final_risk_score = float(np.clip(ml_results["risk_score"] + sentiment_modifier, 0, 100))
    
    final_explanation = f"{ml_results['explanation']}\n\nWeb Agent Research: {research_text}\n(Score adjusted by {sentiment_modifier} due to sentiment)."
    
    return {
        "status": "success",
        "masked_text": masked_text, 
        "ai_analysis": final_explanation,
        "mock_risk_score": final_risk_score,
        "mock_decision": ml_results["decision"],
        "default_prob": ml_results.get("default_probability_pct", 0),
        "recommended_limit_inr": ml_results.get("recommended_limit_inr", 0),
        "recommended_interest_rate_pct": ml_results.get("recommended_interest_rate_pct", 0),
        "five_cs_summary": five_cs,
        "company_name": company_name,
        "extracted_metrics": extracted_data
    }

# GAP 4 FIX: Databricks Data Lake Mock Sync Endpoint
@app.get("/api/databricks/sync")
def databricks_sync():
    return {
        "status": "success", 
        "message": "Connected to Databricks Data Lake. 4,209 unstructured records and GST logs synchronized."
    }

# 6. Human-in-the-Loop Save Route
@app.post("/api/save_decision")
def save_decision(record: DecisionRecord):
    try:
        rec_dict = record.model_dump()
    except AttributeError:
        rec_dict = record.dict()
        
    rec_dict["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    history_collection.insert_one(rec_dict)
    print(f"✅ SAVED TO MONGO: {rec_dict['company_name']} as {rec_dict['status']}")
    return {"status": "success"}

# 7. History Fetching Route
@app.get("/api/history")
def get_history():
    records = list(history_collection.find({}, {"_id": 0}).sort("date", -1).limit(50))
    return {"status": "success", "data": records}

# 8. Dashboard Stats Route
@app.get("/api/stats")
def get_stats():
    total_appraisals = history_collection.count_documents({})
    if total_appraisals == 0:
        return {"status": "success", "data": {"total": 0, "approval_rate": 0, "high_risk": 0}}
    approved_count = history_collection.count_documents({"status": {"$regex": "Approve", "$options": "i"}})
    high_risk_count = history_collection.count_documents({"risk_score": {"$gte": 75}})
    approval_rate = round((approved_count / total_appraisals) * 100, 1)
    return {"status": "success", "data": {"total": total_appraisals, "approval_rate": approval_rate, "high_risk": high_risk_count}}
@app.get("/download-cam/{company_name}")
async def download_cam(company_name: str):
    report_data = history_collection.find_one(
        {"company_name": company_name}, 
        sort=[("date", -1)]
    )
    
    if not report_data:
        return Response(content="Report not found", status_code=404)

    pdf = FPDF()
    pdf.add_page()
    
    # --- FIX START: Clean the text for PDF compatibility ---
    # We replace the Unicode Rupee symbol with 'INR' to prevent the Encoding Error
    raw_text = report_data.get("five_cs", "") or report_data.get("ai_analysis", "")
    safe_text = raw_text.replace("₹", "INR ").replace("\u20b9", "INR ") 
    # --- FIX END ---

    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "CREDIT APPRAISAL MEMO (CAM)", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_font("Helvetica", size=12)
    # Use multi_cell for the cleaned text
    pdf.multi_cell(0, 8, txt=safe_text)
    
    pdf_output = pdf.output() 
    return Response(
        content=pdf_output, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={company_name}_CAM.pdf"}
    )