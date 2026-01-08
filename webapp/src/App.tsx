import { useEffect, useState } from 'react';
import { Header } from './components/layout';
import { RunDashboard } from './pages/RunDashboard';
import { configureApiClient, HealthService } from './api/client';
import { validateConfig } from './config';

function App() {
  const [isConfigured, setIsConfigured] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);

  useEffect(() => {
    // Validate and configure API client on mount
    // This is initial configuration, not a cascading effect

    const initializeApp = async () => {
      try {
        validateConfig();
        configureApiClient();
        setIsConfigured(true);

        // Test API connection
        try {
          await HealthService.healthCheckHealthGet();
        } catch (error) {
          console.warn('Health check failed, but continuing:', error);
          // Don't block app initialization if health check fails
          // User will see connection errors when they try to use the app
        }
      } catch (error) {
        console.error('Configuration error:', error);
        setConfigError(error instanceof Error ? error.message : 'Configuration failed');
        setIsConfigured(false);
      } finally {
        setIsCheckingHealth(false);
      }
    };

    initializeApp();
  }, []);

  if (isCheckingHealth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <div
            className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"
            role="status"
          >
            <span className="sr-only">Loading...</span>
          </div>
          <p className="mt-4 text-gray-600">Initializing...</p>
        </div>
      </div>
    );
  }

  if (!isConfigured) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-bold text-gray-900">Configuration Error</h1>
          <p className="mt-2 text-gray-600">{configError || 'Check console for details'}</p>
          <div className="mt-4 rounded-md bg-yellow-50 p-4 text-left">
            <p className="text-sm text-yellow-800">
              Make sure VITE_API_BASE_URL is set in your .env file
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main role="main">
        <RunDashboard />
      </main>
    </div>
  );
}

export default App;
