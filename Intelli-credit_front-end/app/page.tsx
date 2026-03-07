"use client"

import { useState } from "react"
import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { NewAppraisalView } from "@/components/dashboard/new-appraisal-view"

export default function DashboardPage() {
  const [activeNav, setActiveNav] = useState("new-appraisal")

  const getPageTitle = () => {
    switch (activeNav) {
      case "dashboard":
        return "Dashboard"
      case "new-appraisal":
        return "New Appraisal"
      case "historical":
        return "Historical Data"
      case "settings":
        return "Settings"
      default:
        return "Dashboard"
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar activeItem={activeNav} onItemClick={setActiveNav} />

      {/* Main Content Area */}
      <div className="pl-64">
        <Header title={getPageTitle()} />

        <main className="p-6">
          {activeNav === "new-appraisal" && <NewAppraisalView />}
          
          {activeNav === "dashboard" && (
            <div className="flex h-[60vh] items-center justify-center">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground">Dashboard Overview</h2>
                <p className="mt-2 text-muted-foreground">Analytics and insights coming soon</p>
              </div>
            </div>
          )}
          
          {activeNav === "historical" && (
            <div className="flex h-[60vh] items-center justify-center">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground">Historical Data</h2>
                <p className="mt-2 text-muted-foreground">Past appraisals and records</p>
              </div>
            </div>
          )}
          
          {activeNav === "settings" && (
            <div className="flex h-[60vh] items-center justify-center">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground">Settings</h2>
                <p className="mt-2 text-muted-foreground">Configuration options</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
