import React, { useState, useEffect } from "react";
import { FaBolt, FaDoorClosed, FaDoorOpen } from "react-icons/fa";
import { PiSiren } from "react-icons/pi";
import Card from "./Card";
import "./DeviceStatusCard.css";

interface DeviceStatusCardProps {
  deviceName: string;
  deviceType: string;
  // Props status awal (opsional)
  status?: string;
}

const DeviceStatusCard: React.FC<DeviceStatusCardProps> = ({
  deviceName,
  deviceType,
}) => {
  const [currentStatus, setCurrentStatus] = useState<string>("Inactive");
  const [lastUpdated, setLastUpdated] = useState<string>("-");

  // Identifikasi tipe device
  const isDoorPanel = deviceName === "Door Panel";
  const isPLN = deviceName === "PLN";
  const isMotion1 = deviceName === "Motion Sensor 1";
  const isMotion2 = deviceName === "Motion Sensor 2";
  const isMotion3 = deviceName === "Motion Sensor 3";
  const isMotion4 = deviceName === "Motion Sensor 4";

  useEffect(() => {
    // Tentukan URL API berdasarkan nama device
    let apiUrl = "";
    if (isDoorPanel) {
      apiUrl = "/api/get-door-status/";
    } else if (isPLN) {
      apiUrl = "/api/get-pln-status/";
    } else if (isMotion1) {
      apiUrl = "/api/get-motion1-status/";
    } else if (isMotion2) {
      apiUrl = "/api/get-motion2-status/";
    } else if (isMotion3) {
      apiUrl = "/api/get-motion3-status/";
    } else if (isMotion4) {
      apiUrl = "/api/get-motion4-status/";
    } else {
      return; // Jika bukan device live, tidak perlu polling
    }

    const fetchStatus = async () => {
      try {
        const response = await fetch(apiUrl);
        const data = await response.json();

        if (data.status) {
          setCurrentStatus(data.status);
        }
        if (data.last_updated) {
          setLastUpdated(data.last_updated);
        }
      } catch (error) {
        console.error(`Error fetching ${deviceName} status:`, error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [deviceName, isDoorPanel, isPLN, isMotion1, isMotion2, isMotion3, isMotion4]);

  // --- LOGIC ICON ---
  const getIcon = () => {
    if (isDoorPanel) {
      // Cek case insensitive untuk OPEN/Open
      return currentStatus.toUpperCase() === "OPEN" ? (
        <FaDoorOpen />
      ) : (
        <FaDoorClosed />
      );
    }
    if (isPLN) {
      return <FaBolt />;
    }
    if (isMotion1 || isMotion2 || isMotion3 || isMotion4) {
      return <PiSiren />;
    }
    return <FaBolt />;
  };

  // --- LOGIC CSS COLOR ---
  // Jika Pintu: OPEN = Active (Hijau)
  // Jika PLN: Active/ON = Active (Hijau)
  // Jika Motion: Detected = Active (Hijau)
  const isActive =
    currentStatus.toUpperCase() === "OPEN" ||
    currentStatus === "Active" ||
    currentStatus === "ON" ||
    currentStatus === "Detected";

  const statusClass = isActive ? "status-active" : "status-inactive";

  return (
    <Card className="device-status-card">
      <div className="card-content">
        <div
          className={`icon-container ${deviceName.toLowerCase().replace(" ", "-")}`}
        >
          {getIcon()}
        </div>
        <div className="device-info">
          <h3 className="device-name">{deviceName}</h3>
          <p className="device-type">{deviceType}</p>
          <p className="timestamp">
            {lastUpdated}
          </p>
        </div>
        <div className={`status-badge ${statusClass}`}>{currentStatus}</div>
      </div>
    </Card>
  );
};

export default DeviceStatusCard;
