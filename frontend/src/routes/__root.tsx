import { Outlet, createRootRoute } from "@tanstack/react-router"
import React, { Suspense, useEffect } from "react"

import NotFound from "../components/Common/NotFound"
import { configureApiClient } from "../client/clientConfig"

const loadDevtools = () =>
  Promise.all([
    import("@tanstack/router-devtools"),
    import("@tanstack/react-query-devtools"),
  ]).then(([routerDevtools, reactQueryDevtools]) => {
    return {
      default: () => (
        <>
          <routerDevtools.TanStackRouterDevtools />
          <reactQueryDevtools.ReactQueryDevtools />
        </>
      ),
    }
  })

const TanStackDevtools =
  process.env.NODE_ENV === "production" ? () => null : React.lazy(loadDevtools)

export const Route = createRootRoute({
  component: () => {
    useEffect(() => {
      // Initialize API client with interceptors
      configureApiClient();
    }, []);

    return (
      <>
        <Outlet />
        <Suspense>
          <TanStackDevtools />
        </Suspense>
      </>
    );
  },
  notFoundComponent: () => <NotFound />,
})
