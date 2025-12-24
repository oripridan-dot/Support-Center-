'use client';

import React, { useEffect, useState } from 'react';

interface BrandProgress {
  brand_id: number;
  status: 'discovering' | 'processing' | 'complete';
  urls_discovered: number;
  documents_ingested: number;
  start_time: string;
  end_time?: string;
}

interface IngestionStatus {
  is_running: boolean;
  current_brand: string | null;
  current_step: string | null;
  total_documents: number;
  documents_by_brand: Record<string, number>;
  urls_discovered: number;
  urls_processed: number;
  progress_percent: number;
  last_updated: string;
  errors: Array<{ timestamp: string; message: string }>;
  start_time?: string;
  estimated_completion?: string;
  brand_progress: Record<string, BrandProgress>;
}

export default function IngestionMonitor() {
  const [status, setStatus] = useState<IngestionStatus | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    let wsAttempted = false;
    let wsConnected = false;
    let cleanupPolling: (() => void) | null = null;
    
    const setupPolling = () => {
      // Fallback to polling if WebSocket is not available
      const interval = setInterval(async () => {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
          const response = await fetch(`${apiUrl}/ingestion/status`);
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
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
        const wsBaseUrl = apiUrl.replace(/^https?:\/\//, '').replace(/\/api$/, '');
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



  if (!status || !isVisible) return null;

  const brandCounts = Object.entries(status.documents_by_brand).map(([brand, count]) => {
    const progress = status.brand_progress[brand];
    const statusEmoji = progress?.status === 'complete' ? '✅' : progress?.status === 'processing' ? '⚙️' : '🔍';
    
    return (
      <div key={brand} className="flex justify-between items-center text-sm mb-2 p-2 bg-gray-50 rounded">
        <div>
          <span className="text-gray-600">{statusEmoji} {brand}</span>
          {progress && (
            <p className="text-xs text-gray-400">
              {progress.urls_discovered} URLs, {progress.documents_ingested} docs
            </p>
          )}
        </div>
        <span className="font-semibold text-blue-600">{count} docs</span>
      </div>
    );
  });

  return (
    <div className="fixed bottom-6 right-6 w-96 bg-white rounded-lg shadow-2xl p-6 z-50 border-l-4 border-blue-500">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-gray-800">
          {status.is_running ? '🔄 Ingesting...' : '✅ Ingestion Complete'}
        </h3>
        <button
          onClick={() => setIsVisible(false)}
          className="text-gray-400 hover:text-gray-600 text-xl"
        >
          ✕
        </button>
      </div>

      {status.current_brand && (
        <div className="mb-4 p-3 bg-blue-50 rounded">
          <p className="text-sm text-gray-600">Current Brand</p>
          <p className="font-semibold text-blue-700">{status.current_brand}</p>
          {status.current_step && (
            <p className="text-xs text-gray-500 mt-1">{status.current_step}</p>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-2">
          <span className="text-gray-600">Progress</span>
          <span className="font-semibold text-gray-800">{status.progress_percent.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-gradient-to-r from-blue-400 to-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${status.progress_percent}%` }}
          />
        </div>
      </div>

      {/* Document Stats */}
      <div className="mb-4">
        <p className="text-xs text-gray-600 mb-2 font-semibold uppercase">Documents by Brand</p>
        <div className="max-h-48 overflow-y-auto">
          {brandCounts.length > 0 ? brandCounts : <p className="text-xs text-gray-400">No documents yet</p>}
        </div>
      </div>

      {/* Overall Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4 text-center text-xs">
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-gray-600">Total Docs</p>
          <p className="font-bold text-lg text-gray-800">{status.total_documents}</p>
        </div>
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-gray-600">URLs Found</p>
          <p className="font-bold text-lg text-gray-800">{status.urls_discovered}</p>
        </div>
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-gray-600">Processed</p>
          <p className="font-bold text-lg text-gray-800">{status.urls_processed}</p>
        </div>
      </div>

      {/* Errors */}
      {status.errors.length > 0 && (
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
      <p className="text-xs text-gray-400">
        Last updated: {status.last_updated ? new Date(status.last_updated).toLocaleTimeString() : 'N/A'}
      </p>
    </div>
  );
}
