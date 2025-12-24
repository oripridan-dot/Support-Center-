'use client';

import React from 'react';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface BrandProgress {
  status: 'discovering' | 'processing' | 'complete' | 'failed';
  urls_discovered: number;
  documents_ingested: number;
}

interface BrandIngestionBarProps {
  brandName: string;
  progress?: BrandProgress;
  isCurrent?: boolean;
}

export default function BrandIngestionBar({ brandName, progress, isCurrent }: BrandIngestionBarProps) {
  if (!progress && !isCurrent) return null;

  const urlsDiscovered = progress?.urls_discovered || 0;
  const docsIngested = progress?.documents_ingested || 0;
  const percent = urlsDiscovered > 0 ? Math.round((docsIngested / urlsDiscovered) * 100) : 0;
  const status = progress?.status || (isCurrent ? 'processing' : 'idle');

  return (
    <div className="mt-4 pt-4 border-t border-gray-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {status === 'processing' || status === 'discovering' ? (
            <Loader2 size={14} className="animate-spin text-blue-500" />
          ) : status === 'complete' ? (
            <CheckCircle2 size={14} className="text-green-500" />
          ) : (
            <AlertCircle size={14} className="text-gray-400" />
          )}
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            {status === 'discovering' ? 'Discovering...' : status === 'processing' ? 'Ingesting...' : 'Status'}
          </span>
        </div>
        <span className="text-[10px] font-bold text-blue-600">{percent}%</span>
      </div>
      
      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <div 
          className="h-full bg-blue-500 transition-all duration-500 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
      
      <div className="flex justify-between mt-1">
        <span className="text-[9px] text-gray-400">{docsIngested} / {urlsDiscovered} pages</span>
      </div>
    </div>
  );
}
