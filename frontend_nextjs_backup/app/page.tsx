import Sidebar from '@/components/Sidebar';
import ChatBox from '@/components/ChatBox';

export default function Home() {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 relative flex flex-col h-full">
        {/* Background Pattern */}
        <div className="absolute inset-0 -z-10 opacity-[0.03] pointer-events-none">
          <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(#3b82f6 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        </div>

        <div className="flex-grow overflow-hidden">
          <ChatBox />
        </div>
      </main>
    </div>
  );
}
