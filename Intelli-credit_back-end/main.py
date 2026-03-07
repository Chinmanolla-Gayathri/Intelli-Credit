from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import re
import PyPDF2
import io
import os
from dotenv import load_dotenv

# Load the secret key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

def mask_sensitive_data(text: str) -> str:
    """The Shield: Masks PII"""
    text = re.sub(r"\b\d{10}\b", "[MASKED_ACCOUNT]", text)
    text = re.sub(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[MASKED_PAN]", text, flags=re.IGNORECASE)
    return text

def extract_text_from_pdf(file_bytes) -> str:
    """Helper function to read PDF bytes and extract text"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        # Just grab the first few pages for the prototype to save time/tokens
        num_pages = min(3, len(pdf_reader.pages))
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

@app.post("/api/analyze")
async def analyze(files: list[UploadFile] = File(...)):
    print(f"Received {len(files)} files!")
    
    combined_raw_text = ""
    
    # 1. Process each uploaded file
    for file in files:
        if file.filename.endswith('.pdf'):
            print(f"Reading PDF: {file.filename}")
            # Read the file contents into memory
            content = await file.read()
            # Extract the text
            extracted_text = extract_text_from_pdf(content)
            combined_raw_text += f"\n--- Content from {file.filename} ---\n{extracted_text}"
            
    # Fallback if no text was found (e.g., they uploaded empty files)
    if not combined_raw_text.strip():
        combined_raw_text = "Alert: No readable text found in uploaded documents. Customer with account 1234567890 has PAN ABCDE1234F is applying for a loan."
        
    # 2. Apply the Mask
    masked_text = mask_sensitive_data(combined_raw_text)
    
    # 3. The Prompt to Gemini (Sending the actual document text!)
    prompt = f"""
    You are an expert Indian Corporate Credit Officer. 
    Read this secure, masked document data: 
    "{masked_text}"
    
    Write a 2-sentence professional assessment acknowledging the loan request and mentioning one key fact found in the documents.
    """
    
    # 4. Generate the response
    response = model.generate_content(prompt)
    ai_text = response.text
    
    return {
        "status": "success",
        "masked_text_preview": masked_text[:200] + "...", # Just returning a snippet so we don't crash the browser alert
        "ai_analysis": ai_text,
        "mock_risk_score": 82,
        "mock_decision": "Approved with 12% Interest"
    }
