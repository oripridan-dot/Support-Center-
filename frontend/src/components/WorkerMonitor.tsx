import { useState, useEffect } from 'react';
import { Activity, Loader2, CheckCircle2, XCircle, Clock, TrendingUp, Play, Pause, RefreshCw } from 'lucide-react';

interface WorkerTask {
  brand_id: number;
  brand_name: string;
  current_step: string;
  progress: number;
  total_items: number;
  completed_items: number;
  started_at: string;
}

interface WorkerState {
  status: 'idle' | 'running' | 'completed' | 'failed';
  current_task: WorkerTask | null;
  last_completed: string | null;
  stats: Record<string, any>;
}

interface WorkersStatus {
  explorer: WorkerState;
  scraper: WorkerState;
  ingester: WorkerState;
  recent_activity: string[];
  timestamp: string;
}

export default function WorkerMonitor({ integrated = false }: { integrated?: boolean }) {
  const [status, setStatus] = useState<WorkersStatus | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedBrand, setSelectedBrand] = useState<string>('all');
  const [brands, setBrands] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  console.log('WorkerMonitor integrated mode:', integrated);

  useEffect(() => {
    // Fetch brands list (non-blocking)
    fetch('/api/brands', { signal: AbortSignal.timeout(3000) })
      .then(res => res.json())
      .then(data => setBrands(data))
      .catch(err => console.error('Failed to fetch brands:', err));

    // Fetch initial status immediately
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/ingestion/workers-status', { 
          signal: AbortSignal.timeout(3000) 
        });
        const data = await response.json();
        setStatus(data);
        setLoading(false);
        
        const running = data.explorer.status === 'running' || 
                       data.scraper.status === 'running' || 
                       data.ingester.status === 'running';
        setIsRunning(running);
      } catch (err) {
        console.error('Failed to fetch worker status:', err);
        setError('Failed to connect to backend');
        setLoading(false);
        
        // Set default state so UI can render
        setStatus({
          explorer: { status: 'idle', current_task: null, last_completed: null, stats: {} },
          scraper: { status: 'idle', current_task: null, last_completed: null, stats: {} },
          ingester: { status: 'idle', current_task: null, last_completed: null, stats: {} },
          recent_activity: [],
          timestamp: new Date().toISOString()
        });
      }
    };

    // Fetch immediately on mount
    fetchStatus();

    // Use polling instead of WebSocket (WebSocket not implemented in backend yet)
    let pollingInterval: number | null = null;

    const startPolling = () => {
      if (pollingInterval) return;
      console.log('📡 Starting HTTP polling (every 3s)');
      pollingInterval = window.setInterval(fetchStatus, 3000);
    };

    // Start polling immediately
    startPolling();

    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, []);

  const handleStartPipeline = async () => {
    try {
      const brandId = selectedBrand === 'all' ? null : parseInt(selectedBrand);
      const response = await fetch('/api/ingestion/start-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brand_id: brandId })
      });
      
      if (response.ok) {
        setIsRunning(true);
      } else {
        alert('Failed to start pipeline');
      }
    } catch (err) {
      console.error('Failed to start pipeline:', err);
      alert('Error starting pipeline');
    }
  };

  const handleStopPipeline = async () => {
    try {
      await fetch('/api/ingestion/stop-pipeline', { method: 'POST' });
      setIsRunning(false);
    } catch (err) {
      console.error('Failed to stop pipeline:', err);
    }
  };

  // Show loading state
  if (loading && !status) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="animate-spin text-blue-500 mx-auto mb-4" size={40} />
            <p className="text-gray-600 font-medium">Loading Worker Pipeline...</p>
            <p className="text-sm text-gray-400 mt-2">Connecting to backend</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error && !status) {
    return (
      <div className="bg-white rounded-2xl border border-red-200 p-8">
        <div className="text-center">
          <XCircle className="text-red-500 mx-auto mb-4" size={40} />
          <h3 className="text-xl font-bold text-gray-900 mb-2">Connection Error</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Safe status with defaults
  const safeStatus = status || {
    explorer: { status: 'idle', current_task: null, last_completed: null, stats: {} },
    scraper: { status: 'idle', current_task: null, last_completed: null, stats: {} },
    ingester: { status: 'idle', current_task: null, last_completed: null, stats: {} },
    recent_activity: [],
    timestamp: new Date().toISOString()
  };

  const getStatusIcon = (workerStatus: string) => {
    switch (workerStatus) {
      case 'running':
        return <Loader2 className="animate-spin" size={18} />;
      case 'completed':
        return <CheckCircle2 size={18} className="text-green-500" />;
      case 'failed':
        return <XCircle size={18} className="text-red-500" />;
      default:
        return <Clock size={18} className="text-gray-400" />;
    }
  };

  const getStatusColor = (workerStatus: string) => {
    switch (workerStatus) {
      case 'running':
        return 'border-blue-500 bg-blue-50';
      case 'completed':
        return 'border-green-500 bg-green-50';
      case 'failed':
        return 'border-red-500 bg-red-50';
      default:
        return 'border-gray-200 bg-white';
    }
  };

  const WorkerCard = ({ 
    name, 
    icon, 
    color, 
    worker 
  }: { 
    name: string; 
    icon: string; 
    color: string; 
    worker: WorkerState;
  }) => (
    <div className={`rounded-xl border-2 transition-all ${getStatusColor(worker.status)} p-4`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-lg flex items-center justify-center text-xl font-bold shadow-sm"
            style={{ backgroundColor: color }}
          >
            {icon}
          </div>
          <div>
            <h3 className="font-bold text-gray-900">{name}</h3>
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              {worker.status === 'idle' ? 'Waiting' : worker.status}
            </p>
          </div>
        </div>
        {getStatusIcon(worker.status)}
      </div>

      {worker.current_task && (
        <div className="space-y-2">
          <div className="text-sm">
            <p className="font-bold text-gray-900">{worker.current_task.brand_name}</p>
            <p className="text-gray-600">{worker.current_task.current_step}</p>
          </div>

          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{worker.current_task.completed_items}/{worker.current_task.total_items}</span>
              <span>{worker.current_task.progress}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full transition-all duration-500 rounded-full"
                style={{ 
                  width: `${worker.current_task.progress}%`,
                  backgroundColor: color
                }}
              />
            </div>
          </div>
        </div>
      )}

      {!worker.current_task && worker.last_completed && (
        <div className="text-sm text-gray-600">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Last Completed</p>
          <p className="font-medium">{worker.last_completed}</p>
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-gray-200 grid grid-cols-2 gap-2">
        {Object.entries(worker.stats).slice(0, 2).map(([key, value]) => (
          <div key={key} className="text-center">
            <p className="text-lg font-black" style={{ color }}>{value}</p>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">
              {key.replace(/_/g, ' ')}
            </p>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="bg-white rounded-2xl border border-gray-200">
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-6 rounded-t-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Activity size={28} />
            <div>
              <h2 className="font-black text-2xl">Worker Pipeline</h2>
              <p className="text-sm opacity-90">100% Documentation Coverage Mission</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {isRunning ? (
              <div className="flex items-center gap-2 bg-white/20 px-4 py-2 rounded-lg animate-pulse">
                <Loader2 className="animate-spin" size={16} />
                <span className="font-bold text-sm">RUNNING</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-white/20 px-4 py-2 rounded-lg">
                <Clock size={16} />
                <span className="font-bold text-sm">IDLE</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <select
            value={selectedBrand}
            onChange={(e) => setSelectedBrand(e.target.value)}
            disabled={isRunning}
            className="flex-grow px-4 py-3 rounded-xl bg-white/20 backdrop-blur-sm text-white font-bold border-2 border-white/30 focus:outline-none focus:border-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="all">All Brands</option>
            {brands.map(brand => (
              <option key={brand.id} value={brand.id.toString()}>
                {brand.name}
              </option>
            ))}
          </select>

          {!isRunning ? (
            <button
              onClick={handleStartPipeline}
              className="flex items-center gap-3 px-6 py-3 bg-white text-blue-600 rounded-xl font-bold shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95"
            >
              <Play size={20} />
              Start Pipeline
            </button>
          ) : (
            <button
              onClick={handleStopPipeline}
              className="flex items-center gap-3 px-6 py-3 bg-red-500 text-white rounded-xl font-bold shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95"
            >
              <Pause size={20} />
              Stop
            </button>
          )}

          <button
            onClick={() => window.location.reload()}
            className="p-3 bg-white/20 hover:bg-white/30 rounded-xl transition-all"
            title="Refresh"
          >
            <RefreshCw size={20} />
          </button>
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <WorkerCard
            name="Explorer"
            icon="🔍"
            color="#3b82f6"
            worker={safeStatus.explorer}
          />
          <WorkerCard
            name="Scraper"
            icon="🤖"
            color="#8b5cf6"
            worker={safeStatus.scraper}
          />
          <WorkerCard
            name="Ingester"
            icon="📥"
            color="#10b981"
            worker={safeStatus.ingester}
          />
        </div>

        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6 mb-6">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp size={20} />
            Overall Progress
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-3xl font-black text-blue-600">
                {safeStatus.explorer.stats.brands_explored || 0}
              </p>
              <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">Brands Explored</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-black text-purple-600">
                {safeStatus.scraper.stats.docs_scraped_today || 0}
              </p>
              <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">Docs Scraped</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-black text-green-600">
                {safeStatus.ingester.stats.docs_ingested_today || 0}
              </p>
              <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">Docs Indexed</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-black text-orange-600">
                {safeStatus.ingester.stats.avg_coverage || 0}%
              </p>
              <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">Avg Coverage</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-900 text-gray-100 rounded-xl p-4 font-mono text-xs">
          <h3 className="font-bold mb-3 text-gray-400 uppercase tracking-wider flex items-center gap-2">
            <Activity size={14} />
            Recent Activity
          </h3>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {safeStatus.recent_activity.length > 0 ? (
              safeStatus.recent_activity.map((log, idx) => (
                <div key={idx} className="text-gray-300 py-0.5">{log}</div>
              ))
            ) : (
              <div className="text-gray-500 italic">No recent activity. Start the pipeline to begin ingestion.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

