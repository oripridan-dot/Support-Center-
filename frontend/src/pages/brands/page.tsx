import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Sidebar from '@/components/Sidebar';
import BrandIngestionBar from '@/components/BrandIngestionBar';
import { Search, ArrowRight } from 'lucide-react';

interface Brand {
  id: number;
  name: string;
  logo_url: string;
  description: string;
  total_documents: number;
  target_documents: number;
  document_coverage_percentage: number;
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
    fetch('/api/brands')
      .then(res => res.json())
      .then(data => {
        // Transform basic brand data to match expected format
        const brandsWithStats = data.map((brand: any) => ({
          ...brand,
          total_documents: brand.total_documents || 0,
          target_documents: brand.target_documents || 0,
          document_coverage_percentage: brand.total_documents && brand.target_documents 
            ? (brand.total_documents / brand.target_documents) * 100 
            : 0
        }));
        setBrands(brandsWithStats);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });

    // Poll for HP pipeline status
    const pollStatus = () => {
      fetch('/api/hp/pipeline/status')
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
  ).sort((a, b) => {
    // Sort active brand to top
    const isAActive = ingestionStatus?.current_brand === a.name;
    const isBActive = ingestionStatus?.current_brand === b.name;
    if (isAActive && !isBActive) return -1;
    if (!isAActive && isBActive) return 1;
    return 0;
  });

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 relative flex flex-col h-full overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto w-full space-y-8">
          {/* Header Section */}
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

          {/* Two-column layout: Brands + Live Feed */}
          <div className="grid grid-cols-1 gap-8">
            {/* Brands Grid - Takes full width */}
            <div className="w-full">
              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {[1,2,3,4,5,6,7,8].map(i => (
                    <div key={i} className="h-64 bg-white rounded-3xl animate-pulse border border-gray-100" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {filteredBrands.map((brand) => (
                    <Link to={`/brands/${brand.id}`} key={brand.id} className="group">
                      <div className="bg-white rounded-2xl border border-gray-100 p-4 h-full hover:shadow-xl hover:border-blue-500/30 transition-all duration-300 flex flex-col">
                        <div className="h-24 flex items-center justify-center mb-4 bg-gray-50 rounded-xl p-3 group-hover:bg-white transition-colors">
                          {brand.logo_url ? (
                            <img src={brand.logo_url} alt={brand.name} className="max-h-full max-w-full object-contain opacity-70 grayscale-[30%] group-hover:grayscale-0 group-hover:opacity-100 group-hover:scale-105 transition-all duration-300" />
                          ) : (
                            <span className="text-xl font-bold text-gray-300">{brand.name}</span>
                          )}
                        </div>
                        <h2 className="text-lg font-bold text-gray-900 mb-1 truncate">{brand.name}</h2>
                        <p className="text-xs text-gray-500 line-clamp-2 mb-4">
                          {brand.description || 'Official technical support and documentation.'}
                        </p>
                        
                        <BrandIngestionBar 
                          brandName={brand.name}
                          progress={ingestionStatus?.brand_progress[brand.name]}
                          isCurrent={ingestionStatus?.current_brand === brand.name}
                          totalDocuments={brand.total_documents}
                          targetDocuments={brand.target_documents}
                        />

                        <div className="mt-auto flex items-center text-blue-600 font-bold text-xs opacity-0 group-hover:opacity-100 transition-opacity pt-2">
                          Open Support <ArrowRight size={14} className="ml-1" />
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
