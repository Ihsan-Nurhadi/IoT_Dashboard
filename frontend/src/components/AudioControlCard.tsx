import React, { useState } from "react";
import { BsSpeakerFill } from "react-icons/bs";
import {
  FaMusic,
  FaRegPlayCircle,
  FaVolumeDown,
  FaVolumeUp,
} from "react-icons/fa";
import "./AudioControlCard.css";
import Card from "./Card";

const API_URL = "/api/send/"; // sesuaikan dengan backend Anda

const audioChannels = [1, 2, 3, 4, 5, 6];


const AudioControlCard: React.FC = () => {
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [volume, setVolume] = useState(50);
  const [showVolume, setShowVolume] = useState(false);

  // debounce timers
  const [clickTimeout, setClickTimeout] = useState<number | null>(null);
  const [volumeTimeout, setVolumeTimeout] =
    useState<number | null>(null);

  // === SEND TO SERVER ===
  const sendToServer = async (playlist: number) => {
    const payload = {
      device: "site_1",
      playlist: playlist, // Akan dikirim sebagai angka
      volume: volume,
    };

    console.log("Sending:", payload);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      console.log("Response:", data);
    } catch (err) {
      console.error("Error:", err);
    }
  };

  // === HANDLE SPEAKER CLICK ===
  const handleChannelClick = (channel: number) => {
    setSelectedChannel(channel);
    if (clickTimeout) clearTimeout(clickTimeout);
    
    const timeout = window.setTimeout(() => {
      sendToServer(channel);
    }, 1000);
    setClickTimeout(timeout);
  };

  // === HANDLE VOLUME SLIDE ===
  const handleVolumeChange = (value: number) => {
    setVolume(value);

    if (volumeTimeout) clearTimeout(volumeTimeout);

    const timeout = setTimeout(() => {
      if (selectedChannel) {
        sendToServer(selectedChannel);
      }
    }, 1000); // debounce 400ms

    setVolumeTimeout(timeout);
  };

  return (
    <Card className="audio-control-card">
      <div className="card-header">
        <div className="icon-container audio">
          <BsSpeakerFill />
        </div>
        <div className="header-text">
          <h3 className="card-title">Audio Control</h3>
          <p className="card-subtitle">Select audio channel</p>
        </div>

        {/* Volume Button */}
        <div className="volume-control">
          <span className="adjust-volume-text">Adjust Volume</span>
          <button
            className="volume-button"
            onClick={() => setShowVolume(!showVolume)}
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
                  onChange={(e) =>
                    handleVolumeChange(Number(e.target.value))
                  }
                />
                <FaVolumeUp />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Speaker Buttons */}
      <div className="audio-channels">
        {audioChannels.map((channel) => (
          <button
            key={channel}
            className={`channel-button ${
              selectedChannel === channel ? "active" :""
            }`}
            onClick={() => handleChannelClick(channel)}
          >
            <FaMusic />
            <span>{channel}</span>
          </button>
        ))}
      </div>

      {/* Active Channel */}
      {selectedChannel && (
        <div className="active-channel-display">
          <div className="active-channel-info">
            <FaRegPlayCircle />
            <span>Active Channel</span>
          </div>
          <div className="active-channel-name">
            <span className="active-dot"></span>
            {selectedChannel}
          </div>
        </div>
      )}
    </Card>
  );
};

export default AudioControlCard;
