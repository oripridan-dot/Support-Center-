import Sidebar from '@/components/Sidebar';
import HighPerformanceMonitor from '@/components/HighPerformanceMonitor';

export default function WorkersPage() {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto">
          {/* Page Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-black text-gray-900 mb-2">Worker System</h1>
                <p className="text-gray-600 text-lg">
                  High-performance 22-worker specialized system
                </p>
              </div>
            </div>
          </div>

          {/* HP 22-Worker Monitor */}
          <HighPerformanceMonitor />
        </div>
      </main>
    </div>
  );
}
