import React from 'react';
import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import SiteDetail from './components/SiteDetail';
import TowerSentinel from './components/TowerSentinel';
import VerticalityDetail from './components/VerticalityDetail';
import AqmsDetail from './components/AqmsDetail';
import AssetMonitoringDetail from './components/AssetMonitoringDetail';
import RfidMonitoringDetail from './components/RfidMonitoringDetail';


import LoginPage from './components/LoginPage';
import AdminDashboard from './components/AdminDashboard';
import { Navigate } from 'react-router-dom';

// Layout wrapper untuk NMS views agar menyertakan Header & Footer
const NmsLayout = () => {
  return (
    <div className="app-layout">
      <Header />
      <Outlet />
      <Footer />
    </div>
  );
};

// Helper component to protect routes requiring authentication
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    fetch('/api/auth/status/')
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error('Not authenticated');
      })
      .then((data) => {
        setIsAuthenticated(data.authenticated);
      })
      .catch(() => {
        setIsAuthenticated(false);
      });
  }, []);

  if (isAuthenticated === null) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#0a0f1d',
        color: '#94a3b8',
        fontFamily: 'Inter, sans-serif'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '4px solid rgba(255,255,255,0.1)',
          borderTopColor: '#3b82f6',
          borderRadius: '50%',
          animation: 'spinApp 1s linear infinite',
          marginBottom: '16px'
        }} />
        <span style={{ fontSize: '14px', letterSpacing: '0.05em' }}>Loading Session...</span>
        <style>{`
          @keyframes spinApp {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Landing Page Portal (Tower Sentinel) */}
        <Route path="/" element={<TowerSentinel />} />
        
        {/* Public Login Route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Admin Route */}
        <Route path="/admin" element={
          <ProtectedRoute>
            <AdminDashboard />
          </ProtectedRoute>
        } />
        
        {/* NMS Site Views */}
        <Route element={<NmsLayout />}>
          <Route path="/site-detail" element={<SiteDetail />} />
          <Route path="/verticality/:deviceId" element={<VerticalityDetail />} />
          <Route path="/aqms" element={<AqmsDetail />} />
          <Route path="/asset-monitoring" element={<AssetMonitoringDetail />} />
          <Route path="/rfid-monitoring" element={<RfidMonitoringDetail />} />
        </Route>
      </Routes>
    </Router>
  );
};


export default App;