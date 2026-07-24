import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route} from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import DeviceStatusCard from './components/DeviceStatusCard';
import AudioControlCard from './components/AudioControlCard';
import RotaryControlCard from './components/RotaryControlCard';
import CCTVStreamCard from './components/CCTVStreamCard';
import SiteDetail from './components/SiteDetail';
import { FaCog, FaServer, FaVideo, FaChevronUp, FaChevronDown, FaMapMarkerAlt, FaBuilding } from 'react-icons/fa';

import PirMotionCard from './components/PirMotionCard';

// Komponen untuk Halaman Dashboard Utama
const Dashboard = () => {
  const [isCctvCollapsed, setIsCctvCollapsed] = useState(false);

  return (
    <main className="main-content">
      {/* 0. Site Info Header Banner */}
      <div className="site-info-card dashboard-site-info">
        <div className="site-status-badge">
          <span className="status-dot-green"></span> Online
        </div>
        <h1 className="site-title">NAYAKA WS</h1>
        <div className="site-address">
          <FaMapMarkerAlt className="info-icon" />
          <span>Blok AX no, Jl. Kav. Marinir No.18, RT.14/RW.7, Pd. Klp., Kec. Duren Sawit, Kota Jakarta Timur, Daerah Khusus Ibukota Jakarta 17423</span>
        </div>
        <div className="site-tenant-info">
          <FaBuilding className="info-icon" />
          <span>Mitratel TSEL - Jabodetabek</span>
        </div>
      </div>

      {/* 1. SENSOR STATUS Section */}
      <div className="section-header-simple">
        <h2 className="section-title-caps">SENSOR STATUS</h2>
      </div>
      <div className="grid-container sensor-status-grid">
        <DeviceStatusCard deviceName="PLN" deviceType="Power Supply" />
        <DeviceStatusCard deviceName="Door Panel" deviceType="Access Control" />
      </div>

      {/* 2. PIR MOTION Radar Section */}
      <PirMotionCard />

      {/* 3. CONTROLS Section (Lampu & Sirine) */}
      <div className="side-by-side-controls">
        <RotaryControlCard />
        <AudioControlCard />
      </div>    

      {/* 4. CCTV Section */}
      <div className="cctv-accordion-card">
        <div className="cctv-accordion-header" onClick={() => setIsCctvCollapsed(!isCctvCollapsed)}>
          <div className="cctv-header-left">
            <FaVideo className="cctv-header-icon" />
            <h2 className="cctv-title">CCTV</h2>
          </div>
          <span className="collapse-icon">
            {isCctvCollapsed ? <FaChevronDown /> : <FaChevronUp />}
          </span>
        </div>
        {!isCctvCollapsed && (
          <div className="cctv-accordion-content">
            <div className="cctv-grid">
              <CCTVStreamCard 
                streamId="cctv" 
                cameraName="Kamera #1" 
              />
              <CCTVStreamCard 
                streamId="cctv2" 
                cameraName="Kamera #2" 
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <div className="app-layout">
        <Header />
        
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/site-detail" element={<SiteDetail />} />
        </Routes>

        <Footer />
      </div>
    </Router>
  );
};

export default App;