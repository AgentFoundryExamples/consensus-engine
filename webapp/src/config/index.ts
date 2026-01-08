/**
 * Environment configuration for the Consensus Engine webapp
 * Loaded from environment variables (Vite uses VITE_ prefix)
 */

export interface AppConfig {
  /** Base URL for the API (e.g., http://localhost:8000) */
  apiBaseUrl: string;
  
  /** Optional IAM token for authentication (placeholder for Cloud IAP/IAM) */
  iamToken?: string;
  
  /** Polling interval in milliseconds for checking run status */
  pollingIntervalMs: number;
  
  /** Environment name (development, staging, production) */
  environment: string;
}

/**
 * Load configuration from environment variables
 * Vite exposes env vars prefixed with VITE_ as import.meta.env.VITE_*
 */
export const config: AppConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  iamToken: import.meta.env.VITE_IAM_TOKEN,
  pollingIntervalMs: parseInt(import.meta.env.VITE_POLLING_INTERVAL_MS || '3000', 10),
  environment: import.meta.env.VITE_ENVIRONMENT || import.meta.env.MODE || 'development',
};

/**
 * Validate configuration at startup
 */
export function validateConfig(): void {
  if (!config.apiBaseUrl) {
    throw new Error('VITE_API_BASE_URL must be set');
  }
  
  if (config.pollingIntervalMs < 1000 || config.pollingIntervalMs > 60000) {
    console.warn('VITE_POLLING_INTERVAL_MS should be between 1000 and 60000ms');
  }
  
  console.log('App configuration:', {
    apiBaseUrl: config.apiBaseUrl,
    environment: config.environment,
    pollingIntervalMs: config.pollingIntervalMs,
    hasIamToken: !!config.iamToken,
  });
}
