import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route} from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import DeviceStatusCard from './components/DeviceStatusCard';
import AudioControlCard from './components/AudioControlCard';
import RotaryControlCard from './components/RotaryControlCard';
import FloodlightControlCard from './components/FloodlightControlCard';
import CCTVStreamCard from './components/CCTVStreamCard';
import SiteDetail from './components/SiteDetail';
import { FaCog, FaServer, FaVideo, FaChevronUp, FaChevronDown } from 'react-icons/fa';

// Komponen untuk Halaman Dashboard Utama
const Dashboard = () => {
  const [isCctvCollapsed, setIsCctvCollapsed] = useState(false);

  return (
    <main className="main-content">
      <div className="section-header">
        <FaServer className="section-icon" />
        <div>
          <h2 className="section-title">Device Status</h2>
          <p className="section-subtitle">Monitor your connected devices</p>
        </div>
      </div>
      <div className="grid-container">
        <DeviceStatusCard deviceName="PLN" deviceType="Power Supply" />
        <DeviceStatusCard deviceName="Door Panel" deviceType="Access Control" />
        <DeviceStatusCard deviceName="Motion Sensor 1" deviceType="Motion Detection" />
        <DeviceStatusCard deviceName="Motion Sensor 2" deviceType="Motion Detection" />
      </div>

      <div className="section-header">
        <FaCog className="section-icon" />
        <div>
          <h2 className="section-title">Device Control</h2>
          <p className="section-subtitle">Manage your device operations</p>
        </div>
      </div>
      <div className="device-control-grid">
        <FloodlightControlCard />
      </div>
      <div className="side-by-side-grid">
        <AudioControlCard />
        <RotaryControlCard />
      </div>    

      <div className="cctv-accordion-card">
        <div className="cctv-accordion-header" onClick={() => setIsCctvCollapsed(!isCctvCollapsed)}>
          <FaVideo className="section-icon" />
          <h2 className="section-title">CCTV</h2>
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