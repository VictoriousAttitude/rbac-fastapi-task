import { createFileRoute, Link } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/_layout/forbidden")({
  component: Forbidden,
  head: () => ({
    meta: [
      {
        title: "Access Denied - FastAPI Template",
      },
    ],
  }),
})

function Forbidden() {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <h1 className="text-2xl font-bold">Access denied</h1>
      <p className="text-muted-foreground">
        You don't have permission to view this page. If you think you should,
        ask an administrator to adjust your role.
      </p>
      <Button asChild>
        <Link to="/">Back to Dashboard</Link>
      </Button>
    </div>
  )
}
