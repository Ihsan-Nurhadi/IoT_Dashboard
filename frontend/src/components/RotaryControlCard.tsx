import React, { useState } from 'react';
import Card from './Card';
import './RotaryControlCard.css';
import { FaLightbulb } from 'react-icons/fa';

const API_URL = "/api/send-rotary/";

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

  const handleToggle = () => {
    if (loading) return;
    const nextState = isMotorOn ? 0 : 1;
    sendStatus(nextState);
  };

  return (
    <Card className="rotary-control-card">
      <div className="lampu-card-content">
        <div className="lampu-left">
          <div className="icon-container rotary">
            <FaLightbulb />
          </div>
          <div className="header-text">
            <h3 className="card-title">Lampu</h3>
            <p className="card-subtitle">Rotary Light</p>
          </div>
        </div>

        <div className="lampu-right">
          <span className="switch-label">{isMotorOn ? 'ON' : 'OFF'}</span>
          <button 
            className={`toggle-switch-btn ${isMotorOn ? 'on' : 'off'}`}
            onClick={handleToggle}
            disabled={loading}
            title={isMotorOn ? "Matikan Lampu" : "Nyalakan Lampu"}
          >
            <span className="toggle-switch-slider"></span>
          </button>
        </div>
      </div>
    </Card>
  );
};

export default RotaryControlCard;

