"use client"

import { useState, useEffect } from "react"
import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { NewAppraisalView } from "@/components/dashboard/new-appraisal-view"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, Users, CreditCard, TrendingUp, Loader2 } from "lucide-react"

type HistoryRecord = {
  company_name: string
  date?: string
  risk_score: number
  status: string
  ai_analysis: string
}

function HistoricalAppraisalsCard() {
  const [records, setRecords] = useState<HistoryRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    const fetchHistory = async () => {
      try {
        setIsLoading(true)
        const response = await fetch(
          `http://127.0.0.1:8000/api/history?t=${Date.now()}`,
        )
        if (!response.ok) {
          throw new Error("Failed to fetch history")
        }
        const data = await response.json()
        if (!isMounted) return
        const rows = Array.isArray(data?.data) ? data.data : []
        setRecords(rows)
        setError(null)
      } catch (err) {
        if (!isMounted) return
        console.error("Failed to load history", err)
        setError("Unable to load historical data.")
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    fetchHistory()

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <Card className="animate-in fade-in">
      <CardHeader>
        <CardTitle>Recent Appraisals</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="mr-2 h-5 w-5 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Loading history...</span>
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : records.length === 0 ? (
          <p className="text-sm text-muted-foreground">No historical appraisals found.</p>
        ) : (
          <div className="relative w-full overflow-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                    Appraisal Name
                  </th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                    State
                  </th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                    ML Prediction
                  </th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                    AI Report
                  </th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {records.map((row, i) => (
                  <tr key={`${row.company_name}-${row.date}-${i}`} className="border-b transition-colors hover:bg-muted/50">
                    <td className="p-4 align-middle font-medium">{row.company_name}</td>
                    <td className="p-4 align-middle">{row.status}</td>
                    <td className="p-4 align-middle">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          row.risk_score > 80
                            ? "bg-green-100 text-green-800"
                            : row.risk_score > 60
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-red-100 text-red-800"
                        }`}
                      >
                        {row.risk_score}/100
                      </span>
                    </td>
                    <td className="p-4 align-middle">
                      <span
                        className="line-clamp-2 cursor-help"
                        title={row.ai_analysis}
                      >
                        {row.ai_analysis.length > 100
                          ? `${row.ai_analysis.slice(0, 100)}...`
                          : row.ai_analysis}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const [activeNav, setActiveNav] = useState("new-appraisal")
  const [dashboardStats, setDashboardStats] = useState({
    total: 0,
    approval_rate: 0,
    high_risk: 0,
  })
  const [isLoadingStats, setIsLoadingStats] = useState(true)

  useEffect(() => {
    if (activeNav !== "dashboard") {
      return
    }

    let isMounted = true

    const fetchStats = async () => {
      try {
        setIsLoadingStats(true)
        const response = await fetch(
          `http://127.0.0.1:8000/api/stats?t=${Date.now()}`,
        )
        if (!response.ok) {
          throw new Error("Failed to fetch dashboard stats")
        }
        const data = await response.json()
        if (!isMounted) return
        const stats = data?.data ?? {
          total: 0,
          approval_rate: 0,
          high_risk: 0,
        }
        setDashboardStats(stats)
      } catch (error) {
        if (!isMounted) return
        console.error("Failed to load dashboard stats", error)
      } finally {
        if (isMounted) {
          setIsLoadingStats(false)
        }
      }
    }

    fetchStats()

    return () => {
      isMounted = false
    }
  }, [activeNav])

  const getPageTitle = () => {
    switch (activeNav) {
      case "dashboard": return "Dashboard Overview"
      case "new-appraisal": return "New Appraisal"
      case "historical": return "Historical Data"
      case "settings": return "Settings"
      default: return "Dashboard"
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <Sidebar activeItem={activeNav} onItemClick={setActiveNav} />

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 w-full">
        <Header title={getPageTitle()} />

        <main className="p-4 md:p-6 max-w-7xl mx-auto">
          {activeNav === "new-appraisal" && <NewAppraisalView />}
          
          {/* DASHBOARD TAB POLISH */}
          {activeNav === "dashboard" && (
            <div className="space-y-6 animate-in fade-in">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Appraisals</CardTitle>
                    <Activity className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {isLoadingStats ? (
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      ) : (
                        dashboardStats.total
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">Total CAMs processed</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Approval Rate</CardTitle>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {dashboardStats.approval_rate}%
                    </div>
                    <p className="text-xs text-muted-foreground">AI-assisted approval ratio</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Avg Process Time</CardTitle>
                    <Users className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold flex items-baseline gap-2">
                      <span>2.4 mins</span>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                        ⚡ AI Accelerated
                      </span>
                    </div>
                    <p className="text-xs text-success font-medium">↓ 85% vs manual processing</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">High Risk Flags</CardTitle>
                    <CreditCard className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-destructive">
                      {dashboardStats.high_risk}
                    </div>
                    <p className="text-xs text-muted-foreground">Requires manual review</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
          
          {/* HISTORICAL DATA TAB POLISH */}
          {activeNav === "historical" && <HistoricalAppraisalsCard />}
          
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