import { ChakraProvider } from "@chakra-ui/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { RouterProvider, createRouter } from "@tanstack/react-router"
import ReactDOM from "react-dom/client"
import { routeTree } from "./routeTree.gen"

import { StrictMode } from "react"
import { OpenAPI } from "./client"
import TokenService from "./utils/tokenService"
import theme from "./theme"
import { configureApiClient } from "./client/clientConfig"

// Configure OpenAPI base URL from environment
OpenAPI.BASE = import.meta.env.VITE_API_URL

// Use TokenService for authentication
OpenAPI.TOKEN = async () => TokenService.getAccessToken() || ""

// Initialize the API client with interceptors
configureApiClient()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1, // Default retry once
      refetchOnWindowFocus: false,
    },
  },
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ChakraProvider>
  </StrictMode>,
)
