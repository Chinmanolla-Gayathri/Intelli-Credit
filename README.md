🚀 Intelli-Credit: AI-Powered Enterprise Credit Decisioning Engine
Intelli-Credit is an end-to-end automated credit appraisal platform designed to help banks and NBFCs perform deep-dive risk analysis in seconds. It bridges the gap between unstructured financial documents (PDFs) and structured data (CSVs) using a dual-layered AI & ML pipeline.

🌟 Key Features (Gap Fixes)
Multi-Modal Data Ingestion: Natively parses unstructured Audit PDFs and structured CSV Bank Statements/GST logs using PyPDF2 and Pandas.

The 5 C’s of Credit: Automatically synthesizes Character, Capacity, Capital, Collateral, and Conditions into a professional Banking CAM report.

Hybrid Risk Engine: Combines a Google Gemini-driven feature extractor with a Scikit-Learn Random Forest Regressor for precision scoring.

Digital Credit Research Agent: Simulates a web-crawl of MCA filings and e-Courts litigation to adjust risk scores based on real-time market sentiment.

Enterprise Data Lake Sync: Includes a dedicated endpoint for Databricks synchronization to simulate large-scale data ingestion.

🛠️ Tech Stack
Frontend: Next.js (TypeScript), Tailwind CSS, Lucide React

Backend: FastAPI (Python), Uvicorn

AI/ML: Google Gemini 2.0 Flash, Scikit-Learn (Random Forest)

Database: MongoDB (for Appraisal History)

Data Processing: Pandas, PyPDF2

🚀 Quick Start Instructions
1. Prerequisites
Python 3.9+

Node.js 18+

A Google Gemini API Key

A MongoDB Connection String

2. Backend Setup
Bash
# Navigate to root
cd Intelli-Credit

# Install dependencies
pip install fastapi uvicorn google-generativeai pypdf2 pandas numpy python-dotenv pymongo

# Create a .env file and add your secrets
echo "GEMINI_API_KEY=your_key_here" > .env
echo "MONGO_URI=your_mongodb_uri_here" >> .env

# Start the server
uvicorn main:app --reload
3. Frontend Setup
Bash
# Navigate to frontend folder
cd Intelli-credit_front-end

# Install dependencies
npm install

# Start the development server
npm run dev
📂 How to Test (Demo Guide)
To see the engine in full effect and bypass the "46.1" score limit:

Upload Multiple Files: Select both the Nexus_Tech_Audit.pdf and Nexus_Tech_Bank_Statement.csv simultaneously.

Add Field Notes: Enter a brief observation (e.g., "Facility visit confirmed 100% operation").

Analyze: The engine will map 32 corporate data points to the ML model and generate a dynamic risk score.

Audit Trail: Click "Download Masked Data" to prove the system successfully merged the PDF and CSV data streams.

👥 Contributors
Gayathri Chinmanolla - Lead Backend Architect & AI Integration
Prakarsha Kondour & Shreya Pitla - ML Model Development & Frontend UI
