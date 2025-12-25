import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/page';
import BrandsPage from './pages/brands/page';
import BrandDetailPage from './pages/brands/BrandDetailPage';
import ChatPage from './pages/chat/page';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/brands" element={<BrandsPage />} />
        <Route path="/brands/:brandId" element={<BrandDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
