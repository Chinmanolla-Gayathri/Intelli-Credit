"use client"

import { useState } from "react"
import { Sparkles, Loader2, CheckCircle2, AlertTriangle, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { FileUpload } from "./file-upload"
import { FieldNotes } from "./field-notes"

export function NewAppraisalView() {
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [result, setResult] = useState<any>(null)
  const [fieldNotes, setFieldNotes] = useState("")

  const handleDatabricksSync = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/databricks/sync")
      if (!response.ok) throw new Error("Failed to sync with Databricks")
      const data = await response.json()
      alert(data?.message || "Databricks sync complete!")
    } catch (error) {
      console.error("Databricks sync failed:", error)
      alert("Failed to sync with Databricks. Please try again.")
    }
  }

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      alert("Please upload at least one document first!");
      return;
    }

    setIsLoading(true)
    setResult(null) 
    
    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => {
         formData.append("files", file);
      });
      formData.append("fieldNotes", fieldNotes);

      const response = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        body: formData
      });
      
      const data = await response.json();
      setResult(data);
      
    } catch (error) {
      console.error("Connection failed:", error);
      alert("Uh oh! Make sure your Python server is running.");
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownloadMaskedData = () => {
    if (!result || !result.masked_text) {
      alert("No masked data available.")
      return
    }
    const blob = new Blob([result.masked_text], { type: "text/plain;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "masked_data.txt"
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  // UPDATED: This function now fetches the actual PDF from your backend
  const handleDownloadPDF = async () => {
    if (!result || !result.company_name) {
      alert("Please analyze and SAVE the decision first to generate the official PDF.");
      return;
    }

    try {
      // We call the dedicated PDF endpoint we created in main.py
      const response = await fetch(`http://localhost:8000/download-cam/${encodeURIComponent(result.company_name)}`);
      
      if (!response.ok) {
        throw new Error("PDF generation failed. Ensure you have clicked 'Approve' or 'Reject' to save the data first.");
      }

      // 1. Get the response as a Blob (Binary Large Object)
      const blob = await response.blob();
      
      // 2. Create a local URL for the PDF blob
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      
      // 3. Trigger the browser download
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${result.company_name}_CAM_Report.pdf`);
      document.body.appendChild(link);
      link.click();
      
      // 4. Cleanup
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("PDF Download Error:", error);
      alert("Failed to download PDF. Try saving the decision first.");
    }
  };

  const handleFinalDecision = async (humanDecision: string) => {
    if (humanDecision === "Discard") {
      setResult(null)
      return
    }

    if (!result) return

    const payload = {
      company_name: result.company_name || "Unknown Company",
      risk_score: Number(result.mock_risk_score),
      status: humanDecision,
      ai_analysis: result.ai_analysis,
      extracted_metrics: result.extracted_metrics || {},
      loan_limit: result.recommended_limit_inr,
      interest_rate: result.recommended_interest_rate_pct,
      five_cs: result.five_cs_summary,
    }

    try {
      const response = await fetch("http://localhost:8000/api/save_decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error("Failed to save decision")

      alert("Decision Saved! You can now download the official PDF report.");
    } catch (error) {
      console.error("Error saving decision:", error)
      alert("Failed to save decision to the database.");
    }
  }

  const formatCurrencyInr = (value: number | undefined | null) => {
    if (value == null || Number.isNaN(Number(value))) return "₹0"
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(value))
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Generate Credit Appraisal Memo (CAM)</h2>
          <p className="mt-1 text-sm text-muted-foreground">Automate loan decisioning with AI-powered document analysis</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleDatabricksSync}>Sync with Databricks</Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Document Upload</CardTitle>
            <CardDescription>Upload financial statements and bank logs</CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload onFilesSelected={setSelectedFiles} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analysis Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3 text-sm">
              <span className="text-muted-foreground">Documents</span>
              <span className="font-semibold">{selectedFiles.length} files</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Qualitative Assessment</CardTitle></CardHeader>
        <CardContent><FieldNotes value={fieldNotes} onChange={setFieldNotes} /></CardContent>
      </Card>

      <div className="flex items-center justify-end gap-4 pt-2">
        <Button onClick={handleAnalyze} disabled={isLoading} className="min-w-[200px] gap-2">
          {isLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Analyzing...</> : <><Sparkles className="h-4 w-4" /> Analyze & Generate CAM</>}
        </Button>
      </div>

      {result && (
        <Card className="mt-8 border-2 border-primary/20 shadow-lg animate-in fade-in slide-in-from-bottom-4">
          <CardHeader className="bg-primary/5 border-b border-primary/10 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-xl text-primary"><CheckCircle2 className="h-6 w-6" /> AI Credit Appraisal Complete</CardTitle>
                <CardDescription className="mt-1">Company: {result.company_name}</CardDescription>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-slate-800">{result.mock_risk_score}/100</div>
                <div className="text-sm font-medium text-muted-foreground">Risk Score</div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2">Executive Summary</h4>
              <p className="text-slate-700 leading-relaxed text-sm">{result.ai_analysis}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200">
                <h4 className="text-sm font-semibold text-emerald-900 mb-2">Recommended Terms</h4>
                <p className="text-sm text-emerald-900"><span className="font-semibold">Loan Limit: </span>{formatCurrencyInr(result.recommended_limit_inr)}</p>
                <p className="text-sm text-emerald-900 mt-1"><span className="font-semibold">Interest Rate: </span>{result.recommended_interest_rate_pct}%</p>
              </div>
              <div className="p-4 rounded-lg bg-violet-50 border border-violet-200">
                <h4 className="text-sm font-semibold text-violet-900 mb-2">The Five C&apos;s of Credit</h4>
                <p className="text-xs text-violet-900 leading-relaxed">{result.five_cs_summary}</p>
              </div>
            </div>
          </CardContent>
          <CardFooter className="bg-slate-50 border-t border-slate-100 flex flex-wrap justify-end gap-2 p-4">
            <Button variant="outline" className="border-green-600 text-green-700 hover:bg-green-50" onClick={() => handleFinalDecision("Approved")}>Approve</Button>
            <Button variant="outline" className="border-red-600 text-red-700 hover:bg-red-50" onClick={() => handleFinalDecision("Rejected")}>Reject</Button>
            <Button variant="outline" onClick={handleDownloadMaskedData}>Masked Logs</Button>
            
            {/* THIS IS THE UPDATED BUTTON */}
            <Button variant="default" className="gap-2" onClick={handleDownloadPDF}>
              <FileText className="h-4 w-4" /> Download Full CAM Report (PDF)
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  )
}