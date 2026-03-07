"use client"

import { useState, useCallback } from "react"
import { CloudUpload, FileText, Check, Trash2, FileArchive } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface UploadedFile {
  id: string
  name: string
  type: "pdf" | "zip"
  size: string
}

const initialFiles: UploadedFile[] = [
  { id: "1", name: "GST_Filing_2025.pdf", type: "pdf", size: "2.4 MB" },
  { id: "2", name: "Bank_Statement.pdf", type: "pdf", size: "1.8 MB" },
  { id: "3", name: "Annual_Report.zip", type: "zip", size: "15.2 MB" },
]

export function FileUpload() {
  const [files, setFiles] = useState<UploadedFile[]>(initialFiles)
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    // Handle file drop logic here
  }, [])

  const removeFile = (id: string) => {
    setFiles(files.filter((file) => file.id !== id))
  }

  return (
    <div className="space-y-4">
      {/* Drag and Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "relative flex min-h-[200px] flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border bg-muted/30 hover:border-primary/50 hover:bg-muted/50"
        )}
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
            <CloudUpload className="h-7 w-7 text-primary" />
          </div>
          <p className="mb-1 text-base font-medium text-foreground">
            Drag & drop files here
          </p>
          <p className="mb-4 text-sm text-muted-foreground">
            Upload Company Documents (.zip, or multiple .pdf files)
          </p>
          <Button variant="outline" size="sm" className="font-medium">
            Browse Files
          </Button>
        </div>
      </div>

      {/* Uploaded Files List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">
            Uploaded Documents ({files.length})
          </p>
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between rounded-lg border border-border bg-card p-3 transition-colors hover:bg-accent/30"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    {file.type === "pdf" ? (
                      <FileText className="h-5 w-5 text-primary" />
                    ) : (
                      <FileArchive className="h-5 w-5 text-primary" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">{file.size}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-success/10">
                    <Check className="h-3.5 w-3.5 text-success" />
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => removeFile(file.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                    <span className="sr-only">Remove {file.name}</span>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
