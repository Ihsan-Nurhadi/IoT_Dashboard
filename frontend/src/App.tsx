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

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Landing Page Portal (Tower Sentinel) */}
        <Route path="/" element={<TowerSentinel />} />
        
        {/* NMS Site Views */}
        <Route element={<NmsLayout />}>
          <Route path="/site-detail" element={<SiteDetail />} />
          <Route path="/verticality/:deviceId" element={<VerticalityDetail />} />
          <Route path="/aqms" element={<AqmsDetail />} />
          <Route path="/asset-monitoring" element={<AssetMonitoringDetail />} />
        </Route>
      </Routes>
    </Router>
  );
};


export default App;