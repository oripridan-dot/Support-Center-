/**
 * Performance Monitoring Page
 * Main page for viewing system performance metrics
 */

import React from 'react';
import Sidebar from '../../components/Sidebar';
import HighPerformanceMonitor from '../../components/HighPerformanceMonitor';

const PerformancePage: React.FC = () => {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto">
          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-black text-gray-900 mb-2">Performance Monitoring</h1>
            <p className="text-gray-600 text-lg">
              Real-time monitoring of the high-performance worker system
            </p>
          </div>

          {/* High-Performance Monitor */}
          <HighPerformanceMonitor />
        </div>
      </main>
    </div>
  );
};

export default PerformancePage;
