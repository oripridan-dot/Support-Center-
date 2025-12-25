import { useEffect, useState } from 'react';
import { Clock, FileText, ExternalLink } from 'lucide-react';

interface Document {
  id: number;
  title: string;
  url: string | null;
  brand_name: string;
  brand_id: number;
  updated_at: string;
}

interface RecentDocumentsResponse {
  total: number;
  documents: Document[];
  last_updated: string;
}

export default function RecentDocumentsFeed() {
  const [data, setData] = useState<RecentDocumentsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDocs = () => {
      fetch('/api/backend/documents/recent?limit=30')
        .then(res => res.json())
        .then(data => {
          setData(data);
          setLoading(false);
        })
        .catch(err => {
          console.error('Failed to fetch recent documents:', err);
          setLoading(false);
        });
    };

    fetchDocs();
    const interval = setInterval(fetchDocs, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="text-blue-600" size={24} />
          <h2 className="text-xl font-bold text-gray-900">Recent Documents</h2>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 flex flex-col max-h-[600px]">
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <FileText className="text-blue-600" size={24} />
          <h2 className="text-xl font-bold text-gray-900">Live Document Feed</h2>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Clock size={16} />
          <span>{data?.total || 0} total documents</span>
        </div>
      </div>
      
      <div className="overflow-y-auto flex-1">
        {data?.documents.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <FileText className="mx-auto mb-2 text-gray-400" size={48} />
            <p>No documents yet. Start scraping to see them appear here!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {data?.documents.map((doc, idx) => (
              <div 
                key={`${doc.id}-${idx}`}
                className="p-4 hover:bg-gray-50 transition-colors duration-150 animate-fadeIn"
                style={{ animationDelay: `${idx * 20}ms` }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {doc.brand_name}
                      </span>
                      <span className="text-xs text-gray-400">#{doc.id}</span>
                    </div>
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {doc.title}
                    </h3>
                    {doc.url && (
                      <a 
                        href={doc.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 mt-1 group"
                      >
                        <span className="truncate max-w-[300px]">{doc.url}</span>
                        <ExternalLink size={12} className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </a>
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Auto-refreshing every 2 seconds</span>
          <span className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
            Live
          </span>
        </div>
      </div>
    </div>
  );
}
