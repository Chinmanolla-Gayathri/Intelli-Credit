"use client"

import { useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

export function FieldNotes() {
  const [notes, setNotes] = useState("")

  return (
    <div className="space-y-3">
      <Label
        htmlFor="field-notes"
        className="text-sm font-medium text-foreground"
      >
        Credit Officer Field Notes & Qualitative Insights
      </Label>
      <Textarea
        id="field-notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Enter observations from factory visits or management interviews..."
        className="min-h-[140px] resize-none bg-card text-sm placeholder:text-muted-foreground/60"
      />
      <p className="text-xs text-muted-foreground">
        Include any qualitative observations that may impact credit assessment
      </p>
    </div>
  )
}
