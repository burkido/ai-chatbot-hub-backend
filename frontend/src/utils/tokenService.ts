import { LoginService, type RefreshTokenRequest, type Token } from "../client";
import { clearApplicationKey } from "./applicationKey";

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_INFO_KEY = 'user_info';

// Track if a refresh has been attempted
let tokenRefreshAttempted = false;

/**
 * TokenService manages auth tokens storage and refresh functionality
 */
export const TokenService = {
  /**
   * Save authentication tokens and user info in local storage
   */
  saveTokens: (token: Token): void => {
    localStorage.setItem(ACCESS_TOKEN_KEY, token.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, token.refresh_token);
    
    // Store additional user info
    localStorage.setItem(USER_INFO_KEY, JSON.stringify({
      user_id: token.user_id,
      application_id: token.application_id,
      is_premium: token.is_premium,
      remaining_credit: token.remaining_credit
    }));
    
    // Reset refresh state on successful login/token update
    tokenRefreshAttempted = false;
  },

  /**
   * Get the current access token
   */
  getAccessToken: (): string | null => {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  /**
   * Get the current refresh token
   */
  getRefreshToken: (): string | null => {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  /**
   * Get stored user info
   */
  getUserInfo: () => {
    const infoStr = localStorage.getItem(USER_INFO_KEY);
    if (infoStr) {
      try {
        return JSON.parse(infoStr);
      } catch (e) {
        return null;
      }
    }
    return null;
  },

  /**
   * Check if user is logged in
   */
  isLoggedIn: (): boolean => {
    return !!localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  /**
   * Refresh the access token using the refresh token
   * Will only attempt to refresh once per session unless reset
   */
  refreshToken: async (): Promise<boolean> => {
    const refreshToken = TokenService.getRefreshToken();
    
    if (!refreshToken || tokenRefreshAttempted) {
      return false;
    }

    try {
      // Mark that we've attempted to refresh
      tokenRefreshAttempted = true;
      
      const request: RefreshTokenRequest = {
        refresh_token: refreshToken
      };
      
      const response = await LoginService.refreshAccessToken({ 
        requestBody: request 
      });
      
      TokenService.saveTokens(response);
      // Reset flag on successful refresh
      tokenRefreshAttempted = false;
      return true;
    } catch (error) {
      TokenService.clearTokens();
      return false;
    }
  },

  /**
   * Clear all authentication tokens and related data
   */
  clearTokens: (): void => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_INFO_KEY);
    clearApplicationKey();
    // Reset refresh attempt state
    tokenRefreshAttempted = false;
  },

  /**
   * Reset the refresh attempt state
   * This can be called to allow another refresh attempt after a login
   */
  resetRefreshState: (): void => {
    tokenRefreshAttempted = false;
  }
};

export default TokenService;