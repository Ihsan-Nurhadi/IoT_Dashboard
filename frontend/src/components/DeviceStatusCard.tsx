import React, { useState, useEffect } from "react";
import { FaBolt, FaDoorClosed, FaDoorOpen } from "react-icons/fa";
import Card from "./Card";
import "./DeviceStatusCard.css";

interface DeviceStatusCardProps {
  deviceName: string;
  deviceType: string;
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

  // Fungsi helper untuk format jam agar enak dilihat (Realtime feel)
  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      // Mengembalikan format jam:menit:detik (Contoh: 15:30:45)
      return date.toLocaleTimeString("id-ID", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch (e) {
      return isoString;
    }
  };

  useEffect(() => {
    // 1. Tentukan URL API (Sesuaikan dengan urls.py di backend baru)
    let apiUrl = "";
    if (isDoorPanel) {
      apiUrl = "/api/devicestatus/get-door-status/";
    } else if (isPLN) {
      apiUrl = "/api/devicestatus/get-pln-status/";
    } else {
      return; 
    }

    const fetchStatus = async () => {
      try {
        // 2. TEKNIK ANTI-CACHE: Tambahkan timestamp (?t=...)
        // Ini memaksa browser request ulang ke server, tidak pakai memori lama
        const uniqueUrl = `${apiUrl}?t=${new Date().getTime()}`;
        
        const response = await fetch(uniqueUrl);
        
        // Cek jika response OK (200)
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // 3. Update State
        if (data.status) {
          setCurrentStatus(data.status);
        }
        
        // Ambil data timestamp dari backend (pastikan fieldnya 'updated_at' atau 'last_updated')
        if (data.updated_at) { 
          setLastUpdated(formatTime(data.updated_at));
        } else if (data.last_updated) {
           setLastUpdated(formatTime(data.last_updated));
        }

      } catch (error) {
        console.error(`Error fetching ${deviceName} status:`, error);
      }
    };

    // Panggil sekali saat mounting
    fetchStatus();

    // Polling setiap 2 detik
    const interval = setInterval(fetchStatus, 2000);

    // Cleanup saat pindah halaman
    return () => clearInterval(interval);
  }, [deviceName, isDoorPanel, isPLN]);

  // --- LOGIC ICON ---
  const getIcon = () => {
    if (isDoorPanel) {
      return currentStatus.toUpperCase() === "OPEN" ? (
        <FaDoorOpen />
      ) : (
        <FaDoorClosed />
      );
    }
    if (isPLN) {
      return <FaBolt />;
    }
    return <FaBolt />;
  };

  // --- LOGIC CSS COLOR ---
  const isActive =
    currentStatus.toUpperCase() === "OPEN" ||
    currentStatus === "Active" ||
    currentStatus === "ON";

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
            {isDoorPanel || isPLN ? lastUpdated : "Static"}
          </p>
        </div>
        <div className={`status-badge ${statusClass}`}>{currentStatus}</div>
      </div>
    </Card>
  );
};

export default DeviceStatusCard;