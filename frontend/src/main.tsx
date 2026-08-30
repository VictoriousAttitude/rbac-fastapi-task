import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { toast } from "sonner"
import { client } from "./client/client.gen"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import { routeTree } from "./routeTree.gen"

client.setConfig({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  auth: () => localStorage.getItem("access_token") || "",
})

// 401 = bad credentials -> re-authenticate; 403 = missing permission ->
// friendly feedback without destroying the session
const handleUnauthorized = (error: Error) => {
  if (error instanceof AxiosError && error.response?.status === 401) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      handleUnauthorized(error)
      if (error instanceof AxiosError && error.response?.status === 403) {
        window.location.href = "/forbidden"
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      handleUnauthorized(error)
      if (error instanceof AxiosError && error.response?.status === 403) {
        toast.error("You don't have permission to perform this action")
      }
    },
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
