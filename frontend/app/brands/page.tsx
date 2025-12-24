'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import BrandIngestionBar from '@/components/BrandIngestionBar';
import { Search, ArrowRight } from 'lucide-react';

interface Brand {
  id: number;
  name: string;
  logo_url: string;
  description: string;
}

interface IngestionStatus {
  is_running: boolean;
  current_brand: string | null;
  brand_progress: Record<string, any>;
}

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [ingestionStatus, setIngestionStatus] = useState<IngestionStatus | null>(null);

  useEffect(() => {
    fetch('/api/backend/brands')
      .then(res => res.json())
      .then(data => {
        setBrands(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });

    // Poll for ingestion status
    const pollStatus = () => {
      fetch('/api/backend/ingestion/status')
        .then(res => res.json())
        .then(data => setIngestionStatus(data))
        .catch(err => console.error('Status poll error:', err));
    };

    pollStatus();
    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const filteredBrands = brands.filter(b => 
    b.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 relative flex flex-col h-full overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto w-full space-y-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Partner Brands</h1>
              <p className="text-gray-500 mt-2">Select a brand to start a specialized support session.</p>
            </div>
            
            <div className="relative max-w-md w-full">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
              <input 
                type="text"
                placeholder="Search brands..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm"
              />
            </div>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1,2,3,4,5,6].map(i => (
                <div key={i} className="h-64 bg-white rounded-3xl animate-pulse border border-gray-100" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredBrands.map((brand) => (
                <Link href={`/brands/${brand.id}`} key={brand.id} className="group">
                  <div className="bg-white rounded-3xl border border-gray-100 p-6 h-full hover:shadow-xl hover:border-blue-500/30 transition-all duration-300 flex flex-col">
                    <div className="h-32 flex items-center justify-center mb-6 bg-gray-50 rounded-2xl p-4 group-hover:bg-white transition-colors">
                      {brand.logo_url ? (
                        <img src={brand.logo_url} alt={brand.name} className="max-h-full max-w-full object-contain grayscale group-hover:grayscale-0 transition-all" />
                      ) : (
                        <span className="text-2xl font-bold text-gray-300">{brand.name}</span>
                      )}
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">{brand.name}</h2>
                    <p className="text-sm text-gray-500 line-clamp-2 mb-6">
                      {brand.description || 'Official technical support and documentation.'}
                    </p>

                    <BrandIngestionBar 
                      brandName={brand.name}
                      progress={ingestionStatus?.brand_progress[brand.name]}
                      isCurrent={ingestionStatus?.current_brand === brand.name}
                    />

                    <div className="mt-auto flex items-center text-blue-600 font-bold text-sm opacity-0 group-hover:opacity-100 transition-opacity">
                      Open Support <ArrowRight size={16} className="ml-2" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
