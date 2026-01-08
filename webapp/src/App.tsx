import { useEffect, useState } from 'react';
import { Header, Container } from './components/layout';
import { Button, StatusBadge } from './components/ui';
import { configureApiClient, HealthService } from './api/client';
import { validateConfig, config } from './config';

function App() {
  const [isConfigured, setIsConfigured] = useState(false);
  const [healthStatus, setHealthStatus] = useState<string>('checking...');

  useEffect(() => {
    // Validate and configure API client on mount
    // This is initial configuration, not a cascading effect
    // eslint-disable-next-line react-hooks/exhaustive-deps
    try {
      validateConfig();
      configureApiClient();
      setIsConfigured(true);

      // Test API connection
      HealthService.healthCheckHealthGet()
        .then((response) => {
          setHealthStatus(response.status || 'healthy');
        })
        .catch((error) => {
          console.error('Health check failed:', error);
          setHealthStatus('unhealthy');
        });
    } catch (error) {
      console.error('Configuration error:', error);
      setIsConfigured(false);
    }
  }, []);

  if (!isConfigured) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Configuration Error</h1>
          <p className="mt-2 text-gray-600">Check console for details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main role="main">
        <Container className="py-8">
          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Welcome to Consensus Engine
            </h2>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">API Status:</span>
                <StatusBadge status={healthStatus === 'healthy' ? 'completed' : 'failed'} />
                <span className="text-sm text-gray-600">{healthStatus}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">API Base URL:</span>
                <code className="rounded bg-gray-100 px-2 py-1 text-sm text-gray-800">
                  {config.apiBaseUrl}
                </code>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Environment:</span>
                <span className="text-sm font-medium text-gray-900">{config.environment}</span>
              </div>
            </div>
            <div className="mt-6">
              <Button
                onClick={() => {
                  console.log('Button clicked');
                }}
              >
                Get Started
              </Button>
            </div>
          </div>
        </Container>
      </main>
    </div>
  );
}

export default App;
