/**
 * Utilities for managing the application key for API requests
 */

const APPLICATION_KEY_STORAGE_KEY = 'application_key';

/**
 * Save the application key to local storage
 */
export const saveApplicationKey = (key: string): void => {
  localStorage.setItem(APPLICATION_KEY_STORAGE_KEY, key);
};

/**
 * Get the application key from local storage
 */
export const getApplicationKey = (): string | null => {
  return localStorage.getItem(APPLICATION_KEY_STORAGE_KEY);
};

/**
 * Clear the application key from local storage
 */
export const clearApplicationKey = (): void => {
  localStorage.removeItem(APPLICATION_KEY_STORAGE_KEY);
};