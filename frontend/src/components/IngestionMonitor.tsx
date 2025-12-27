import { useEffect, useState } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Loader2 } from 'lucide-react';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface BrandProgress {
  brand_id: number;
  status: 'discovering' | 'processing' | 'complete' | 'failed' | 'idle';
  urls_discovered: number;
  documents_ingested: number;
  start_time: string;
  end_time?: string;
}

interface IngestionStatus {
  is_running: boolean;
  current_brand: string | null;
  current_step: string | null;
  current_document?: string | null;
  total_documents: number;
  current_brand_documents?: number;
  current_brand_target?: number;
  current_brand_progress?: number;
  documents_by_brand: Record<string, number>;
  urls_discovered: number;
  urls_processed: number;
  progress_percent: number;
  last_updated: string;
  errors: Array<{ timestamp: string; message: string }>;
  start_time?: string;
  estimated_completion?: string;
  brand_progress: Record<string, BrandProgress & { document_count?: number }>;
}

interface IngestionMonitorProps {
  variant?: 'floating' | 'sidebar';
}

export default function IngestionMonitor({ variant = 'floating' }: IngestionMonitorProps) {
  const [status, setStatus] = useState<IngestionStatus | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    let wsAttempted = false;
    let wsConnected = false;
    let cleanupPolling: (() => void) | null = null;
    
    const setupPolling = () => {
      // Fallback to polling if WebSocket is not available
      const interval = setInterval(async () => {
        try {
          const response = await fetch('/api/ingestion/status');
          const data: IngestionStatus = await response.json();
          setStatus(data);
          
          // Auto-show when ingestion starts
          if (data.is_running && !isVisible) {
            setIsVisible(true);
          }
          // Auto-hide when complete
          if (!data.is_running && data.progress_percent === 100) {
            setTimeout(() => setIsVisible(false), 3000);
          }
        } catch (error) {
          console.error('Failed to fetch ingestion status:', error);
        }
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    };
    
    // Try WebSocket if not in dev environment
    const tryWebSocket = () => {
      if (wsAttempted || typeof window === 'undefined') return;
      wsAttempted = true;
      
      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsBaseUrl = window.location.host;
        const wsUrl = `${wsProtocol}//${wsBaseUrl}/api/ingestion/ws/status`;
        
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
          wsConnected = true;
          setWs(socket);
          // Stop polling if WebSocket connects
          if (cleanupPolling) {
            cleanupPolling();
            cleanupPolling = null;
          }
        };
        
        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setStatus(data);
            
            if (data.is_running && !isVisible) {
              setIsVisible(true);
            }
            if (!data.is_running && data.progress_percent === 100) {
              setTimeout(() => setIsVisible(false), 3000);
            }
          } catch (error) {
            console.log('Parse error, using polling');
          }
        };
        
        socket.onerror = () => {
          if (!wsConnected && !cleanupPolling) {
            cleanupPolling = setupPolling();
          }
        };
        
        socket.onclose = () => {
          if (wsConnected && !cleanupPolling) {
            cleanupPolling = setupPolling();
          }
        };
      } catch (error) {
        if (!cleanupPolling) {
          cleanupPolling = setupPolling();
        }
      }
    };
    
    // Start with polling, try WebSocket after initial fetch
    cleanupPolling = setupPolling();
    setTimeout(tryWebSocket, 500);
    
    // Cleanup on unmount
    return () => {
      if (cleanupPolling) cleanupPolling();
      if (ws) ws.close();
    };
  }, []);



  if (!status || (!isVisible && variant === 'floating')) return null;
  
  // if (variant === 'sidebar' && !isVisible) return null; // Always show in sidebar to allow starting

  const handleStartIngestion = async () => {
    if (isStarting) return;
    setIsStarting(true);
    try {
      await fetch('/api/ingestion/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ force_rescan: false }),
      });
      // Optimistically show visibility
      setIsVisible(true);
    } catch (error) {
      console.error('Failed to start ingestion:', error);
    } finally {
      // Keep loading state for a moment to prevent flickering until next poll/ws update
      setTimeout(() => setIsStarting(false), 1000);
    }
  };

  const brandCounts = Object.entries(status?.brand_progress || {}).map(([brand, progress]) => {
    const count = progress.document_count || 0;
    const statusEmoji = progress.status === 'complete' ? '✅' : progress.status === 'processing' ? '⚙️' : progress.status === 'idle' ? '⏸' : '🔍';
    
    // Only show brands with documents or currently processing
    if (count === 0 && progress.status !== 'processing') return null;
    
    return (
      <div key={brand} className="flex justify-between items-center text-xs mb-1 p-1.5 bg-gray-50 rounded">
        <div className="flex-1 truncate mr-2">
          <span className="text-gray-600">{statusEmoji} {brand}</span>
        </div>
        <span className="font-semibold text-blue-600 whitespace-nowrap">{count}</span>
      </div>
    );
  }).filter(Boolean);

  // Don't render until we have status data
  if (!status) {
    return null;
  }

  return (
    <div className={cn(
      "bg-white transition-all duration-300",
      variant === 'floating' 
        ? "fixed bottom-6 right-6 w-96 rounded-lg shadow-2xl p-6 z-50 border-l-4 border-blue-500" 
        : "w-full border-t border-gray-100 p-4 bg-gray-50 flex-1 flex flex-col"
    )}>
      <div className="flex justify-between items-center mb-3">
        <h3 className={cn("font-bold text-gray-800", variant === 'sidebar' ? "text-sm" : "text-lg")}>
          {status.is_running ? '🔄 Ingesting...' : 'Ingestion Ready'}
        </h3>
        <div className="flex items-center gap-2">
          {!status.is_running && (
            <button
              onClick={handleStartIngestion}
              disabled={isStarting}
              className={cn(
                "px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors flex items-center gap-1 shadow-sm",
                isStarting && "opacity-70 cursor-not-allowed"
              )}
              title="Start Ingestion"
            >
              {isStarting ? (
                <>
                  <Loader2 size={12} className="animate-spin" />
                  <span>Starting...</span>
                </>
              ) : (
                <>
                  <span>▶</span> Start
                </>
              )}
            </button>
          )}
          {variant === 'floating' && (
            <button
              onClick={() => setIsVisible(false)}
              className="text-gray-400 hover:text-gray-600 text-xl"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {status.current_brand && (
        <div className="mb-3 p-2 bg-blue-50 rounded flex-1 flex flex-col">
          <p className="text-xs text-gray-600">Current Brand</p>
          <p className="font-semibold text-blue-700 text-sm truncate">{status.current_brand}</p>
          {status.current_brand_documents !== undefined && status.current_brand_target !== undefined && (
            <div className="mt-2">
              <div className="flex justify-between text-[10px] mb-1">
                <span className="text-gray-600">Docs</span>
                <span className="font-semibold text-blue-600">
                  {status.current_brand_documents}/{status.current_brand_target}
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-1">
                <div
                  className="bg-blue-600 h-1 rounded-full transition-all"
                  style={{ width: `${Math.min((status.current_brand_documents / status.current_brand_target) * 100, 100)}%` }}
                />
              </div>
            </div>
          )}
          {status.current_step && variant === 'floating' && (
            <p className="text-xs text-gray-500 mt-1">{status.current_step}</p>
          )}
          {status.current_document && (
            <div className="mt-auto pt-2 border-t border-blue-100">
              <p className="text-[10px] text-gray-500 uppercase font-bold mb-1">Processing Document</p>
              <p className="text-[10px] text-blue-600 break-all leading-tight" title={status.current_document}>
                {status.current_document}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-gray-600">Total Progress</span>
          <span className="font-semibold text-gray-800">{(status.progress_percent || 0).toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all duration-300 ${(status.progress_percent || 0) >= 100 ? 'bg-green-500' : 'bg-gradient-to-r from-blue-400 to-blue-600'}`}
            style={{ width: `${status.progress_percent || 0}%` }}
          />
        </div>
      </div>

      {/* Document Stats - Only show in floating */}
      {variant === 'floating' && (
        <div className="mb-4">
          <p className="text-xs text-gray-600 mb-2 font-semibold uppercase">Documents by Brand</p>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {brandCounts.length > 0 ? brandCounts : <p className="text-xs text-gray-400 p-2">No documents yet</p>}
          </div>
        </div>
      )}
      
      {/* Overall Stats */}
      <div className="grid grid-cols-2 gap-2 mb-2 text-center text-xs">
        <div className="bg-gray-50 p-1.5 rounded">
          <p className="text-gray-500 text-[10px]">Total</p>
          <p className="font-bold text-gray-800">{status.total_documents || 0}</p>
        </div>
        <div className="bg-gray-50 p-1.5 rounded">
          <p className="text-gray-500 text-[10px]">Done</p>
          <p className="font-bold text-gray-800">{(status.progress_percent || 0).toFixed(0)}%</p>
        </div>
      </div>

      {/* Errors */}
      {status.errors && status.errors.length > 0 && variant === 'floating' && (
        <div className="mb-4 p-3 bg-red-50 rounded border border-red-200">
          <p className="text-xs font-semibold text-red-700 mb-2">Recent Errors ({status.errors.length})</p>
          <div className="max-h-24 overflow-y-auto">
            {status.errors.slice(-3).map((error, idx) => (
              <p key={idx} className="text-xs text-red-600 mb-1">
                • {error.message}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Last Updated */}
      <p className="text-[10px] text-gray-400 text-center mt-2">
        Updated: {status.last_updated ? new Date(status.last_updated).toLocaleTimeString() : 'N/A'}
      </p>
    </div>
  );
}
