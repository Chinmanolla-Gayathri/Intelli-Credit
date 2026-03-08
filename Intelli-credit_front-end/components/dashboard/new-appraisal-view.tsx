"use client"

import { useState } from "react"
import { Sparkles, Loader2, CheckCircle2, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { FileUpload } from "./file-upload"
import { FieldNotes } from "./field-notes"

export function NewAppraisalView() {
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  // 1. New state to hold the final AI report!
  const [result, setResult] = useState(null)
  const [fieldNotes, setFieldNotes] = useState("")

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      alert("Please upload at least one PDF document first!");
      return;
    }

    setIsLoading(true)
    setResult(null) // Clear previous results
    
    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => {
         formData.append("files", file);
      });
      formData.append("fieldNotes", fieldNotes);

      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        body: formData
      });
      
      const data = await response.json();
      
      // 2. Instead of alerting, we save the data to our state!
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
      alert("No masked data available to download.")
      return
    }

    try {
      const blob = new Blob([result.masked_text], { type: "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = "masked_data.txt"
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error("Failed to download masked data", error)
      alert("Unable to download masked data.")
    }
  }

  const handleFinalDecision = async (humanDecision: string) => {
    if (humanDecision === "Discard") {
      setResult(null)
      return
    }

    if (!result) {
      alert("No appraisal result available to save.")
      return
    }

    const payload = {
      company_name: result.company_name || "Unknown Company",
      risk_score: Number(result.mock_risk_score),
      status: humanDecision,
      ai_analysis: result.ai_analysis,
      extracted_metrics: result.extracted_metrics || {},
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/api/save_decision", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error("Failed to save decision")
      }

      alert("Saved to Database!")
      setResult(null)
    } catch (error) {
      console.error("Error saving decision:", error)
      alert("Failed to save decision to the database.")
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">
          Generate Credit Appraisal Memo (CAM)
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Automate loan decisioning with AI-powered document analysis and risk assessment
        </p>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Document Upload</CardTitle>
            <CardDescription>Upload financial statements, GST filings, and other supporting documents</CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload onFilesSelected={setSelectedFiles} />
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analysis Summary</CardTitle>
            <CardDescription>Upload documents to begin analysis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
              <span className="text-sm text-muted-foreground">Documents</span>
              <span className="text-sm font-semibold text-foreground">{selectedFiles.length > 0 ? selectedFiles.length : '3'} files</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
              <span className="text-sm text-muted-foreground">Status</span>
              <span className="text-sm font-semibold text-success">{selectedFiles.length > 0 ? 'Ready for Analysis' : 'Awaiting Upload'}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Qualitative Assessment</CardTitle>
          <CardDescription>Add observations and insights from your field assessment</CardDescription>
        </CardHeader>
        <CardContent>
          <FieldNotes value={fieldNotes} onChange={setFieldNotes} />
        </CardContent>
      </Card>

      {/* Action Area */}
      <div className="flex items-center justify-end gap-4 pt-2">
        <Button variant="outline">Save Draft</Button>
        <Button onClick={handleAnalyze} disabled={isLoading} className="min-w-[200px] gap-2">
          {isLoading ? (
            <><Loader2 className="h-4 w-4 animate-spin" /> Analyzing...</>
          ) : (
            <><Sparkles className="h-4 w-4" /> Analyze & Generate CAM</>
          )}
        </Button>
      </div>

      {/* 3. THE NEW AI RESULT CARD - Only shows when result exists */}
      {result && (
        <Card className="mt-8 border-2 border-primary/20 shadow-lg animate-in fade-in slide-in-from-bottom-4 duration-500">
          <CardHeader className="bg-primary/5 border-b border-primary/10 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-xl text-primary">
                  <CheckCircle2 className="h-6 w-6" />
                  AI Credit Appraisal Complete
                </CardTitle>
                <CardDescription className="mt-1">Generated by Intelli-Credit Risk Engine</CardDescription>
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
              <p className="text-slate-700 leading-relaxed">{result.ai_analysis}</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
               <div className="p-4 rounded-lg bg-green-50 border border-green-100">
                 <h4 className="text-sm font-semibold text-green-800 mb-1">System Decision</h4>
                 <p className="font-bold text-green-900">{result.mock_decision}</p>
               </div>
               <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
                 <h4 className="text-sm font-semibold text-blue-800 mb-1 flex items-center gap-2">
                   <AlertTriangle className="h-4 w-4" /> Data Masking Protocol
                 </h4>
                 <p className="text-xs text-blue-900 font-mono mt-2 truncate">{result.masked_text_preview}</p>
               </div>
            </div>
          </CardContent>
          <CardFooter className="bg-slate-50 border-t border-slate-100 flex flex-wrap justify-end gap-2">
            <Button
              variant="outline"
              className="border-green-600 text-green-700 hover:bg-green-50"
              onClick={() => handleFinalDecision("Approved")}
            >
              Approve
            </Button>
            <Button
              variant="outline"
              className="border-red-600 text-red-700 hover:bg-red-50"
              onClick={() => handleFinalDecision("Rejected")}
            >
              Reject
            </Button>
            <Button
              variant="outline"
              className="text-muted-foreground hover:bg-muted/40"
              onClick={() => handleFinalDecision("Discard")}
            >
              Discard
            </Button>
            <Button variant="outline" onClick={handleDownloadMaskedData}>
              Download Masked Data
            </Button>
            <Button
              variant="default"
              onClick={() => {
                if (!result) {
                  alert("No CAM report available to download.")
                  return
                }

                try {
                  const camTextLines = [
                    "Intelli-Credit CAM Report",
                    "=========================",
                    "",
                    `Company Name: ${result.company_name || "Unknown Company"}`,
                    `System Decision: ${result.mock_decision}`,
                    `Risk Score: ${result.mock_risk_score}/100`,
                    "",
                    "AI Analysis:",
                    result.ai_analysis || "N/A",
                    "",
                    "Extracted Metrics (JSON):",
                    JSON.stringify(result.extracted_metrics || {}, null, 2),
                  ]

                  const blob = new Blob([camTextLines.join("\n")], {
                    type: "text/plain;charset=utf-8",
                  })
                  const url = URL.createObjectURL(blob)
                  const link = document.createElement("a")
                  link.href = url
                  link.download = `${
                    (result.company_name || "CAM_Report").replace(/[^\w\-]+/g, "_")
                  }_CAM_Report.txt`
                  document.body.appendChild(link)
                  link.click()
                  link.remove()
                  URL.revokeObjectURL(url)
                } catch (error) {
                  console.error("Failed to download CAM report", error)
                  alert("Unable to download CAM report.")
                }
              }}
            >
              Download Full CAM Report (PDF)
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  )
}