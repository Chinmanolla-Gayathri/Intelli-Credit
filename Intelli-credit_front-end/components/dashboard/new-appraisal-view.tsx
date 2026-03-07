"use client"

import { useState } from "react"
import { Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileUpload } from "./file-upload"
import { FieldNotes } from "./field-notes"

export function NewAppraisalView() {
  const [isLoading, setIsLoading] = useState(false)
  // 1. Added state to hold the actual files the user selects
  const [selectedFiles, setSelectedFiles] = useState([])

  const handleAnalyze = async () => {
    // 2. Prevent clicking if no files are uploaded
    if (selectedFiles.length === 0) {
      alert("Please upload at least one PDF document first!");
      return;
    }

    setIsLoading(true)
    
    try {
      // 3. Package the files into a FormData object
      const formData = new FormData();
      selectedFiles.forEach((file) => {
         formData.append("files", file); // "files" must match the Python backend variable
      });

      // 4. Send the actual files to the Python server (No headers needed for FormData, the browser does it automatically)
      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        body: formData
      });
      
      const data = await response.json();
      
      console.log("Response from Python Brain:", data);
      alert(`✅ Success!\n\nAI Analysis: ${data.ai_analysis}\n\nMasked Preview: ${data.masked_text_preview}`);
      
    } catch (error) {
      console.error("Connection failed:", error);
      alert("Uh oh! Make sure your Python server is running in your other terminal.");
    } finally {
      setIsLoading(false)
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
        {/* Document Upload Section */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Document Upload</CardTitle>
            <CardDescription>
              Upload financial statements, GST filings, and other supporting documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload />
            
            {/* 5. The functional input hidden below the UI for testing */}
            <div className="mt-4 pt-4 border-t border-border">
               <p className="text-sm font-medium mb-2 text-muted-foreground">Functional Upload (For Testing):</p>
               <input 
                 type="file" 
                 multiple 
                 accept=".pdf"
                 onChange={(e) => {
                    if (e.target.files) {
                       setSelectedFiles(Array.from(e.target.files));
                    }
                 }}
                 className="block w-full text-sm text-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
               />
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analysis Summary</CardTitle>
            <CardDescription>
              Upload documents to begin analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
              <span className="text-sm text-muted-foreground">Documents</span>
              <span className="text-sm font-semibold text-foreground">3 files</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
              <span className="text-sm text-muted-foreground">Total Size</span>
              <span className="text-sm font-semibold text-foreground">19.4 MB</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
              <span className="text-sm text-muted-foreground">Status</span>
              <span className="text-sm font-semibold text-success">Ready</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Field Notes Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Qualitative Assessment</CardTitle>
          <CardDescription>
            Add observations and insights from your field assessment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldNotes />
        </CardContent>
      </Card>

      {/* Action Area */}
      <div className="flex items-center justify-end gap-4 pt-2">
        <Button variant="outline">Save Draft</Button>
        <Button
          onClick={handleAnalyze}
          disabled={isLoading}
          className="min-w-[200px] gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Analyze & Generate CAM
            </>
          )}
        </Button>
      </div>
    </div>
  )
}