/**
 * API Health Check Component
 * Shows connection status to backend
 */

import React, { useEffect, useState } from 'react';
import { checkHealth } from '../lib/api';

interface HealthStatus {
  status: string;
  checks: {
    task_queue: boolean;
    cache: boolean;
    metrics: boolean;
    chromadb: boolean;
  };
  timestamp: string;
}

export const ApiHealthCheck: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      // Try the new high-performance health endpoint first
      const response = await fetch('/api/hp/health');
      if (response.ok) {
        const data = await response.json();
        setHealth({
          status: data.status === 'healthy' ? 'healthy' : 'degraded',
          checks: {
            task_queue: true,
            cache: true,
            metrics: true,
            chromadb: data.status === 'healthy'
          },
          timestamp: data.timestamp
        });
        setError(null);
        setLoading(false);
        return;
      }
      
      // Fallback to old health check
      const data = await checkHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      setError('Backend connection failed');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-100">
        <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></div>
        <span className="text-xs text-gray-600">Checking...</span>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-100">
        <div className="w-2 h-2 rounded-full bg-red-500"></div>
        <span className="text-xs text-red-700">Offline</span>
      </div>
    );
  }

  const isHealthy = health.status === 'healthy';

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${
        isHealthy ? 'bg-green-100' : 'bg-yellow-100'
      }`}
    >
      <div
        className={`w-2 h-2 rounded-full ${
          isHealthy ? 'bg-green-500' : 'bg-yellow-500'
        } animate-pulse`}
      ></div>
      <span className={`text-xs ${isHealthy ? 'text-green-700' : 'text-yellow-700'}`}>
        {isHealthy ? 'Online' : 'Degraded'}
      </span>
    </div>
  );
};

export default ApiHealthCheck;
