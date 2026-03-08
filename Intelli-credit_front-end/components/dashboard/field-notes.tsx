"use client"

import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

interface FieldNotesProps {
  value: string
  onChange: (value: string) => void
}

export function FieldNotes({ value, onChange }: FieldNotesProps) {

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
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter observations from factory visits or management interviews..."
        className="min-h-[140px] resize-none bg-card text-sm placeholder:text-muted-foreground/60"
      />
      <p className="text-xs text-muted-foreground">
        Include any qualitative observations that may impact credit assessment
      </p>
    </div>
  )
}
