import React from 'react';
import { BrowserRouter as Router, Routes, Route} from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import DeviceStatusCard from './components/DeviceStatusCard';
import AudioControlCard from './components/AudioControlCard';
import RotaryControlCard from './components/RotaryControlCard';
import FloodlightControlCard from './components/FloodlightControlCard';
import { FaCog, FaServer } from 'react-icons/fa';

// Komponen untuk Halaman Dashboard Utama
const Dashboard = () => (
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
  </main>
);

const App: React.FC = () => {
  return (
    <Router>
      <div className="app-layout">
        <Header />
        
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>

        <Footer />
      </div>
    </Router>
  );
};

export default App;