'use client';
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, Sparkles, Image as ImageIcon, FileText, ExternalLink } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  images?: { url: string; alt: string }[];
  pdfs?: { url: string; title: string }[];
  brand_logos?: { name: string; url: string }[];
  sources?: { title?: string; url?: string; source?: string }[];
}

export default function ChatBox({ 
  brandId, 
  brandName,
  brandLogo,
  selectedProduct,
  primaryColor = '#3b82f6',
  secondaryColor = '#ffffff'
}: { 
  brandId?: number, 
  brandName?: string,
  brandLogo?: string,
  selectedProduct?: { id: number, name: string, image_url: string },
  primaryColor?: string,
  secondaryColor?: string
}) {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const response = await fetch('/api/backend/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: query, 
          brand_id: brandId,
          product_id: selectedProduct?.id,
          is_first_message: messages.length === 0,
          history: messages.slice(-10).map(m => ({ role: m.role, content: m.content }))
        }),
      });
      
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Server error');
      }
      
      const data = await response.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.answer,
        images: data.images,
        pdfs: data.pdfs,
        brand_logos: data.brand_logos,
        sources: data.sources
      }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'I encountered an error. The support system is currently being updated. Please try again in a few moments.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-transparent overflow-hidden">
      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-grow overflow-y-auto px-4 md:px-8 py-8 space-y-8 scroll-smooth relative"
      >
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-8 max-w-2xl mx-auto">
            <div className="relative">
              <div 
                className="w-32 h-32 rounded-[2.5rem] flex items-center justify-center animate-pulse shadow-2xl bg-white border-4 overflow-hidden" 
                style={{ borderColor: `${secondaryColor}40` }}
              >
                {selectedProduct?.image_url ? (
                  <img src={selectedProduct.image_url} alt="Product" className="w-full h-full object-contain p-4" />
                ) : brandLogo ? (
                  <img src={brandLogo} alt={brandName} className="w-full h-full object-contain p-4" />
                ) : (
                  <Bot size={48} style={{ color: secondaryColor }} />
                )}
              </div>
              <div 
                className="absolute -top-2 -right-2 w-10 h-10 rounded-full flex items-center justify-center shadow-lg border-4 border-white"
                style={{ backgroundColor: secondaryColor }}
              >
                <Sparkles size={18} className="text-white" />
              </div>
            </div>
            
            <div className="space-y-3">
              <h3 className="text-3xl font-black text-gray-900 tracking-tight">
                {brandName} <span style={{ color: secondaryColor }}>Expert Support</span>
              </h3>
              <p className="text-gray-500 text-lg max-w-md mx-auto leading-relaxed">
                Ask me anything about {brandName} products, from technical specifications to complex troubleshooting.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full px-4">
              {[
                { label: 'Technical Specifications', icon: FileText },
                { label: 'Troubleshooting Guide', icon: Bot },
                { label: 'Product Comparison', icon: Sparkles },
                { label: 'Setup & Installation', icon: ExternalLink }
              ].map((item) => (
                <button 
                  key={item.label}
                  onClick={() => setQuery(`${item.label} for...`)}
                  className="flex items-center gap-4 px-6 py-4 text-sm font-bold text-gray-700 bg-white hover:bg-gray-50 rounded-2xl transition-all text-left border border-gray-100 shadow-sm hover:shadow-md group"
                >
                  <div 
                    className="p-2 rounded-lg group-hover:scale-110 transition-transform"
                    style={{ backgroundColor: `${secondaryColor}10` }}
                  >
                    <item.icon size={18} style={{ color: secondaryColor }} />
                  </div>
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div 
            key={idx} 
            className={cn(
              "flex w-full gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500",
              msg.role === 'user' ? "flex-row-reverse" : "flex-row"
            )}
          >
            <div className={cn(
              "flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg relative",
              msg.role === 'user' ? "bg-gray-900 text-white" : "bg-white border border-gray-100"
            )}
            style={msg.role === 'user' ? { backgroundColor: primaryColor } : {}}
            >
              {msg.role === 'user' ? (
                <User size={20} />
              ) : (
                <>
                  <div className="relative w-full h-full flex items-center justify-center z-10 overflow-hidden rounded-2xl">
                    {brandLogo ? (
                      <img src={brandLogo} alt={brandName} className="w-full h-full object-contain p-1.5" />
                    ) : (
                      <Bot size={20} style={{ color: secondaryColor }} className="z-10" />
                    )}
                    <div 
                      className="absolute inset-0 opacity-10"
                      style={{ backgroundColor: secondaryColor }}
                    />
                  </div>
                  <div 
                    className="absolute inset-0 rounded-2xl blur-md opacity-40 animate-pulse"
                    style={{ backgroundColor: secondaryColor }}
                  />
                </>
              )}
            </div>

            <div className={cn(
              "max-w-[85%] md:max-w-[70%] space-y-4",
              msg.role === 'user' ? "items-end" : "items-start"
            )}>
              <div className={cn(
                "rounded-3xl px-6 py-4 shadow-sm border",
                msg.role === 'user' 
                  ? "text-white border-blue-500 rounded-tr-none" 
                  : "bg-white text-gray-800 border-gray-100 rounded-tl-none"
              )}
              style={msg.role === 'user' ? { backgroundColor: primaryColor, borderColor: primaryColor } : {}}
              >
                <div className={cn(
                  "prose prose-sm max-w-none",
                  msg.role === 'user' ? "prose-invert" : "prose-slate"
                )}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({node, ...props}) => <h1 className="text-xl font-black text-gray-900 mt-6 mb-3 flex items-center gap-2 border-b border-gray-100 pb-2" {...props} />,
                      h2: ({node, ...props}) => <h2 className="text-lg font-bold text-gray-800 mt-5 mb-2 flex items-center gap-2" {...props} />,
                      h3: ({node, ...props}) => <h3 className="text-base font-bold text-gray-800 mt-4 mb-1" {...props} />,
                      h4: ({node, ...props}) => {
                        const content = String(props.children);
                        if (content.includes('QUICK OVERVIEW')) return <div className="px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-widest mb-3 inline-block" style={{ backgroundColor: `${secondaryColor}15`, color: secondaryColor }}>🌟 Quick Overview</div>;
                        if (content.includes('KEY SPECIFICATIONS')) return <div className="px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-widest mb-3 inline-block" style={{ backgroundColor: `${secondaryColor}15`, color: secondaryColor }}>📊 Key Specifications</div>;
                        if (content.includes('COMPARISON')) return <div className="px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-widest mb-3 inline-block" style={{ backgroundColor: `${secondaryColor}15`, color: secondaryColor }}>⚔️ Comparison</div>;
                        if (content.includes('TROUBLESHOOTING')) return <div className="px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-widest mb-3 inline-block" style={{ backgroundColor: `${secondaryColor}15`, color: secondaryColor }}>🛠️ Troubleshooting</div>;
                        if (content.includes('PRO TIP')) return <div className="px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-widest mb-3 inline-block" style={{ backgroundColor: `${secondaryColor}15`, color: secondaryColor }}>💡 Pro Tip</div>;
                        return <h4 className="text-sm font-bold text-gray-700 mt-3 mb-1 uppercase tracking-wider" {...props} />;
                      },
                      table: ({node, ...props}) => (
                        <div className="my-6 overflow-hidden rounded-2xl border border-gray-200 shadow-md bg-white">
                          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Technical Specifications</span>
                          </div>
                          <table className="w-full text-sm text-left border-collapse" {...props} />
                        </div>
                      ),
                      thead: ({node, ...props}) => <thead className="bg-gray-50 border-b border-gray-100" {...props} />,
                      th: ({node, ...props}) => <th className="px-4 py-3 font-bold text-gray-900 border-r border-gray-100 last:border-r-0" {...props} />,
                      td: ({node, ...props}) => <td className="px-4 py-3 border-b border-gray-50 text-gray-600 border-r border-gray-50 last:border-r-0" {...props} />,
                      ul: ({node, ...props}) => <ul className="space-y-2 my-3 list-none pl-0" {...props} />,
                      li: ({node, ...props}) => (
                        <li className="flex gap-3 items-start">
                          <span className="mt-2 w-1.5 h-1.5 rounded-full shrink-0 bg-gray-300" />
                          <span className="text-gray-700" {...props} />
                        </li>
                      ),
                      strong: ({node, ...props}) => <strong className="font-black text-gray-900 text-lg" {...props} />,
                      p: ({node, ...props}) => <p className="mb-4 leading-relaxed" {...props} />,
                      code: ({node, ...props}) => <code className="bg-gray-100 px-1 rounded font-mono" style={{ color: secondaryColor }} {...props} />,
                      hr: ({node, ...props}) => <hr className="my-6 border-gray-100" {...props} />,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Visuals/Images from documents */}
              {msg.images && msg.images.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
                  {msg.images.map((img, i) => (
                    <div key={i} className="relative group aspect-video overflow-hidden rounded-2xl border border-gray-100 bg-gray-50 shadow-sm hover:shadow-md transition-all">
                      <img 
                        src={img.url} 
                        alt={img.alt || "Product visual"} 
                        className="w-full h-full object-contain p-2 cursor-zoom-in group-hover:scale-105 transition-transform"
                      />
                      {img.alt && (
                        <div className="absolute bottom-0 inset-x-0 bg-black/60 backdrop-blur-sm p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <p className="text-[10px] text-white truncate">{img.alt}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* PDF Documents */}
              {msg.pdfs && msg.pdfs.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-4">
                  {msg.pdfs.map((pdf, i) => (
                    <a 
                      key={i}
                      href={pdf.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 px-4 py-3 bg-white border border-gray-100 rounded-2xl hover:border-blue-500 hover:shadow-md transition-all group"
                    >
                      <div className="p-2 bg-red-50 text-red-600 rounded-xl group-hover:bg-red-600 group-hover:text-white transition-colors">
                        <FileText size={18} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-gray-900 truncate max-w-[150px]">{pdf.title}</span>
                        <span className="text-[10px] text-gray-400 uppercase font-bold flex items-center gap-1">
                          Open PDF <ExternalLink size={10} />
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="flex flex-col gap-2 mt-4 pt-4 border-t border-gray-100">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.slice(0, 5).map((source, i) => (
                      source.url ? (
                        <a 
                          key={i} 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded border border-blue-100 truncate max-w-xs hover:underline hover:bg-blue-100 transition-colors flex items-center gap-1" 
                          title={source.source || source.url}
                        >
                          {source.title || source.source || "Document"} <ExternalLink size={8} />
                        </a>
                      ) : (
                        <div key={i} className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded border border-gray-100 truncate max-w-xs" title={source.source || source.url}>
                          {source.title || source.source || "Document"}
                        </div>
                      )
                    ))}
                  </div>
                </div>
              )}

              {/* Brand Logos */}
              {msg.brand_logos && msg.brand_logos.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-gray-100">
                  <p className="w-full text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Related Brands</p>
                  {msg.brand_logos.map((brand, i) => (
                    <div key={i} className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-100 rounded-xl shadow-sm" title={brand.name}>
                      <img src={brand.url} alt={brand.name} className="w-6 h-6 object-contain" />
                      <span className="text-xs font-bold text-gray-700">{brand.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-4 animate-pulse">
            <div className="w-10 h-10 bg-gray-100 rounded-2xl" />
            <div className="space-y-3 flex-grow max-w-[40%]">
              <div className="h-4 bg-gray-100 rounded-full w-3/4" />
              <div className="h-4 bg-gray-100 rounded-full" />
              <div className="h-4 bg-gray-100 rounded-full w-5/6" />
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 md:p-8 bg-white border-t border-gray-100">
        {selectedProduct && (
          <div className="max-w-4xl mx-auto mb-4 p-4 rounded-2xl bg-gray-50 border border-gray-100 flex items-center gap-4 animate-in slide-in-from-bottom-4 duration-300">
            {selectedProduct.image_url && (
              <img src={selectedProduct.image_url} alt={selectedProduct.name} className="w-12 h-12 rounded-lg object-cover border border-gray-200 shadow-sm" />
            )}
            <div className="flex-grow">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-0.5">Selected Product</p>
              <p className="text-sm font-bold text-gray-900">{selectedProduct.name}</p>
            </div>
            <button 
              type="button"
              onClick={() => setQuery(`Tell me about the ${selectedProduct.name}`)}
              className="px-4 py-2 rounded-xl bg-white text-xs font-bold text-gray-900 shadow-sm hover:shadow-md transition-all border border-gray-100"
            >
              Ask AI
            </button>
          </div>
        )}
        <form 
          onSubmit={handleSearch} 
          className="max-w-4xl mx-auto relative group"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={brandName ? `Ask about ${brandName}...` : "Ask a technical question..."}
            className="w-full pl-6 pr-16 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 transition-all text-gray-900 placeholder:text-gray-400 shadow-sm group-hover:shadow-md"
            style={{ 
              '--tw-ring-color': `${secondaryColor}40`,
              borderColor: query ? secondaryColor : '#e5e7eb'
            } as any}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-3 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:scale-105 active:scale-95"
            style={{ backgroundColor: secondaryColor }}
          >
            <Send size={20} />
          </button>
        </form>
        <p className="text-center mt-4 text-[10px] text-gray-400 uppercase tracking-widest font-bold">
          Halilit Technical Support Hub • 2025
        </p>
      </div>
    </div>
  );
}
