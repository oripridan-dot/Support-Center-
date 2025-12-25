import Sidebar from '@/components/Sidebar';
import ChatBox from '@/components/ChatBox';

export default function ChatPage() {
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      
      <main className="flex-grow lg:ml-64 relative flex flex-col h-full">
        <div className="flex-grow overflow-hidden">
          <ChatBox />
        </div>
      </main>
    </div>
  );
}
