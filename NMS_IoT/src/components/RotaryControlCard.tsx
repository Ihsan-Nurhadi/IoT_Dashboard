import React, { useState } from 'react';
import Card from './Card';
import './RotaryControlCard.css';
import { FaSync, FaPlay, FaStop } from 'react-icons/fa';

const API_URL = "http://localhost:8000/send-rotary/"; // sesuaikan

const RotaryControlCard: React.FC = () => {
  const [isMotorOn, setIsMotorOn] = useState(false);
  const [loading, setLoading] = useState(false);

  const sendStatus = async (status: number) => {
    try {
      setLoading(true);
      await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status })
      });
      setIsMotorOn(status === 1);
    } catch (error) {
      console.error("Failed send MQTT", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="rotary-control-card">
      <div className="card-header">
        <div className="icon-container rotary">
          <FaSync />
        </div>
        <div className="header-text">
          <h3 className="card-title">Rotary Control</h3>
          <p className="card-subtitle">Motor operation control</p>
        </div>
      </div>

      <div className="rotary-status-container">
        <div className={`rotary-indicator ${isMotorOn ? 'motor-on' : ''}`} />
      </div>

      <div className="motor-status">
        <FaPlay className="motor-status-icon" />
        <span>Motor Status</span>
        <span className={`motor-status-badge ${isMotorOn ? 'on' : ''}`}>
          {isMotorOn ? 'Running' : 'Stopped'}
        </span>
      </div>

      <div className="control-buttons">
        <button
          className={`control-button on ${isMotorOn ? 'active' : ''}`}
          onClick={() => sendStatus(1)}
          disabled={loading}
        >
          <FaPlay /> Turn ON
        </button>

        <button
          className={`control-button off ${!isMotorOn ? 'active' : ''}`}
          onClick={() => sendStatus(0)}
          disabled={loading}
        >
          <FaStop /> Turn OFF
        </button>
      </div>
    </Card>
  );
};

export default RotaryControlCard;
