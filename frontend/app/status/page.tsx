'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { Activity, Database, FileText, Clock, AlertCircle, CheckCircle2 } from 'lucide-react';

interface BrandStats {
  id: number;
  name: string;
  logo_url: string;
  total_products: number;
  covered_products: number;
  coverage_percentage: number;
  last_ingestion: string | null;
}

export default function StatusPage() {
  const [stats, setStats] = useState<BrandStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/backend/brands/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
        setLastUpdated(new Date());
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 relative flex flex-col h-full overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto w-full space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">System Status</h1>
              <p className="text-gray-500 mt-2">Real-time monitoring of knowledge base ingestion and brand coverage.</p>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Activity size={16} className="animate-pulse text-green-500" />
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6">
            {loading ? (
              <div className="text-center py-12 text-gray-400">Loading status...</div>
            ) : (
              stats.map((brand) => (
                <div key={brand.id} className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex flex-col md:flex-row md:items-center gap-6">
                    {/* Brand Info */}
                    <div className="flex items-center gap-4 w-full md:w-1/4">
                      <div className="h-16 w-16 bg-gray-50 rounded-xl flex items-center justify-center p-2 border border-gray-100">
                        {brand.logo_url ? (
                          <img src={brand.logo_url} alt={brand.name} className="max-h-full max-w-full object-contain" />
                        ) : (
                          <span className="font-bold text-gray-300">{brand.name[0]}</span>
                        )}
                      </div>
                      <div>
                        <h3 className="font-bold text-lg text-gray-900">{brand.name}</h3>
                        <div className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded-full w-fit mt-1">
                          <CheckCircle2 size={12} /> Active
                        </div>
                      </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="flex-grow grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="space-y-1">
                        <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                          <Database size={12} /> Total Products
                        </div>
                        <div className="text-2xl font-bold text-gray-900">{brand.total_products}</div>
                      </div>

                      <div className="space-y-1">
                        <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                          <FileText size={12} /> Ingested
                        </div>
                        <div className="text-2xl font-bold text-blue-600">{brand.covered_products}</div>
                      </div>

                      <div className="space-y-1 col-span-2 md:col-span-1">
                        <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                          <Activity size={12} /> Coverage
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-2xl font-bold text-gray-900">{brand.coverage_percentage}%</div>
                        </div>
                        <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-blue-500 rounded-full transition-all duration-500"
                            style={{ width: `${brand.coverage_percentage}%` }}
                          />
                        </div>
                      </div>

                      <div className="space-y-1 col-span-2 md:col-span-1">
                        <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                          <Clock size={12} /> Last Activity
                        </div>
                        <div className="text-sm font-medium text-gray-700">
                          {brand.last_ingestion ? new Date(brand.last_ingestion).toLocaleString() : 'Never'}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Additional Info / "News" Placeholder */}
                  <div className="mt-6 pt-6 border-t border-gray-50 flex gap-4 overflow-x-auto pb-2">
                    <div className="min-w-[200px] p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                      <div className="text-xs font-bold text-blue-600 mb-1">LATEST INGESTION</div>
                      <p className="text-xs text-blue-800">
                        {brand.last_ingestion 
                          ? `System processed new data on ${new Date(brand.last_ingestion).toLocaleDateString()}`
                          : 'No data processed yet.'}
                      </p>
                    </div>
                    <div className="min-w-[200px] p-3 bg-gray-50 rounded-lg border border-gray-100 opacity-60">
                      <div className="text-xs font-bold text-gray-500 mb-1">UPCOMING PRODUCTS</div>
                      <p className="text-xs text-gray-600">No upcoming products detected.</p>
                    </div>
                    <div className="min-w-[200px] p-3 bg-gray-50 rounded-lg border border-gray-100 opacity-60">
                      <div className="text-xs font-bold text-gray-500 mb-1">BRAND TIPS</div>
                      <p className="text-xs text-gray-600">No tips available.</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
