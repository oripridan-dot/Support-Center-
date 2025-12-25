'use client';
import { useState, useEffect, use } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatBox from '@/components/ChatBox';
import { Package, Search, ChevronRight, Sparkles } from 'lucide-react';

interface Brand {
  id: number;
  name: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  total_products?: number;
  covered_products?: number;
  coverage_percentage?: number;
  // Real data fields
  total_documents?: number;
  target_documents?: number;
  document_coverage_percentage?: number;
}

interface Product {
  id: number;
  name: string;
  description: string;
  image_url: string;
}

export default function BrandPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const brandId = parseInt(resolvedParams.id);
  const [brand, setBrand] = useState<Brand | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);

  useEffect(() => {
    // Fetch brand details
    fetch(`/api/backend/brands/${brandId}`)
      .then(res => res.json())
      .then(data => setBrand(data))
      .catch(err => console.error(err));

    // Fetch brand products
    fetch(`/api/backend/brands/${brandId}/products`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setProducts(data);
        } else {
          console.error('Expected array of products, got:', data);
          setProducts([]);
        }
      })
      .catch(err => {
        console.error(err);
        setProducts([]);
      });
  }, [brandId]);

  const filteredProducts = Array.isArray(products) ? products.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) : [];

  const getVisibleColor = (color: string, fallback: string) => {
    if (!color) return fallback;
    const c = color.toLowerCase();
    if (c === '#ffffff' || c === '#fff' || c === 'white') {
      return fallback;
    }
    return color;
  };

  const brandVibes: Record<string, string> = {
    'Mackie': 'Loud & Proud • Professional Audio',
    'Allen & Heath': 'Precision Engineering • British Excellence',
    'Montarbo': 'Italian Sound Heritage • Since 1962',
    'RCF': 'The Sound of Experience • Italian Innovation'
  };

  const brandVibe = brand?.name ? brandVibes[brand.name] || 'Professional Audio Solutions' : '';

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden relative">
      {/* Brand Background Gradient */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{ 
          background: `radial-gradient(circle at 50% 50%, ${brand?.secondary_color || '#3b82f6'} 0%, transparent 70%)` 
        }}
      />
      
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 relative flex flex-row h-full overflow-hidden">
        {/* Chat Section */}
        <div className="flex-grow overflow-hidden flex flex-col relative">
          {/* Brand Watermark Background */}
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-[0.02] overflow-hidden select-none">
            <h1 className="text-[25vw] font-black uppercase tracking-tighter rotate-[-15deg]">
              {brand?.name}
            </h1>
          </div>

          {/* Brand Header */}
          <div 
            className="h-24 border-b border-gray-200 flex items-center px-8 gap-6 shrink-0 z-10 bg-white/80 backdrop-blur-md justify-between"
          >
            <div className="flex items-center gap-4">
              {brand?.logo_url ? (
                <div className="p-2 bg-white rounded-xl shadow-sm border border-gray-100">
                  <img src={brand.logo_url} alt={brand.name} className="h-12 w-auto object-contain" />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center font-bold text-xl text-gray-400">
                  {brand?.name?.[0]}
                </div>
              )}
              <div>
                <h1 className="font-black text-3xl text-gray-900 tracking-tight">{brand?.name}</h1>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: brand?.secondary_color || '#22c55e' }} />
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{brandVibe}</span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-8">
              {/* Coverage Bar - Using REAL document data */}
              {brand && brand.document_coverage_percentage !== undefined && (
                <div className="hidden md:flex flex-col items-end gap-1.5 min-w-[240px]">
                  <div className="flex items-center justify-between w-full text-xs font-bold">
                    <span className="text-gray-400 uppercase tracking-wider text-[10px]">Documentation Coverage</span>
                    <span style={{ color: getVisibleColor(brand.secondary_color, brand.primary_color) }}>{brand.document_coverage_percentage}%</span>
                  </div>
                  <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden border border-gray-100">
                    <div 
                      className="h-full rounded-full transition-all duration-1000 ease-out relative overflow-hidden"
                      style={{ 
                        width: `${brand.document_coverage_percentage}%`,
                        backgroundColor: getVisibleColor(brand.secondary_color, brand.primary_color)
                      }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]" style={{ backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)' }} />
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-400 font-bold">
                    {brand.total_documents || 0} of {brand.target_documents || 100} documents ingested
                  </p>
                </div>
              )}

              <div className="hidden lg:flex flex-col items-end border-l border-gray-100 pl-8">
                <span className="text-2xl font-black text-gray-900">{products.length}</span>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Total Products</span>
              </div>
            </div>
          </div>

          <div className="flex-grow overflow-hidden z-10">
            <ChatBox 
              brandId={brandId} 
              brandName={brand?.name} 
              brandLogo={brand?.logo_url}
              selectedProduct={selectedProduct}
              primaryColor={brand?.primary_color}
              secondaryColor={brand?.secondary_color}
            />
          </div>
        </div>


      </main>

      {/* Product Detail Modal */}
      {isProductModalOpen && selectedProduct && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div 
            className="bg-white w-full max-w-2xl rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative h-64 bg-gray-100 flex items-center justify-center overflow-hidden">
              {selectedProduct.image_url ? (
                <img src={selectedProduct.image_url} alt={selectedProduct.name} className="w-full h-full object-contain p-8" />
              ) : (
                <Package size={64} className="text-gray-300" />
              )}
              <button 
                onClick={() => setIsProductModalOpen(false)}
                className="absolute top-4 right-4 p-2 bg-white/80 backdrop-blur-md rounded-full hover:bg-white transition-colors shadow-lg"
              >
                <ChevronRight className="rotate-180" size={20} />
              </button>
              
              {/* Brand Badge */}
              <div 
                className="absolute bottom-4 left-4 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest text-white shadow-lg"
                style={{ backgroundColor: brand?.primary_color }}
              >
                {brand?.name}
              </div>
            </div>
            
            <div className="p-8">
              <h2 className="text-2xl font-black text-gray-900 mb-2">{selectedProduct.name}</h2>
              <p className="text-gray-600 leading-relaxed mb-8">
                {selectedProduct.description || 'This product is part of the official catalog. You can ask the AI assistant for technical specifications, setup guides, and troubleshooting steps related to this specific model.'}
              </p>
              
              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                  <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Category</p>
                  <p className="text-sm font-bold text-gray-900">Professional Audio</p>
                </div>
                <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                  <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Support Status</p>
                  <p className="text-sm font-bold text-green-600 flex items-center gap-1">
                    <Sparkles size={12} />
                    AI Enhanced
                  </p>
                </div>
              </div>
              
              <div className="flex gap-3">
                <button 
                  onClick={() => setIsProductModalOpen(false)}
                  className="flex-grow py-4 rounded-2xl font-bold text-white shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all"
                  style={{ backgroundColor: brand?.secondary_color }}
                >
                  Start Support Chat
                </button>
                <button 
                  className="px-6 py-4 rounded-2xl font-bold text-gray-900 bg-gray-100 hover:bg-gray-200 transition-colors"
                  onClick={() => window.open(`https://www.google.com/search?q=${brand?.name}+${selectedProduct.name}+manual`, '_blank')}
                >
                  Manuals
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
