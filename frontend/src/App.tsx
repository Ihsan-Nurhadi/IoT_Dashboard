import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Footer from './components/Footer';
import DeviceStatusCard from './components/DeviceStatusCard';
import AudioControlCard from './components/AudioControlCard';
import RotaryControlCard from './components/RotaryControlCard';
import FloodlightControlCard from './components/FloodlightControlCard';
import LoginPage from './components/LoginPage';
import { FaCog, FaServer } from 'react-icons/fa';

// Komponen untuk Halaman Dashboard Utama
const Dashboard = () => (
  <div className="app-layout">
    <Header />
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
    <Footer />
  </div>
);

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Redirect root ke halaman login */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  );
};

export default App;