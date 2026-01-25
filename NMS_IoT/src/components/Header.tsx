import React from 'react';
import { Link } from 'react-router-dom';
import './Header.css';
import { FaSatelliteDish, FaHome } from 'react-icons/fa';

const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="logo-container">
        <FaSatelliteDish className="logo-icon" />
        <div>
          <h1 className="app-title">IoT Control Panel</h1>
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
