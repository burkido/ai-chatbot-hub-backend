import { OpenAPI } from './core/OpenAPI';
import { getApplicationKey } from '../utils/applicationKey';
import axios from 'axios';

/**
 * Configure the OpenAPI client with interceptors for auth and application key
 */
export const configureApiClient = () => {
  // Configure request interceptor to add auth and application key headers
  OpenAPI.interceptors.request.use(async (config) => {
    // Add Authorization header if token exists
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${token}`
      };
    }

    // Add X-Application-Key header if it exists
    const applicationKey = getApplicationKey();
    if (applicationKey) {
      config.headers = {
        ...config.headers,
        'X-Application-Key': applicationKey
      };
    }

    return config;
  });
  
  // Initialize axios defaults with the base URL
  axios.defaults.baseURL = OpenAPI.BASE;
  
  return OpenAPI;
};