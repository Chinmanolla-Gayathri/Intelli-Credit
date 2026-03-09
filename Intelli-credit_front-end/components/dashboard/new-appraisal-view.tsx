"use client"

import { useState } from "react"
import jsPDF from "jspdf"
import autoTable from "jspdf-autotable"
import { Sparkles, Loader2, CheckCircle2, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { FileUpload } from "./file-upload"
import { FieldNotes } from "./field-notes"

export function NewAppraisalView() {
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  // 1. New state to hold the final AI report!
  const [result, setResult] = useState<any>(null)
  const [fieldNotes, setFieldNotes] = useState("")

  const handleDatabricksSync = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/databricks/sync")
      if (!response.ok) {
        throw new Error("Failed to sync with Databricks")
      }
      const data = await response.json()
      alert(data?.message || "Databricks sync complete!")
    } catch (error) {
      console.error("Databricks sync failed:", error)
      alert("Failed to sync with Databricks. Please try again.")
    }
  }

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
      loan_limit: result.recommended_limit_inr,
      interest_rate: result.recommended_interest_rate_pct,
      five_cs: result.five_cs_summary,
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

  const formatCurrencyInr = (value: number | undefined | null) => {
    if (value == null || Number.isNaN(Number(value))) return "₹0"
    try {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(Number(value))
    } catch {
      return `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
    }
  }

  const downloadCamReport = () => {
    if (!result) {
      alert("No CAM report available to download.")
      return
    }

    try {
      const doc = new jsPDF()
      const pageWidth = doc.internal.pageSize.getWidth()
      const pageHeight = doc.internal.pageSize.getHeight()
      const marginX = 16
      let currentY = 20

      // Header - base64 logo and title
      const logoBase64 =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAALElEQVQ4T2NkoBAwUqifgYGB4T8jCDAxMZph0aJFYBVEM2GqAaNGjXqEAADEWQh8P+GZWQAAAABJRU5ErkJggg=="

      try {
        const logoWidth = 28
        const logoHeight = 28
        const logoX = pageWidth / 2 - logoWidth / 2
        const logoY = 8
        doc.addImage(logoBase64, "PNG", logoX, logoY, logoWidth, logoHeight)
        currentY = logoY + logoHeight + 6
      } catch {
        // if logo fails, continue without blocking PDF generation
        currentY = 20
      }

      doc.setFontSize(16)
      doc.setFont("helvetica", "bold")
      doc.text("INTELLI-CREDIT RISK ENGINE", pageWidth / 2, currentY, {
        align: "center",
      })
      currentY += 6

      // Horizontal separator under header
      doc.setDrawColor(200)
      doc.line(marginX, currentY, pageWidth - marginX, currentY)
      currentY += 8

      // Summary table
      const summaryBody = [
        [
          result.company_name || "Unknown Company",
          `${result.mock_risk_score ?? "N/A"}/100`,
          formatCurrencyInr(result.recommended_limit_inr),
          result.recommended_interest_rate_pct != null
            ? `${result.recommended_interest_rate_pct}%`
            : "N/A",
        ],
      ]

      autoTable(doc, {
        startY: currentY,
        head: [["Company Name", "Risk Score", "Loan Limit", "Interest Rate"]],
        body: summaryBody,
        styles: { fontSize: 12 },
        headStyles: { fillColor: [22, 93, 255], fontSize: 12 },
        theme: "grid",
        margin: { left: marginX, right: marginX },
      })

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const autoTableData: any = (doc as any).lastAutoTable
      currentY = autoTableData?.finalY ? autoTableData.finalY + 8 : currentY + 30

      const addSection = (title: string, text: string | undefined | null) => {
        const safeText = text || "N/A"

        doc.setFontSize(16)
        doc.setFont("helvetica", "bold")
        doc.setTextColor(30, 64, 175) // blue header

        if (currentY > pageHeight - 30) {
          doc.addPage()
          currentY = 20
        }
        doc.text(title, marginX, currentY)
        currentY += 8

        doc.setFontSize(12)
        doc.setFont("helvetica", "normal")
        doc.setTextColor(0, 0, 0)

        const wrappedText = doc.splitTextToSize(
          safeText,
          pageWidth - marginX * 2,
        )

        wrappedText.forEach((line: string) => {
          if (currentY > pageHeight - 20) {
            doc.addPage()
            currentY = 20
          }
          doc.text(line, marginX, currentY)
          currentY += 6
        })

        currentY += 4
      }

      addSection("Executive Summary", result.ai_analysis)
      addSection("The Five C's of Credit", result.five_cs_summary)
      addSection("Secondary Web Research", result.ai_analysis)

      // Footer on every page
      const generatedOn = new Date().toLocaleString()
      const pageCount = doc.getNumberOfPages()
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i)
        const h = doc.internal.pageSize.getHeight()
        doc.setFontSize(8)
        doc.setTextColor(120)
        doc.text(
          `Generated on ${generatedOn} | Confidential Banking Document`,
          marginX,
          h - 10,
        )
      }

      const filename = `${
        (result.company_name || "CAM_Report").replace(/[^\w\-]+/g, "_")
      }_CAM_Report.pdf`
      doc.save(filename)
    } catch (error) {
      console.error("Failed to generate CAM PDF", error)
      alert("Unable to generate CAM PDF.")
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Generate Credit Appraisal Memo (CAM)
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Automate loan decisioning with AI-powered document analysis and risk assessment
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="mt-2 sm:mt-0"
          onClick={handleDatabricksSync}
        >
          Sync with Databricks
        </Button>
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
              <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2">
                Executive Summary
              </h4>
              <p className="text-slate-700 leading-relaxed">{result.ai_analysis}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 rounded-lg bg-green-50 border border-green-100">
                <h4 className="text-sm font-semibold text-green-800 mb-1">System Decision</h4>
                <p className="font-bold text-green-900">{result.mock_decision}</p>
              </div>
              <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
                <h4 className="text-sm font-semibold text-blue-800 mb-1 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" /> Data Masking Protocol
                </h4>
                <p className="text-xs text-blue-900 font-mono mt-2 truncate">
                  {result.masked_text_preview}
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200">
                <h4 className="text-sm font-semibold text-emerald-900 mb-2">
                  Recommended Terms
                </h4>
                <p className="text-sm text-emerald-900">
                  <span className="font-semibold">Loan Limit: </span>
                  {formatCurrencyInr(result.recommended_limit_inr)}
                </p>
                <p className="text-sm text-emerald-900 mt-1">
                  <span className="font-semibold">Interest Rate: </span>
                  {result.recommended_interest_rate_pct != null
                    ? `${result.recommended_interest_rate_pct}%`
                    : "N/A"}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-violet-50 border border-violet-200">
                <h4 className="text-sm font-semibold text-violet-900 mb-2">
                  The Five C&apos;s of Credit
                </h4>
                <p className="text-sm text-violet-900 leading-relaxed">
                  {result.five_cs_summary || "Five C's summary not available."}
                </p>
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
            <Button variant="default" onClick={downloadCamReport}>
              Download Full CAM Report (PDF)
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  )
}