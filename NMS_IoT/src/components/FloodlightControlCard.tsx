import React, { useState } from 'react';
import Card from './Card';
import './FloodlightControlCard.css';
import { FaLightbulb, FaPowerOff } from 'react-icons/fa';

const API_URL = "/api/send-floodlight/"; // sesuaikan

const FloodlightControlCard: React.FC = () => {
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
    <Card className="floodlight-control-card">
      <div className="card-header">
        <div className="icon-container">
          <FaLightbulb />
        </div>
        <div className="header-text">
          <h3 className="card-title">Floodlight Control</h3>
          <p className="card-subtitle">Outdoor lighting control</p>
        </div>
      </div>

      <div className="status-indicator-container">
        <div className={`status-indicator ${isMotorOn ? 'on' : ''}`}>
          <FaPowerOff />
        </div>
      </div>

      <div className="light-status">
        <FaLightbulb className="light-status-icon" />
        <span>Light Status</span>
        <span className={`light-status-badge ${isMotorOn ? 'on' : ''}`}>
          {isMotorOn ? 'ON' : 'OFF'}
        </span>
      </div>

      <div className="control-buttons">
        <button
          className={`control-button on ${!isMotorOn ? 'active' : ''}`}
          onClick={() => sendStatus(1)}
          disabled={loading}
        >
          <FaLightbulb /> Turn ON
        </button>

        <button
          className={`control-button off ${isMotorOn ? 'active' : ''}`}
          onClick={() => sendStatus(0)}
          disabled={loading}
        >
          <FaPowerOff /> Turn OFF
        </button>
      </div>
    </Card>
  );
};

export default FloodlightControlCard;
