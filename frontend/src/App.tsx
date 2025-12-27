import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/page';
import BrandsPage from './pages/brands/page';
import BrandDetailPage from './pages/brands/BrandDetailPage';
import ChatPage from './pages/chat/page';
import WorkersPage from './pages/workers/page';
import PerformancePage from './pages/performance/page';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/brands" element={<BrandsPage />} />
        <Route path="/brands/:brandId" element={<BrandDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/workers" element={<WorkersPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
