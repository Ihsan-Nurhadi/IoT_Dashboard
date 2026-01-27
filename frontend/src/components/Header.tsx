import React from 'react';
import { Link } from 'react-router-dom';
import './Header.css';
import {FaHome } from 'react-icons/fa';

const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="logo-container">
        <img src="/logo.svg" alt="logo" className="logo-icon" />
        <div>
          <h1 className="app-title">NMS Control Panel</h1>
          <p className="app-subtitle">Real-time device management</p>
        </div>
      </div>

      <nav className="header-nav">
        <Link to="/" className="nav-link"><FaHome /> Dashboard</Link>
      </nav>

      <div className="system-status">
        <span className="status-indicator-dot"></span>
        System Online
      </div>
    </header>
  );
};

export default Header;

