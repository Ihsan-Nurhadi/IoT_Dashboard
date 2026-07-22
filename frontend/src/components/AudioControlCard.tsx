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

const audioChannels = [
  "Audio 1",
  "Audio 2",
  "Audio 3",
  "Audio 4",
  "Audio 5",
  "Audio 6",
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

  const handleChannelClick = async (channel: string) => {
    const isDeactivating = selectedChannel === channel;
    const nextChannel = isDeactivating ? null : channel;
    setSelectedChannel(nextChannel);

    if (nextChannel) {
      const numMatch = nextChannel.match(/\d+/);
      const sirenNum = numMatch ? numMatch[0] : "1";
      await sendMqttCommand(`SIREN${sirenNum}ON`, volume);
    } else {
      await sendMqttCommand("SIREN#OFF");
    }
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
        <div className="volume-control">
          <button
            className="volume-button"
            onClick={() => setShowVolume(!showVolume)}
          >
            <span>Adjust Volume</span>
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
        {audioChannels.map((channel) => (
          <button
            key={channel}
            className={`channel-button ${
              selectedChannel === channel ? "active" : ""
            }`}
            onClick={() => handleChannelClick(channel)}
          >
            <FaMusic />
            <span>{channel}</span>
          </button>
        ))}
      </div>
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