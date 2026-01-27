import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import { useEffect, useState } from "react";
import "leaflet/dist/leaflet.css"; // WAJIB ADA

// Perbaikan icon default leaflet yang sering hilang di React
import L from 'leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

export default function TrackerMap() {
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    const fetchData = () => {
      fetch("http://localhost:8000/api/positions/")
        .then(res => res.json())
        .then(data => setPositions(data))
        .catch(err => console.error("Error fetching data:", err));
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen w-full font-sans">
      {/* Sidebar List Kendaraan */}
      <div className="w-1/4 h-full bg-gray-900 text-white p-4 overflow-y-auto shadow-xl z-[1000]">
        <h1 className="text-xl font-bold mb-4 border-b border-gray-700 pb-2">Fleet Tracker</h1>
        <div className="space-y-3">
          {positions.map((pos) => (
            <div key={pos.id} className="p-3 bg-gray-800 rounded-lg border-l-4 border-blue-500 hover:bg-gray-700 transition">
              <p className="font-semibold text-sm">Vehicle ID: {pos.id}</p>
              <div className="flex justify-between mt-2">
                <span className="text-xs text-gray-400">⚡ {pos.speed} km/h</span>
                <span className={`text-xs px-2 py-0.5 rounded ${pos.attributes?.ignition ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                   {pos.attributes?.ignition ? "Engine ON" : "Engine OFF"}
                </span>
              </div>
            </div>
          ))}
          {positions.length === 0 && <p className="text-gray-500 text-sm italic">Menunggu data...</p>}
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 h-full relative">
        <MapContainer 
          center={[-6.2, 106.8]} 
          zoom={12} 
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {positions.map(pos => (
            <Marker 
              key={pos.id} 
              position={[pos.latitude, pos.longitude]}
            >
              <Popup>
                <div className="text-sm">
                  <strong className="block border-b mb-1">Vehicle Info</strong>
                  <b>Speed:</b> {pos.speed} km/h <br />
                  <b>Status:</b> {pos.attributes?.ignition ? "🟢 Active" : "🔴 Stopped"} <br />
                  <span className="text-[10px] text-gray-500">{pos.latitude}, {pos.longitude}</span>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}