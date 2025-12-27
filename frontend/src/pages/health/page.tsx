import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';

export default function HealthPage() {
  const [backendHealth, setBackendHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/health', { signal: AbortSignal.timeout(5000) })
      .then(res => res.json())
      .then(data => {
        setBackendHealth(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Health check failed:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 overflow-y-auto p-8">
        <h1 className="text-3xl font-bold mb-6">System Health</h1>
        
        {loading ? (
          <div className="text-gray-600">Loading...</div>
        ) : backendHealth ? (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-3 h-3 rounded-full ${backendHealth.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-xl font-semibold">
                Backend: {backendHealth.status}
              </span>
            </div>
            <pre className="bg-gray-50 p-4 rounded text-sm overflow-auto">
              {JSON.stringify(backendHealth, null, 2)}
            </pre>
          </div>
        ) : (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <p className="text-red-800">❌ Backend is not responding</p>
          </div>
        )}
        
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="font-semibold text-blue-900 mb-2">Quick Links</h2>
          <ul className="space-y-2">
            <li><a href="/api/hp/stats" target="_blank" className="text-blue-600 hover:underline">HP Worker Stats</a></li>
            <li><a href="/api/brands" target="_blank" className="text-blue-600 hover:underline">Brands API</a></li>
            <li><a href="http://localhost:8000/docs" target="_blank" className="text-blue-600 hover:underline">API Docs</a></li>
          </ul>
        </div>
      </main>
    </div>
  );
}
