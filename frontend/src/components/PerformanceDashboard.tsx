/**
 * Performance Dashboard Component
 * Displays real-time metrics from the lightweight implementation
 */

import React, { useEffect, useState } from 'react';
import { apiV2Endpoints } from '../lib/api';
import AsyncScrapingInterface from './AsyncScrapingInterface';

interface MetricsData {
  total_requests: number;
  avg_duration_ms: number;
  max_duration_ms: number;
  min_duration_ms: number;
  requests_per_minute: number;
  error_rate_percent: number;
  status_codes: Record<string, number>;
  top_endpoints: Record<string, number>;
  methods: Record<string, number>;
}

interface CacheStats {
  total_entries: number;
  total_size_mb: number;
  cache_hits: number;
  cache_misses: number;
  hit_rate_percent: number;
  cache_dir: string;
}

interface QueueStatus {
  workers: number;
  queue_size: number;
  total_tasks: number;
  status_breakdown: Record<string, number>;
  running: boolean;
}

export const PerformanceDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [cache, setCache] = useState<CacheStats | null>(null);
  const [queue, setQueue] = useState<QueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [metricsData, cacheData, queueData] = await Promise.all([
        apiV2Endpoints.metricsStats(100),
        apiV2Endpoints.cacheStats(),
        apiV2Endpoints.queueStatus(),
      ]);

      setMetrics(metricsData as MetricsData);
      setCache(cacheData as CacheStats);
      setQueue(queueData as QueueStatus);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const clearCache = async () => {
    try {
      await apiV2Endpoints.clearCache();
      await fetchData(); // Refresh data
    } catch (err) {
      setError('Failed to clear cache');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error}</p>
        <button
          onClick={fetchData}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Performance Dashboard</h2>
        <div className="flex gap-2">
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Refresh
          </button>
          <button
            onClick={clearCache}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
          >
            Clear Cache
          </button>
        </div>
      </div>

      {/* Metrics Overview */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Requests"
            value={metrics.total_requests || 0}
            icon="📊"
          />
          <MetricCard
            title="Avg Response Time"
            value={`${(metrics.avg_duration_ms || 0).toFixed(2)}ms`}
            icon="⚡"
            color="text-blue-600"
          />
          <MetricCard
            title="Error Rate"
            value={`${(metrics.error_rate_percent || 0).toFixed(1)}%`}
            icon="⚠️"
            color={(metrics.error_rate_percent || 0) > 5 ? 'text-red-600' : 'text-green-600'}
          />
          <MetricCard
            title="Requests/Min"
            value={(metrics.requests_per_minute || 0).toFixed(1)}
            icon="🚀"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cache Stats */}
        {cache && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span>💾</span> Cache Statistics
            </h3>
            <div className="space-y-3">
              <StatRow label="Total Entries" value={cache.total_entries || 0} />
              <StatRow label="Total Size" value={`${(cache.total_size_mb || 0).toFixed(2)} MB`} />
              <StatRow label="Cache Hits" value={cache.cache_hits || 0} />
              <StatRow label="Cache Misses" value={cache.cache_misses || 0} />
              <StatRow
                label="Hit Rate"
                value={`${cache.hit_rate_percent || 0}%`}
                highlight={(cache.hit_rate_percent || 0) > 70}
              />
            </div>
          </div>
        )}

        {/* Queue Status */}
        {queue && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span>⚙️</span> Task Queue Status
            </h3>
            <div className="space-y-3">
              <StatRow label="Workers" value={queue.workers} />
              <StatRow label="Queue Size" value={queue.queue_size} />
              <StatRow label="Total Tasks" value={queue.total_tasks} />
              <StatRow
                label="Status"
                value={queue.running ? 'Running' : 'Stopped'}
                highlight={queue.running}
              />
              {Object.entries(queue.status_breakdown).map(([status, count]) => (
                <StatRow key={status} label={status} value={count} indent />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Status Codes & Top Endpoints */}
      {metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Status Codes</h3>
            <div className="space-y-2">
              {Object.entries(metrics.status_codes).map(([code, count]) => (
                <div key={code} className="flex justify-between items-center">
                  <span className={`font-mono ${getStatusColor(parseInt(code))}`}>
                    {code}
                  </span>
                  <span className="text-gray-600">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Top Endpoints</h3>
            <div className="space-y-2">
              {Object.entries(metrics.top_endpoints).slice(0, 10).map(([endpoint, count]) => (
                <div key={endpoint} className="flex justify-between items-center">
                  <span className="text-sm font-mono text-gray-700 truncate">
                    {endpoint}
                  </span>
                  <span className="text-gray-600">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Performance Range */}
      {metrics && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Response Time Range</h3>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="text-sm text-gray-600 mb-1">Min</div>
              <div className="text-2xl font-bold text-green-600">
                {(metrics.min_duration_ms || 0).toFixed(2)}ms
              </div>
            </div>
            <div className="flex-1">
              <div className="text-sm text-gray-600 mb-1">Avg</div>
              <div className="text-2xl font-bold text-blue-600">
                {(metrics.avg_duration_ms || 0).toFixed(2)}ms
              </div>
            </div>
            <div className="flex-1">
              <div className="text-sm text-gray-600 mb-1">Max</div>
              <div className="text-2xl font-bold text-red-600">
                {(metrics.max_duration_ms || 0).toFixed(2)}ms
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Async Scraping Interface */}
      <AsyncScrapingInterface />
    </div>
  );
};

// Helper Components
const MetricCard: React.FC<{
  title: string;
  value: string | number;
  icon: string;
  color?: string;
}> = ({ title, value, icon, color = 'text-gray-900' }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-600 mb-1">{title}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
      </div>
      <div className="text-4xl">{icon}</div>
    </div>
  </div>
);

const StatRow: React.FC<{
  label: string;
  value: string | number;
  highlight?: boolean;
  indent?: boolean;
}> = ({ label, value, highlight, indent }) => (
  <div className={`flex justify-between items-center ${indent ? 'pl-4' : ''}`}>
    <span className="text-gray-600">{label}</span>
    <span className={`font-semibold ${highlight ? 'text-green-600' : 'text-gray-900'}`}>
      {value}
    </span>
  </div>
);

const getStatusColor = (code: number): string => {
  if (code >= 200 && code < 300) return 'text-green-600';
  if (code >= 300 && code < 400) return 'text-blue-600';
  if (code >= 400 && code < 500) return 'text-yellow-600';
  return 'text-red-600';
};

export default PerformanceDashboard;
