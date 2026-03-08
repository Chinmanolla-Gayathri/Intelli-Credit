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

# Define the expected format for human approval
class DecisionRecord(BaseModel):
    company_name: str
    risk_score: float
    status: str
    ai_analysis: str
    extracted_metrics: dict

# 2. Configure Gemini
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. Load ML Models and Meta Data
print("Loading ML Models...")
with open("intelli_credit_clf_v2.pkl", "rb") as f:
    clf_v2 = pickle.load(f)

with open("intelli_credit_reg.pkl", "rb") as f:
    reg = pickle.load(f)

with open("intelli_credit_meta.json", "r") as f:
    meta = json.load(f)

# THE LATE-NIGHT HACK: Extract exact columns for BOTH mismatched models!
CLF_COLS = list(clf_v2.feature_names_in_)
REG_COLS = list(reg.feature_names_in_)
THRESHOLD = meta.get("decision_threshold", 0.25)

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
    """The ML Engine: Hacked to support mismatched teammate models!"""
    # Create two separate dataframes so neither model panics!
    row_clf = {col: extracted_data.get(col, 0) for col in CLF_COLS}
    row_reg = {col: extracted_data.get(col, 0) for col in REG_COLS}
    
    X_clf = pd.DataFrame([row_clf], columns=CLF_COLS)
    X_reg = pd.DataFrame([row_reg], columns=REG_COLS)

    # Hard reject check (Look directly at what Gemini extracted!)
    hard_reject_reasons = []
    if extracted_data.get("circular_trading_flag", 0) == 1:
        hard_reject_reasons.append("Circular trading detected")
    if extracted_data.get("emi_bounce_count", 0) >= 8:
        hard_reject_reasons.append(f"EMI bounce count critically high")

    if hard_reject_reasons:
        return {
            "decision": "HARD REJECT", 
            "risk_score": 100.0, 
            "explanation": "Rejected at pre-screening: " + "; ".join(hard_reject_reasons),
            "default_probability_pct": 100.0
        }

    # ML scoring: Feed the separate dataframes to their respective models
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

    return {
        "decision": decision,
        "risk_score": round(risk_score, 1),
        "explanation": f"{decision} — Risk Score: {risk_score:.1f}/100. Default probability: {default_prob*100:.1f}%.",
        "default_probability_pct": round(default_prob * 100, 1)
    }

# 5. Main Analysis Route
@app.post("/api/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    field_notes: str = Form(default="")
):
    combined_raw_text = f"--- Field Notes ---\n{field_notes}\n\n"
    
    for file in files:
        if file.filename.endswith('.pdf'):
            content = await file.read()
            combined_raw_text += f"\n--- Content from {file.filename} ---\n{extract_text_from_pdf(content)}"
        elif file.filename.endswith('.zip'):
            content = await file.read()
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for zinfo in z.infolist():
                    if zinfo.filename.endswith('.pdf'):
                        with z.open(zinfo) as pdf_file:
                            combined_raw_text += f"\n--- Content from {zinfo.filename} ---\n{extract_text_from_pdf(pdf_file.read())}"
            
    masked_text = mask_sensitive_data(combined_raw_text)
    
    prompt = f"""
    You are a data extraction AI for a bank. Read the following text and extract financial metrics.
    If a value is not found, output 0.
    
    Text: "{masked_text}"
    
    Return ONLY a raw JSON object with these exact keys (no markdown formatting, no text before or after).
    Ensure the JSON maps to typical financial metrics found in the text. Try to find values like:
    {{
        "annual_revenue_inr": <number>,
        "credit_score": <number>,
        "gstr1_vs_3b_mismatch": <number between 0 and 1>,
        "emi_bounce_count": <number>,
        "circular_trading_flag": <1 if detected, 0 if not>,
        "debt_to_equity": <number>,
        "interest_coverage_ratio": <number>,
        "company_name": "<string>"
    }}
    """
    
    response = model.generate_content(prompt)
    json_text = response.text.replace("```json", "").replace("```", "").strip()
    
    try:
        extracted_data = json.loads(json_text)
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        extracted_data = {} 
        
    company_name = extracted_data.get("company_name", "Unknown Company")
    
    # --- OPTION A: AI Sentiment Analysis ---
    sentiment_prompt = f"""
    Analyze the general market sentiment for a company named '{company_name}'. 
    Based on standard business knowledge, classify the sentiment as strictly POSITIVE, NEGATIVE, or NEUTRAL.
    Return ONLY ONE WORD: POSITIVE, NEGATIVE, or NEUTRAL.
    """
    try:
        sentiment_response = model.generate_content(sentiment_prompt)
        sentiment = sentiment_response.text.strip().upper()
    except Exception as e:
        print(f"Sentiment Analysis Error: {e}")
        sentiment = "NEUTRAL"
    
    sentiment_modifier = 0
    if "POSITIVE" in sentiment:
        sentiment_modifier = -5.0 # Lowers risk
    elif "NEGATIVE" in sentiment:
        sentiment_modifier = 5.0  # Increases risk
    # ---------------------------------------
        
    ml_results = predict_risk(extracted_data)
    
    # Apply the sentiment modifier to the ML risk score
    final_risk_score = float(np.clip(ml_results["risk_score"] + sentiment_modifier, 0, 100))
    final_explanation = f"{ml_results['explanation']} Market Sentiment: {sentiment} (Score adjusted by {sentiment_modifier})."
    
    return {
        "status": "success",
        "masked_text": masked_text, 
        "ai_analysis": final_explanation,
        "mock_risk_score": final_risk_score,
        "mock_decision": ml_results["decision"],
        "default_prob": ml_results.get("default_probability_pct", 0),
        "company_name": company_name,
        "extracted_metrics": extracted_data
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
    # Sort by date descending so most recent decisions appear first
    records = list(history_collection.find({}, {"_id": 0}).sort("date", -1).limit(50))
    return {"status": "success", "data": records}

# 8. Dashboard Stats Route (OPTION C)
@app.get("/api/stats")
def get_stats():
    total_appraisals = history_collection.count_documents({})
    
    if total_appraisals == 0:
        return {"status": "success", "data": {"total": 0, "approval_rate": 0, "high_risk": 0}}
        
    # Count how many were approved (case-insensitive search for "Approve")
    approved_count = history_collection.count_documents({"status": {"$regex": "Approve", "$options": "i"}})
    
    # Count how many had a risk score >= 75
    high_risk_count = history_collection.count_documents({"risk_score": {"$gte": 75}})
    
    approval_rate = round((approved_count / total_appraisals) * 100, 1)
    
    return {
        "status": "success",
        "data": {
            "total": total_appraisals,
            "approval_rate": approval_rate,
            "high_risk": high_risk_count
        }
    }
