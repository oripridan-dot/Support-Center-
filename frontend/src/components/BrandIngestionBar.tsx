
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface BrandProgress {
  status: 'discovering' | 'processing' | 'complete' | 'failed';
  urls_discovered: number;
  documents_ingested: number;
}

interface BrandIngestionBarProps {
  brandName?: string;
  progress?: BrandProgress;
  isCurrent?: boolean;
  totalDocuments?: number;
  targetDocuments?: number;
}

export default function BrandIngestionBar({ progress, isCurrent, totalDocuments, targetDocuments }: BrandIngestionBarProps) {
  // If we have active progress, use it. Otherwise use static stats if available.
  const hasProgress = !!progress;
  const hasStats = totalDocuments !== undefined && targetDocuments !== undefined;
  
  if (!hasProgress && !isCurrent && !hasStats) return null;

  let urlsDiscovered = 0;
  let docsIngested = 0;
  let percent = 0;
  let status = 'idle';

  if (hasProgress) {
    // Use targetDocuments if available as the goal, otherwise fallback to discovered URLs
    const target = (targetDocuments && targetDocuments > 0) ? targetDocuments : progress!.urls_discovered;
    
    urlsDiscovered = target;
    docsIngested = progress!.documents_ingested;
    
    percent = urlsDiscovered > 0 ? Math.round((docsIngested / urlsDiscovered) * 100) : 0;
    percent = Math.min(percent, 100);
    
    status = progress!.status;
    // If we are 100% done, mark as complete unless we are actively working
    if (percent >= 100 && status !== 'processing' && status !== 'discovering') {
      status = 'complete';
    }
  } else if (isCurrent) {
    status = 'processing';
  } else if (hasStats) {
    urlsDiscovered = targetDocuments!;
    docsIngested = totalDocuments!;
    percent = urlsDiscovered > 0 ? Math.round((docsIngested / urlsDiscovered) * 100) : 0;
    // Cap at 100%
    percent = Math.min(percent, 100);
    status = percent >= 100 ? 'complete' : 'idle';
  }

  return (
    <div className="mt-4 pt-4 border-t border-gray-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {status === 'processing' || status === 'discovering' ? (
            <Loader2 size={14} className="animate-spin text-blue-500" />
          ) : status === 'complete' ? (
            <CheckCircle2 size={14} className="text-green-500" />
          ) : status === 'failed' ? (
            <AlertCircle size={14} className="text-red-500" />
          ) : (
            <AlertCircle size={14} className="text-gray-400" />
          )}
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            {status === 'discovering' ? 'Discovering...' : status === 'processing' ? 'Ingesting...' : status === 'complete' ? 'Complete' : status === 'failed' ? 'Failed' : 'Coverage'}
          </span>
        </div>
        <span className="text-[10px] font-bold text-blue-600">{percent}%</span>
      </div>
      
      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ease-out ${status === 'complete' ? 'bg-green-500' : status === 'failed' ? 'bg-red-500' : 'bg-blue-500'}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      
      <div className="flex justify-between mt-1">
        <span className="text-[9px] text-gray-400">{docsIngested} / {urlsDiscovered} docs</span>
      </div>
    </div>
  );
}
