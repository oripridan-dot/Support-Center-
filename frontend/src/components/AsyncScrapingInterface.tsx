/**
 * Async Scraping Interface
 * UI for triggering async scraping tasks
 */

import React, { useState } from 'react';
import { apiV2Endpoints } from '../lib/api';

export const AsyncScrapingInterface: React.FC = () => {
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScrape = async () => {
    if (!url || !brand) {
      setError('Please enter both URL and brand name');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiV2Endpoints.scrapeAsync(url, brand);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scraping failed');
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async () => {
    if (!result?.task_id) return;

    try {
      const status = await apiV2Endpoints.taskStatus(result.task_id);
      setResult({ ...result, ...(status as any) });
    } catch (err) {
      setError('Failed to check task status');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <span>🚀</span> Async Scraping
      </h3>

      <div className="space-y-4">
        {/* Input Fields */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            URL to Scrape
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/product"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Brand Name
          </label>
          <input
            type="text"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            placeholder="e.g., Roland"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleScrape}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Queuing...' : 'Start Scraping'}
          </button>

          {result?.task_id && (
            <button
              onClick={checkStatus}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
            >
              Check Status
            </button>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className="p-4 bg-gray-50 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Task ID:</span>
              <code className="text-xs bg-gray-200 px-2 py-1 rounded">
                {result.task_id}
              </code>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Status:</span>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  result.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : result.status === 'failed'
                    ? 'bg-red-100 text-red-800'
                    : result.status === 'processing'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-blue-100 text-blue-800'
                }`}
              >
                {result.status}
              </span>
            </div>

            {result.result && (
              <div className="mt-2 pt-2 border-t border-gray-200">
                <span className="text-sm font-medium text-gray-700">Result:</span>
                <pre className="mt-1 text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto">
                  {JSON.stringify(result.result, null, 2)}
                </pre>
              </div>
            )}

            {result.error && (
              <div className="mt-2 pt-2 border-t border-red-200">
                <span className="text-sm font-medium text-red-700">Error:</span>
                <p className="mt-1 text-xs text-red-600">{result.error}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AsyncScrapingInterface;
