import React, { useState } from "react";
import {
  FaVolumeUp,
  FaVolumeDown,
  FaMicrophone,
  FaBullhorn,
  FaExclamationTriangle,
  FaBell,
} from "react-icons/fa";
import { PiSiren } from "react-icons/pi";
import "./AudioControlCard.css";
import Card from "./Card";

interface SirineButton {
  id: string;
  label: string;
  sirenNum: string;
  icon: React.ReactNode;
}

const sirineButtons: SirineButton[] = [
  { id: "s1", label: "Suara 1", sirenNum: "1", icon: <FaMicrophone /> },
  { id: "s2", label: "Suara 2", sirenNum: "2", icon: <FaMicrophone /> },
  { id: "s3", label: "Suara 3", sirenNum: "3", icon: <FaBullhorn /> },
  { id: "polisi", label: "Polisi", sirenNum: "4", icon: <PiSiren /> },
  { id: "darurat", label: "Darurat", sirenNum: "5", icon: <FaExclamationTriangle /> },
  { id: "beep", label: "Beep", sirenNum: "6", icon: <FaBell /> },
];

const AudioControlCard: React.FC = () => {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [volume, setVolume] = useState(50);
  const [showVolume, setShowVolume] = useState(false);

  const sendMqttCommand = async (command: string, vol?: number) => {
    try {
      const payload: any = { command };
      if (vol !== undefined) {
        payload.volume = vol;
      }
      await fetch("/api/send/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      console.error("Failed to send siren command:", err);
    }
  };

  const commitVolume = async (vol: number) => {
    try {
      await fetch("/api/send/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ volume: vol }),
      });
    } catch (err) {
      console.error("Failed to send volume:", err);
    }
  };

  const handleChannelClick = async (btn: SirineButton) => {
    const isDeactivating = selectedChannel === btn.id;
    const nextChannel = isDeactivating ? null : btn.id;
    setSelectedChannel(nextChannel);

    if (nextChannel) {
      await sendMqttCommand(`SIREN${btn.sirenNum}ON`, volume);
    } else {
      await sendMqttCommand("SIREN#OFF");
    }
  };

  return (
    <Card className="audio-control-card">
      <div className="card-header">
        <div className="icon-container audio">
          <FaVolumeUp />
        </div>
        <div className="header-text">
          <h3 className="card-title">Sirine</h3>
          <p className="card-subtitle">Audio Broadcast</p>
        </div>
        <div className="volume-control">
          <button
            className="volume-button"
            onClick={() => setShowVolume(!showVolume)}
            title="Adjust Volume"
          >
            <FaVolumeUp />
          </button>
          {showVolume && (
            <div className="volume-slider-popup">
              <div className="volume-slider-header">
                <span>Volume</span>
                <span>{volume}%</span>
              </div>
              <div className="volume-slider-container">
                <FaVolumeDown />
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volume}
                  className="volume-slider"
                  onChange={(e) => setVolume(Number(e.target.value))}
                  onMouseUp={() => commitVolume(volume)}
                  onTouchEnd={() => commitVolume(volume)}
                />
                <FaVolumeUp />
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="audio-channels">
        {sirineButtons.map((btn) => (
          <button
            key={btn.id}
            className={`channel-button ${
              selectedChannel === btn.id ? "active" : ""
            }`}
            onClick={() => handleChannelClick(btn)}
          >
            <span className="btn-icon">{btn.icon}</span>
            <span className="btn-label">{btn.label}</span>
          </button>
        ))}
      </div>
    </Card>
  );
};

export default AudioControlCard;