import { useState, useEffect } from 'react';
import { 
  Activity, Loader2, CheckCircle2, AlertCircle, Clock, TrendingUp, 
  Zap, Shield, RefreshCw, Server, CircuitBoard, BarChart3, Play, Square
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface WorkerMetrics {
  timestamp: string;
  workers: {
    [category: string]: {
      count: number;
      active: number;
    };
  };
  queue_sizes: {
    [category: string]: number;
  };
  processed: {
    [category: string]: number;
  };
  failed: {
    [category: string]: number;
  };
  retries: {
    [category: string]: number;
  };
  avg_duration_ms: {
    [category: string]: number;
  };
  success_rate: {
    [category: string]: number;
  };
  circuit_breakers: {
    [name: string]: {
      name: string;
      state: string;
      failure_count: number;
      success_count: number;
      last_failure: string | null;
    };
  };
}

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  total_workers: number;
  active_workers: number;
  total_processed: number;
  total_failed: number;
  overall_success_rate: number;
  alerts: string[];
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function HighPerformanceMonitor() {
  const [metrics, setMetrics] = useState<WorkerMetrics | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval] = useState(2000); // 2 seconds
  const [isRunning, setIsRunning] = useState(false);
  const [selectedBrand, setSelectedBrand] = useState<string>('all');
  const [brands, setBrands] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<string[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>('');


  // Fetch brands list
  useEffect(() => {
    fetch('/api/brands', { signal: AbortSignal.timeout(30000) })
      .then(res => res.json())
      .then(data => setBrands(data))
      .catch(err => {
        console.error('Failed to fetch brands:', err);
        setBrands([]);
      });
  }, []);

  // Pipeline control handlers
  const handleStartPipeline = async () => {
    try {
      const brandId = selectedBrand === 'all' ? null : parseInt(selectedBrand);
      const params = brandId ? `?brand_id=${brandId}` : '';
      const response = await fetch(`/api/hp/pipeline/start${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        setIsRunning(true);
      } else {
        const error = await response.json();
        alert(`Failed to start HP pipeline: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to start HP pipeline:', err);
      alert('Error starting HP pipeline');
    }
  };

  const handleStopPipeline = async () => {
    try {
      await fetch('/api/hp/pipeline/stop', { method: 'POST' });
      setIsRunning(false);
    } catch (err) {
      console.error('Failed to stop HP pipeline:', err);
    }
  };

  // Fetch data
  const fetchData = async () => {
    try {
      const [statsRes, healthRes, pipelineRes, activityRes] = await Promise.all([
        fetch('/api/hp/stats', { signal: AbortSignal.timeout(30000) }),
        fetch('/api/hp/health', { signal: AbortSignal.timeout(30000) }),
        fetch('/api/hp/pipeline/status', { signal: AbortSignal.timeout(30000) }),
        fetch('/api/hp/activity?limit=5', { signal: AbortSignal.timeout(30000) })
      ]);

      if (statsRes.ok && healthRes.ok) {
        const statsData = await statsRes.json();
        const healthData = await healthRes.json();
        const pipelineData = pipelineRes.ok ? await pipelineRes.json() : { is_running: false };
        const activityData = activityRes.ok ? await activityRes.json() : { events: [] };
        
        console.log('HP Stats:', statsData);
        console.log('HP Health:', healthData);
        console.log('HP Pipeline Status:', pipelineData);
        console.log('HP Activity:', activityData);
        
        // Transform HP stats to match expected metrics format
        const workersByCategory: { [key: string]: { count: number; active: number } } = {};
        
        // Get queue sizes and completed metrics
        const queues = statsData.queues || {};
        const completed = statsData.metrics?.completed || {};
        
        Object.entries(statsData.workers?.by_category || {}).forEach(([category, count]) => {
          const categoryKey = category.toUpperCase();
          const queueSize = queues[category] || 0;
          const completedCount = completed[category] || 0;
          
          // Show workers as "active" if they have queue OR have completed work
          let activeWorkers = 0;
          if (queueSize > 0) {
            activeWorkers = Math.min(queueSize, count as number);
          } else if (completedCount > 0) {
            // If tasks were completed, show some workers were active
            activeWorkers = Math.min(Math.ceil(completedCount / 10), count as number);
          }
          
          workersByCategory[categoryKey] = {
            count: count as number,
            active: activeWorkers
          };
        });
        
        // Handle null metrics gracefully
        const completedMetrics = statsData.metrics?.completed || {};
        const failedMetrics = statsData.metrics?.failed || {};
        const retriesMetrics = statsData.metrics?.retries || {};
        const avgDurationMetrics = statsData.metrics?.avg_duration || {};
        
        // Normalize all metric keys to UPPERCASE to match workers keys
        const normalizeKeys = (obj: any) => {
          const normalized: any = {};
          Object.entries(obj).forEach(([key, val]) => {
            normalized[key.toUpperCase()] = val;
          });
          return normalized;
        };
        
        const transformedMetrics: WorkerMetrics = {
          timestamp: new Date().toISOString(),
          workers: workersByCategory,
          queue_sizes: normalizeKeys(statsData.queues || {}),
          processed: normalizeKeys(completedMetrics),
          failed: normalizeKeys(failedMetrics),
          retries: normalizeKeys(retriesMetrics),
          avg_duration_ms: Object.entries(avgDurationMetrics).reduce((acc, [key, val]) => {
            acc[key.toUpperCase()] = val ? (val as number) * 1000 : 0;
            return acc;
          }, {} as { [key: string]: number }),
          success_rate: Object.keys(workersByCategory).reduce((acc, key) => {
            const lowerKey = key.toLowerCase();
            const completed = (completedMetrics[lowerKey] || 0) as number;
            const failed = (failedMetrics[lowerKey] || 0) as number;
            const total = completed + failed;
            acc[lowerKey] = total > 0 ? completed / total : 1.0;
            return acc;
          }, {} as { [key: string]: number }),
          circuit_breakers: statsData.circuit_breakers || {}
        };
        
        const totalCompleted = Object.values(completedMetrics).reduce((a: number, b) => a + ((b as number) || 0), 0);
        const totalFailed = Object.values(failedMetrics).reduce((a: number, b) => a + ((b as number) || 0), 0);
        const totalProcessed = totalCompleted + totalFailed;
        
        const transformedHealth: HealthStatus = {
          status: healthData.healthy ? 'healthy' : 'degraded',
          timestamp: new Date().toISOString(),
          total_workers: healthData.workers?.total || 22,
          active_workers: statsData.active_tasks || 0,  // Use active_tasks from stats
          total_processed: totalCompleted,
          total_failed: totalFailed,
          overall_success_rate: totalProcessed > 0 ? totalCompleted / totalProcessed : 1.0,
          alerts: []
        };
        
        // Add alerts based on circuit breaker states
        Object.entries(healthData.circuit_breakers || {}).forEach(([name, state]) => {
          if (state === 'open') {
            transformedHealth.alerts.push(`Circuit breaker ${name} is OPEN`);
          }
        });
        
        setMetrics(transformedMetrics);
        setHealth(transformedHealth);
        setLoading(false);
        setLastUpdated(new Date().toLocaleTimeString());
        
        // Check if HP pipeline is actually running from backend
        const actuallyRunning = pipelineData.is_running === true;
        setIsRunning(actuallyRunning);
        
        // Update activity log from real activity logger
        if (activityData.events && activityData.events.length > 0) {
          const activities = activityData.events.map((event: any) => event.message);
          setRecentActivity(activities);
        } else if (pipelineData.progress && pipelineData.progress.activity_log) {
          const activities = pipelineData.progress.activity_log.map((item: any) => 
            `${item.message}`
          );
          setRecentActivity(activities);
        } else if (pipelineData.database) {
          // Fallback to database stats if no activity log
          const dbStats = `📊 Database: ${pipelineData.database.total_documents} docs | ${pipelineData.database.brands_with_documentation}/${pipelineData.database.total_brands} brands (${pipelineData.database.coverage_percentage}%)`;
          setRecentActivity([dbStats]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch HP worker data:', error);
      setLoading(false);
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    fetchData();

    if (autoRefresh) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  // Manual refresh
  const handleRefresh = () => {
    setLoading(true);
    fetchData();
  };

  if (loading || !metrics || !health) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Pipeline Control Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
              <Activity className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">Worker Pipeline</h2>
              <p className="text-blue-100 text-sm">100% Documentation Coverage Mission</p>
            </div>
          </div>
          
          <div className={`px-4 py-2 rounded-lg backdrop-blur-sm flex items-center gap-2 ${
            isRunning ? 'bg-green-500/30' : 'bg-white/20'
          }`}>
            <Clock className="w-4 h-4" />
            <span className="font-semibold">{isRunning ? 'RUNNING' : 'IDLE'}</span>
          </div>
        </div>
        
        {/* Controls */}
        <div className="flex items-center gap-4 mt-6">
          <select
            value={selectedBrand}
            onChange={(e) => setSelectedBrand(e.target.value)}
            disabled={isRunning}
            className="flex-grow bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl px-4 py-3 text-white placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-white/50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="all" className="text-gray-900">All Brands</option>
            {brands.map((brand) => (
              <option key={brand.id} value={brand.id} className="text-gray-900">
                {brand.name}
              </option>
            ))}
          </select>
          
          {!isRunning ? (
            <button
              onClick={handleStartPipeline}
              className="px-6 py-3 bg-white text-blue-600 font-semibold rounded-xl hover:bg-blue-50 transition-all flex items-center gap-2 shadow-lg"
            >
              <Play className="w-5 h-5" />
              Start Pipeline
            </button>
          ) : (
            <button
              onClick={handleStopPipeline}
              className="px-6 py-3 bg-red-500 text-white font-semibold rounded-xl hover:bg-red-600 transition-all flex items-center gap-2 shadow-lg"
            >
              <Square className="w-5 h-5" />
              Stop
            </button>
          )}
          
          <button
            onClick={handleRefresh}
            className="px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl hover:bg-white/20 transition-all"
            title="Refresh metrics"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-gray-900">Real-Time Monitoring</h3>
          <p className="text-sm text-gray-500 mt-1">22 specialized workers across 5 categories</p>
        </div>
        
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-xs text-gray-500">
              Last updated: {lastUpdated}
            </span>
          )}
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh ({refreshInterval / 1000}s)
          </label>
        </div>
      </div>

      {/* Health Status Card */}
      <HealthCard health={health} />

      {/* Worker Pool Grid */}
      <WorkerPoolGrid metrics={metrics} />

      {/* Circuit Breakers */}
      <CircuitBreakerStatus metrics={metrics} />

      {/* Performance Metrics */}
      <PerformanceMetrics metrics={metrics} />

      {/* Recent Activity */}
      {recentActivity.length > 0 && <RecentActivity activity={recentActivity} />}

      {/* Alerts */}
      {health.alerts.length > 0 && <AlertsSection alerts={health.alerts} />}
    </div>
  );
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

function HealthCard({ health }: { health: HealthStatus }) {
  const statusConfig = {
    healthy: { color: 'bg-green-500', icon: CheckCircle2, text: 'Healthy' },
    degraded: { color: 'bg-yellow-500', icon: AlertCircle, text: 'Degraded' },
    unhealthy: { color: 'bg-red-500', icon: AlertCircle, text: 'Unhealthy' }
  };

  const config = statusConfig[health.status];
  const StatusIcon = config.icon;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 ${config.color} rounded-xl flex items-center justify-center`}>
            <StatusIcon className="w-8 h-8 text-white" />
          </div>
          
          <div>
            <h3 className="text-2xl font-bold text-gray-900">{config.text}</h3>
            <p className="text-sm text-gray-500">System Status</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <Stat label="Workers" value={`${health.active_workers}/${health.total_workers}`} />
          <Stat label="Success Rate" value={`${(health.overall_success_rate * 100).toFixed(1)}%`} />
          <Stat label="Processed" value={health.total_processed.toLocaleString()} />
          <Stat label="Failed" value={health.total_failed.toLocaleString()} />
        </div>
      </div>
    </div>
  );
}

function WorkerPoolGrid({ metrics }: { metrics: WorkerMetrics }) {
  const categories = Object.keys(metrics.workers || {});

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {categories.map((category) => (
        <WorkerPoolCard
          key={category}
          category={category}
          workers={metrics.workers[category] || { count: 0, active: 0 }}
          queueSize={metrics.queue_sizes?.[category] || 0}
          processed={metrics.processed?.[category] || 0}
          failed={metrics.failed?.[category] || 0}
          successRate={metrics.success_rate?.[category] || 1.0}
          avgDuration={metrics.avg_duration_ms?.[category] || 0}
        />
      ))}
    </div>
  );
}

function WorkerPoolCard({
  category,
  workers,
  queueSize,
  processed,
  failed: _failed,
  successRate,
  avgDuration
}: {
  category: string;
  workers: { count: number; active: number };
  queueSize: number;
  processed: number;
  failed: number;
  successRate: number;
  avgDuration: number;
}) {
  const categoryIcons: { [key: string]: any } = {
    RAG_QUERY: Zap,
    SCRAPING: Activity,
    EMBEDDING: CircuitBoard,
    INGESTION: Server,
    BATCH: BarChart3,
    MAINTENANCE: Clock
  };

  const Icon = categoryIcons[category] || Activity;

  const categoryColors: { [key: string]: string } = {
    RAG_QUERY: 'bg-purple-500',
    SCRAPING: 'bg-blue-500',
    EMBEDDING: 'bg-green-500',
    INGESTION: 'bg-orange-500',
    BATCH: 'bg-pink-500',
    MAINTENANCE: 'bg-gray-500'
  };

  const color = categoryColors[category] || 'bg-gray-500';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="font-semibold text-gray-900">{category.replace(/_/g, ' ')}</h4>
            <p className="text-sm text-gray-500">{workers.count} workers</p>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{workers.active}</div>
          <div className="text-xs text-gray-500">active</div>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Queue:</span>
          <span className={`font-semibold ${queueSize > 50 ? 'text-orange-600' : 'text-gray-900'}`}>
            {queueSize}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Processed:</span>
          <span className="font-semibold text-gray-900">{processed.toLocaleString()}</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Success Rate:</span>
          <span className={`font-semibold ${successRate < 0.95 ? 'text-red-600' : 'text-green-600'}`}>
            {(successRate * 100).toFixed(1)}%
          </span>
        </div>
        
        {avgDuration > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-600">Avg Duration:</span>
            <span className="font-semibold text-gray-900">{avgDuration.toFixed(0)}ms</span>
          </div>
        )}
      </div>
    </div>
  );
}

function CircuitBreakerStatus({ metrics }: { metrics: WorkerMetrics }) {
  const breakers = Object.values(metrics.circuit_breakers);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-4">
        <Shield className="w-6 h-6 text-blue-500" />
        <h3 className="text-lg font-semibold text-gray-900">Circuit Breakers</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {breakers.map((breaker) => (
          <div key={breaker.name} className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-gray-900 capitalize">{breaker.name}</span>
              <CircuitBreakerBadge state={breaker.state} />
            </div>
            
            <div className="text-sm space-y-1">
              <div className="flex justify-between text-gray-600">
                <span>Failures:</span>
                <span className={breaker.failure_count > 0 ? 'text-red-600 font-semibold' : ''}>
                  {breaker.failure_count}
                </span>
              </div>
              {breaker.state === 'half_open' && (
                <div className="flex justify-between text-gray-600">
                  <span>Successes:</span>
                  <span className="text-green-600 font-semibold">{breaker.success_count}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CircuitBreakerBadge({ state }: { state: string }) {
  const stateConfig: { [key: string]: { color: string; text: string } } = {
    closed: { color: 'bg-green-100 text-green-800', text: 'Closed' },
    open: { color: 'bg-red-100 text-red-800', text: 'Open' },
    half_open: { color: 'bg-yellow-100 text-yellow-800', text: 'Testing' }
  };

  const config = stateConfig[state] || stateConfig.closed;

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.text}
    </span>
  );
}

function PerformanceMetrics({ metrics }: { metrics: WorkerMetrics }) {
  const totalProcessed = Object.values(metrics.processed).reduce((a, b) => a + b, 0);
  const totalFailed = Object.values(metrics.failed).reduce((a, b) => a + b, 0);
  const totalRetries = Object.values(metrics.retries).reduce((a, b) => a + b, 0);
  
  const avgDuration = totalProcessed > 0
    ? Object.values(metrics.avg_duration_ms).reduce((a, b) => a + b, 0) / 
      Object.values(metrics.avg_duration_ms).filter(d => d > 0).length
    : 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-4">
        <TrendingUp className="w-6 h-6 text-green-500" />
        <h3 className="text-lg font-semibold text-gray-900">Performance Metrics</h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <MetricCard
          label="Total Processed"
          value={totalProcessed.toLocaleString()}
          color="text-blue-600"
        />
        <MetricCard
          label="Total Failed"
          value={totalFailed.toLocaleString()}
          color="text-red-600"
        />
        <MetricCard
          label="Retries"
          value={totalRetries.toLocaleString()}
          color="text-orange-600"
        />
        <MetricCard
          label="Avg Duration"
          value={`${avgDuration.toFixed(0)}ms`}
          color="text-green-600"
        />
      </div>
    </div>
  );
}

function AlertsSection({ alerts }: { alerts: string[] }) {
  return (
    <div className="bg-orange-50 border border-orange-200 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <AlertCircle className="w-6 h-6 text-orange-600" />
        <h3 className="text-lg font-semibold text-orange-900">Active Alerts</h3>
      </div>

      <ul className="space-y-2">
        {alerts.map((alert, index) => (
          <li key={index} className="flex items-start gap-2 text-sm text-orange-800">
            <span className="font-semibold">•</span>
            <span>{alert}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RecentActivity({ activity }: { activity: string[] }) {
  return (
    <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-700 p-6">
      <div className="flex items-center gap-3 mb-4">
        <Activity className="w-6 h-6 text-blue-400" />
        <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
        <span className="text-xs text-slate-400 ml-auto">Last {activity.length} events</span>
      </div>

      <div className="bg-slate-950 rounded-lg p-4 max-h-96 overflow-y-auto">
        <ul className="space-y-1 font-mono text-xs">
          {activity.slice().reverse().map((event, index) => (
            <li key={index} className="text-slate-300 hover:text-white hover:bg-slate-800 px-2 py-1 rounded transition-colors">
              {event}
            </li>
          ))}
          {activity.length === 0 && (
            <li className="text-slate-500 italic">No recent activity</li>
          )}
        </ul>
      </div>
    </div>
  );
}

// Helper components
function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="text-center">
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      <div className="text-sm text-gray-600 mt-1">{label}</div>
    </div>
  );
}
