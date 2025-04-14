import { OpenAPI } from "./core/OpenAPI"
import { getApplicationKey } from "../utils/applicationKey"
import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from "axios"
import TokenService from "../utils/tokenService"

// Flag to avoid multiple token refresh requests
let isRefreshing = false
let refreshAttempted = false // Track if a refresh has been attempted this session
let failedQueue: {
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}[] = []

const processQueue = (error: unknown | null, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error)
    } else {
      promise.resolve(token)
    }
  })

  failedQueue = []
}

/**
 * Configure the OpenAPI client with interceptors for auth, token refresh, and application key
 */
export const configureApiClient = () => {
  // Configure request interceptor to add auth and application key headers
  OpenAPI.interceptors.request.use(async (config) => {
    // Add Authorization header if token exists
    const token = TokenService.getAccessToken()
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      }
    }

    // Add X-Application-Key header if it exists
    const applicationKey = getApplicationKey()
    if (applicationKey) {
      config.headers = {
        ...config.headers,
        "X-Application-Key": applicationKey,
      }
    }

    return config
  })

  // Add response interceptor to handle token refresh
  axios.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as AxiosRequestConfig & {
        _retry?: boolean
        _isRefreshRequest?: boolean // Flag to identify refresh token requests
      }

      // Skip if this is not an auth error or is already being retried
      // Also skip if this is a refresh token request itself (to prevent loops)
      if (
        !originalRequest ||
        error.response?.status !== 401 ||
        originalRequest._retry ||
        originalRequest._isRefreshRequest ||
        refreshAttempted // Skip refresh if we've already attempted once
      ) {
        return Promise.reject(error)
      }

      // If we're not refreshing yet, try to refresh the token
      if (!isRefreshing) {
        isRefreshing = true
        refreshAttempted = true // Mark that we've attempted a refresh
        originalRequest._retry = true

        try {
          // Attempt to refresh the token
          const refreshed = await TokenService.refreshToken()

          if (refreshed) {
            // Update the Authorization header
            if (originalRequest.headers) {
              originalRequest.headers["Authorization"] =
                `Bearer ${TokenService.getAccessToken()}`
            }

            // Process any queued requests
            processQueue(null, TokenService.getAccessToken())

            // Retry the original request
            return axios(originalRequest)
          } else {
            // If refresh failed, reject all queued requests
            processQueue(new Error("Token refresh failed"))

            // Redirect to login page
            window.location.href = "/login"
            return Promise.reject(error)
          }
        } catch (refreshError) {
          // If refresh throws an error, reject all queued requests
          processQueue(refreshError)

          // Redirect to login page
          window.location.href = "/login"
          return Promise.reject(error)
        } finally {
          isRefreshing = false
        }
      } else {
        // If we're already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            // Once we have a token, update the header and retry
            if (originalRequest.headers) {
              originalRequest.headers["Authorization"] = `Bearer ${token}`
            }
            return axios(originalRequest)
          })
          .catch((err) => {
            return Promise.reject(err)
          })
      }
    },
  )

  // Initialize axios defaults with the base URL
  axios.defaults.baseURL = OpenAPI.BASE

  return OpenAPI
}
