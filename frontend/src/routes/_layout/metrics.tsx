import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Suspense } from "react"

import { MetricsService, UsersService } from "@/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { canViewMetrics } from "@/lib/roles"

export const Route = createFileRoute("/_layout/metrics")({
  component: Metrics,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!canViewMetrics(user.role)) {
      throw redirect({ to: "/forbidden" })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Metrics - FastAPI Template",
      },
    ],
  }),
})

function MetricsSummaryContent() {
  const { data: summary } = useSuspenseQuery({
    queryFn: async () => (await MetricsService.readMetricsSummary()).data,
    queryKey: ["metrics-summary"],
  })

  const cards = [
    { title: "Total users", value: summary.total_users },
    { title: "Active users", value: summary.active_users },
    ...Object.entries(summary.users_by_role).map(([role, count]) => ({
      title: `Role: ${role}`,
      value: count,
    })),
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">
              {card.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{card.value}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function Metrics() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Metrics</h1>
        <p className="text-muted-foreground">User counts across the app</p>
      </div>
      <Suspense fallback={<p className="text-muted-foreground">Loading...</p>}>
        <MetricsSummaryContent />
      </Suspense>
    </div>
  )
}
