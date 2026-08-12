import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './AdminDashboard.css';

interface BLEDevice {
  mac: string;
  name: string;
  location: string;
  installation_date: string | null;
  vendor: string;
  height: string;
  rssi_threshold: number;
  image: string | null;
  is_active: boolean;
}

interface UnregisteredBeacon {
  mac: string;
  name: string;
  rssi: number;
  last_seen: string;
}

const AdminDashboard: React.FC = () => {
  const [devices, setDevices] = useState<BLEDevice[]>([]);
  const [unregistered, setUnregistered] = useState<UnregisteredBeacon[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingUnregistered, setLoadingUnregistered] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  // Tab and Cameras States
  interface CCTVCamera {
    camera_id: string;
    camera_name: string;
    rtsp_url: string;
    onvif_url: string | null;
    username: string | null;
    password?: string | null;
    width: number;
    height: number;
    is_active: boolean;
    detection_zones: { name: string; points: [number, number][] }[];
  }

  const [cameras, setCameras] = useState<CCTVCamera[]>([]);
  const [loadingCameras, setLoadingCameras] = useState<boolean>(false);
  const [activeSection, setActiveSection] = useState<'ble' | 'cctv'>('ble');

  // Camera Form & Modal States
  const [isCameraModalOpen, setIsCameraModalOpen] = useState<boolean>(false);
  const [selectedCamera, setSelectedCamera] = useState<CCTVCamera | null>(null);
  const [isCameraEditMode, setIsCameraEditMode] = useState<boolean>(false);
  const [formCamId, setFormCamId] = useState<string>('');
  
  const [camName, setCamName] = useState<string>('');
  const [camRtsp, setCamRtsp] = useState<string>('');
  const [camOnvif, setCamOnvif] = useState<string>('');
  const [camUser, setCamUser] = useState<string>('');
  const [camPass, setCamPass] = useState<string>('');
  const [camWidth, setCamWidth] = useState<number>(1920);
  const [camHeight, setCamHeight] = useState<number>(1080);
  const [camActive, setCamActive] = useState<boolean>(true);

  // Zone Drawing States
  const [zones, setZones] = useState<{ name: string; points: [number, number][] }[]>([]);
  const [activeZoneIndex, setActiveZoneIndex] = useState<number | null>(null);
  const [snapshotUrl, setSnapshotUrl] = useState<string>('/contoh cctv.jpg');
  const [baselinesStatus, setBaselinesStatus] = useState<{ morning: boolean; afternoon: boolean; night: boolean }>({
    morning: false,
    afternoon: false,
    night: false
  });
  const [loadingSnapshot, setLoadingSnapshot] = useState<boolean>(false);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragTargetRef = useRef<{ zoneIndex: number; pointIndex: number } | null>(null);

  // Modal & Form States for BLE Devices
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isEditMode, setIsEditMode] = useState<boolean>(false);
  
  const [formMac, setFormMac] = useState<string>('');
  const [formName, setFormName] = useState<string>('');
  const [formLocation, setFormLocation] = useState<string>('Sector A - Upper Level');
  const [formInstallDate, setFormInstallDate] = useState<string>('');
  const [formVendor, setFormVendor] = useState<string>('Huawei');
  const [formHeight, setFormHeight] = useState<string>('38 Meter');
  const [formRssiThreshold, setFormRssiThreshold] = useState<number>(-75);
  const [formIsActive, setFormIsActive] = useState<boolean>(true);
  const [formImageFile, setFormImageFile] = useState<File | null>(null);
  const [formImagePreview, setFormImagePreview] = useState<string | null>(null);
  const [clearImage, setClearImage] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Load registered devices, unregistered beacons, and cameras
  useEffect(() => {
    fetchDevices();
    fetchUnregistered();
    fetchCameras();
    const interval = setInterval(() => {
      fetchUnregistered();
    }, 10000); // refresh unregistered scans every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/ble/devices/');
      if (res.ok) {
        const data = await res.json();
        setDevices(data);
      } else {
        setError('Gagal memuat daftar BLE device terdaftar');
      }
    } catch (err) {
      console.error(err);
      setError('Kesalahan jaringan saat memuat BLE device');
    } finally {
      setLoading(false);
    }
  };

  const fetchUnregistered = async () => {
    try {
      setLoadingUnregistered(true);
      const res = await fetch('/api/ble/devices/scanned-unregistered/');
      if (res.ok) {
        const data = await res.json();
        setUnregistered(data);
      }
    } catch (err) {
      console.error('Error fetching unregistered scans:', err);
    } finally {
      setLoadingUnregistered(false);
    }
  };

  const fetchCameras = async () => {
    try {
      setLoadingCameras(true);
      const res = await fetch('/api/cameras/');
      if (res.ok) {
        const data = await res.json();
        setCameras(data);
      } else {
        setError('Gagal memuat daftar CCTV Camera');
      }
    } catch (err) {
      console.error(err);
      setError('Kesalahan jaringan saat memuat CCTV Camera');
    } finally {
      setLoadingCameras(false);
    }
  };

  const openAddCameraModal = () => {
    setSelectedCamera(null);
    setIsCameraEditMode(false);
    setFormCamId('');
    setCamName('');
    setCamRtsp('');
    setCamOnvif('');
    setCamUser('');
    setCamPass('');
    setCamWidth(1920);
    setCamHeight(1080);
    setCamActive(true);
    setZones([]);
    setActiveZoneIndex(null);
    setSnapshotUrl('/contoh cctv.jpg');
    setBaselinesStatus({ morning: false, afternoon: false, night: false });
    setIsCameraModalOpen(true);
  };

  const openEditCameraModal = async (cam: CCTVCamera) => {
    setSelectedCamera(cam);
    setIsCameraEditMode(true);
    setFormCamId(cam.camera_id);
    setCamName(cam.camera_name);
    setCamRtsp(cam.rtsp_url);
    setCamOnvif(cam.onvif_url || '');
    setCamUser(cam.username || '');
    setCamPass('');
    setCamWidth(cam.width);
    setCamHeight(cam.height);
    setCamActive(cam.is_active);
    setZones(cam.detection_zones || []);
    setActiveZoneIndex(null);
    setBaselinesStatus({ morning: false, afternoon: false, night: false });
    fetchBaselinesStatus(cam.camera_id);
    setIsCameraModalOpen(true);
    
    // Load snapshot
    try {
      setLoadingSnapshot(true);
      setSnapshotUrl('/contoh cctv.jpg');
      const res = await fetch(`/api/cameras/${cam.camera_id}/snapshot/`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setSnapshotUrl(data.url);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingSnapshot(false);
    }
  };

  const refreshCameraSnapshot = async () => {
    const activeId = isCameraEditMode ? selectedCamera?.camera_id : formCamId.trim();
    if (!activeId) {
      alert('Masukkan Camera ID dan simpan kamera terlebih dahulu untuk mengambil snapshot');
      return;
    }
    try {
      setLoadingSnapshot(true);
      const res = await fetch(`/api/cameras/${activeId}/snapshot/`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setSnapshotUrl(data.url + '&nocache=' + new Date().getTime());
        } else {
          alert('Gagal mengambil gambar snapshot dari kamera RTSP: ' + (data.message || 'Error'));
        }
      }
    } catch (err) {
      console.error(err);
      alert('Error saat merefresh snapshot');
    } finally {
      setLoadingSnapshot(false);
    }
  };

  const fetchBaselinesStatus = async (camId: string) => {
    try {
      const res = await fetch(`/api/cctv/baselines-status/?camera_id=${camId}`);
      if (res.ok) {
        const data = await res.json();
        setBaselinesStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch baselines status:", err);
    }
  };

  const handleCaptureBaselineSlot = async (tod: 'morning' | 'afternoon' | 'night') => {
    const camId = isCameraEditMode ? selectedCamera?.camera_id : formCamId.trim();
    if (!camId) {
      alert("Simpan kamera terlebih dahulu sebelum merekam baseline.");
      return;
    }
    setLoadingSnapshot(true);
    try {
      const res = await fetch(`/api/cctv/capture-baseline/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ camera_id: camId, tod })
      });
      if (res.ok) {
        alert(`Baseline ${tod === 'morning' ? 'Pagi' : tod === 'afternoon' ? 'Siang' : 'Malam'} berhasil direkam untuk semua zona!`);
        fetchBaselinesStatus(camId);
      } else {
        const data = await res.json();
        alert(`Gagal merekam baseline: ${data.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error capturing baseline.");
    } finally {
      setLoadingSnapshot(false);
    }
  };

  const handleDeleteBaselineSlot = async (tod: 'morning' | 'afternoon' | 'night') => {
    const camId = isCameraEditMode ? selectedCamera?.camera_id : formCamId.trim();
    if (!camId) return;
    if (!window.confirm(`Apakah Anda yakin ingin menghapus baseline ${tod === 'morning' ? 'Pagi' : tod === 'afternoon' ? 'Siang' : 'Malam'} untuk semua zona kamera ini?`)) {
      return;
    }
    setLoadingSnapshot(true);
    try {
      const res = await fetch(`/api/cctv/delete-baseline/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ camera_id: camId, tod })
      });
      if (res.ok) {
        alert(`Baseline ${tod === 'morning' ? 'Pagi' : tod === 'afternoon' ? 'Siang' : 'Malam'} berhasil dihapus.`);
        fetchBaselinesStatus(camId);
      } else {
        alert("Gagal menghapus baseline.");
      }
    } catch (err) {
      console.error(err);
      alert("Error deleting baseline.");
    } finally {
      setLoadingSnapshot(false);
    }
  };

  const handleCameraSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const activeId = isCameraEditMode ? selectedCamera?.camera_id : formCamId.trim();
    if (!activeId) {
      setError('Camera ID harus diisi');
      return;
    }

    // Validate detection zones points count (minimal 3, maksimal 5)
    for (const zone of zones) {
      if (zone.points.length < 3) {
        setError(`Zone "${zone.name}" harus memiliki minimal 3 titik untuk menandakan antena (saat ini: ${zone.points.length} titik).`);
        return;
      }
      if (zone.points.length > 5) {
        setError(`Zone "${zone.name}" tidak boleh memiliki lebih dari 5 titik (saat ini: ${zone.points.length} titik).`);
        return;
      }
    }
    
    try {
      const payload = {
        camera_id: activeId,
        camera_name: camName,
        rtsp_url: camRtsp,
        onvif_url: camOnvif,
        username: camUser,
        password: camPass,
        width: camWidth,
        height: camHeight,
        is_active: camActive,
        detection_zones: zones
      };
      
      const url = isCameraEditMode 
        ? `/api/cameras/${activeId}/update/` 
        : `/api/cameras/create/`;
        
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken') || ''
        },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        showSuccess(isCameraEditMode ? 'Konfigurasi Kamera & Detection Zone berhasil disimpan' : 'Kamera CCTV baru berhasil ditambahkan');
        setIsCameraModalOpen(false);
        fetchCameras();
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.error || err.detail || err.message || 'Gagal menyimpan konfigurasi kamera');
      }
    } catch (err) {
      console.error(err);
      setError('Kesalahan jaringan saat menyimpan konfigurasi kamera');
    }
  };

  const handleDeleteCamera = async (camId: string) => {
    if (!window.confirm(`Apakah Anda yakin ingin menghapus kamera CCTV ${camId}?`)) {
      return;
    }
    try {
      const res = await fetch(`/api/cameras/${camId}/delete/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken') || ''
        }
      });
      if (res.ok) {
        showSuccess('Kamera CCTV berhasil dihapus');
        fetchCameras();
      } else {
        setError('Gagal menghapus kamera CCTV');
      }
    } catch (err) {
      console.error(err);
      setError('Gagal menghapus kamera CCTV karena masalah jaringan');
    }
  };

  const getCookie = (name: string) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  };

  // Canvas multiple zones drawer functions
  const redrawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    zones.forEach((zone, zoneIdx) => {
      const isSelected = zoneIdx === activeZoneIndex;
      const points = zone.points;
      if (points.length === 0) return;

      // Draw polygon lines
      ctx.beginPath();
      ctx.moveTo(points[0][0] * canvas.width, points[0][1] * canvas.height);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i][0] * canvas.width, points[i][1] * canvas.height);
      }
      if (points.length >= 3) {
        ctx.closePath();
      }

      ctx.strokeStyle = isSelected ? '#22d3ee' : 'rgba(239, 68, 68, 0.7)';
      ctx.lineWidth = isSelected ? 3 : 2;
      ctx.setLineDash(isSelected ? [5, 5] : []);
      ctx.stroke();

      ctx.fillStyle = isSelected ? 'rgba(34, 211, 238, 0.12)' : 'rgba(239, 68, 68, 0.05)';
      ctx.fill();

      // Draw control vertices
      points.forEach((pt) => {
        ctx.beginPath();
        ctx.arc(pt[0] * canvas.width, pt[1] * canvas.height, 6, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? '#22d3ee' : '#ef4444';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.fill();
        ctx.stroke();
      });

      // Label Text
      ctx.font = 'bold 11px sans-serif';
      ctx.fillStyle = isSelected ? '#22d3ee' : '#ef4444';
      ctx.fillText(zone.name, points[0][0] * canvas.width, points[0][1] * canvas.height - 10);
    });
  };

  useEffect(() => {
    if (isCameraModalOpen) {
      const timer = setTimeout(() => {
        redrawCanvas();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isCameraModalOpen, zones, activeZoneIndex]);

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    // Check if clicked close to any point in the active zone
    if (activeZoneIndex !== null) {
      const activeZone = zones[activeZoneIndex];
      let foundPointIdx = -1;
      activeZone.points.forEach((pt, idx) => {
        const dist = Math.sqrt(Math.pow(pt[0] - x, 2) + Math.pow(pt[1] - y, 2));
        if (dist < 0.03) {
          foundPointIdx = idx;
        }
      });

      if (foundPointIdx !== -1) {
        dragTargetRef.current = { zoneIndex: activeZoneIndex, pointIndex: foundPointIdx };
        return;
      }
    }

    // Check other zones to select one
    let activatedZoneIdx: number | null = null;
    let activatedPtIdx = -1;
    zones.forEach((zone, zIdx) => {
      zone.points.forEach((pt, pIdx) => {
        const dist = Math.sqrt(Math.pow(pt[0] - x, 2) + Math.pow(pt[1] - y, 2));
        if (dist < 0.03) {
          activatedZoneIdx = zIdx;
          activatedPtIdx = pIdx;
        }
      });
    });

    if (activatedZoneIdx !== null) {
      setActiveZoneIndex(activatedZoneIdx);
      dragTargetRef.current = { zoneIndex: activatedZoneIdx, pointIndex: activatedPtIdx };
      return;
    }

    // If active zone exists, add a point
    if (activeZoneIndex !== null) {
      const currentPoints = zones[activeZoneIndex].points;
      if (currentPoints.length >= 5) {
        alert('Maksimal 5 titik untuk menandakan satu area antena!');
        return;
      }
      const updatedZones = [...zones];
      updatedZones[activeZoneIndex].points.push([x, y]);
      setZones(updatedZones);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!dragTargetRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

    const { zoneIndex, pointIndex } = dragTargetRef.current;
    const updatedZones = [...zones];
    updatedZones[zoneIndex].points[pointIndex] = [x, y];
    setZones(updatedZones);
    redrawCanvas();
  };

  const handleCanvasMouseUp = () => {
    dragTargetRef.current = null;
  };

  const handleAddZone = () => {
    const newZone = {
      name: `Antena ${zones.length + 1}`,
      points: [] as [number, number][]
    };
    setZones([...zones, newZone]);
    setActiveZoneIndex(zones.length);
  };

  const handleDeleteZone = (index: number) => {
    const updated = zones.filter((_, idx) => idx !== index);
    setZones(updated);
    if (activeZoneIndex === index) {
      setActiveZoneIndex(null);
    } else if (activeZoneIndex !== null && activeZoneIndex > index) {
      setActiveZoneIndex(activeZoneIndex - 1);
    }
  };

  const handleZoneNameChange = (index: number, name: string) => {
    const updated = [...zones];
    updated[index].name = name;
    setZones(updated);
  };

  const handleClearActiveZone = () => {
    if (activeZoneIndex === null) return;
    const updated = [...zones];
    updated[activeZoneIndex].points = [];
    setZones(updated);
    redrawCanvas();
  };

  const handleLogout = async () => {
    try {
      const res = await fetch('/api/auth/logout/', { method: 'POST' });
      if (res.ok) {
        navigate('/login');
      }
    } catch (err) {
      console.error(err);
      navigate('/login');
    }
  };

  const openAddModal = () => {
    setIsEditMode(false);
    setFormMac('');
    setFormName('');
    setFormLocation('Sector A - Upper Level');
    setFormInstallDate('');
    setFormVendor('Huawei');
    setFormHeight('38 Meter');
    setFormRssiThreshold(-75);
    setFormIsActive(true);
    setFormImageFile(null);
    setFormImagePreview(null);
    setClearImage(false);
    setError('');
    setIsModalOpen(true);
  };

  const openEditModal = (device: BLEDevice) => {
    setIsEditMode(true);
    setFormMac(device.mac);
    setFormName(device.name);
    setFormLocation(device.location);
    setFormInstallDate(device.installation_date || '');
    setFormVendor(device.vendor);
    setFormHeight(device.height);
    setFormRssiThreshold(device.rssi_threshold);
    setFormIsActive(device.is_active);
    setFormImageFile(null);
    setFormImagePreview(device.image || null);
    setClearImage(false);
    setError('');
    setIsModalOpen(true);
  };

  const handleQuickRegister = (beacon: UnregisteredBeacon) => {
    setIsEditMode(false);
    setFormMac(beacon.mac);
    setFormName(beacon.name || 'Antena Baru');
    setFormLocation('Sector A - Upper Level');
    setFormInstallDate(new Date().toISOString().split('T')[0]);
    setFormVendor('Huawei');
    setFormHeight('38 Meter');
    setFormRssiThreshold(-75);
    setFormIsActive(true);
    setFormImageFile(null);
    setFormImagePreview(null);
    setClearImage(false);
    setError('');
    setIsModalOpen(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFormImageFile(file);
      setClearImage(false);

      // Create local preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setFormImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemovePreview = () => {
    setFormImageFile(null);
    setFormImagePreview(null);
    setClearImage(true);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDeleteDevice = async (mac: string) => {
    if (!window.confirm(`Apakah Anda yakin ingin menghapus konfigurasi BLE device ${mac}?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/ble/devices/${mac}/delete/`, {
        method: 'POST',
      });
      if (res.ok) {
        showSuccess('BLE Device berhasil dihapus');
        fetchDevices();
        fetchUnregistered();
      } else {
        setError('Gagal menghapus BLE Device');
      }
    } catch (err) {
      console.error(err);
      setError('Gagal menghapus BLE device karena masalah jaringan');
    }
  };

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => {
      setSuccessMsg('');
    }, 4000);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formMac.trim() || !formName.trim()) {
      setError('MAC Address dan Nama Perangkat harus diisi.');
      return;
    }

    // Build Form Data for file upload
    const formData = new FormData();
    formData.append('mac', formMac.trim());
    formData.append('name', formName.trim());
    formData.append('location', formLocation);
    formData.append('installation_date', formInstallDate || '');
    formData.append('vendor', formVendor);
    formData.append('height', formHeight);
    formData.append('rssi_threshold', formRssiThreshold.toString());
    formData.append('is_active', formIsActive.toString());

    if (formImageFile) {
      formData.append('image', formImageFile);
    } else if (clearImage) {
      formData.append('clear_image', 'true');
    }

    const url = isEditMode ? `/api/ble/devices/${formMac}/` : '/api/ble/devices/';
    const method = isEditMode ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method: method,
        body: formData, // No 'Content-Type' header here, browser sets boundary
      });

      if (res.ok) {
        showSuccess(isEditMode ? 'Konfigurasi device berhasil diperbarui' : 'Device baru berhasil didaftarkan');
        setIsModalOpen(false);
        fetchDevices();
        fetchUnregistered();
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.error || errData.detail || `Gagal menyimpan konfigurasi BLE Device (HTTP Status: ${res.status})`);
      }
    } catch (err) {
      console.error(err);
      setError('Kesalahan jaringan saat menyimpan konfigurasi');
    }
  };

  return (
    <div className="admin-dashboard">
      {/* Navbar */}
      <header className="admin-header">
        <div className="header-brand">
          <div className="brand-logo">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="logo-svg">
              <path d="M5 22h14M12 2v20M17 12a5 5 0 0 0-10 0M19 7a8.5 8.5 0 0 0-14 0" />
            </svg>
          </div>
          <div>
            <h1>BLE Sentinel Admin</h1>
            <p>Control Panel & Asset Configurator</p>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn-danger" onClick={handleLogout}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="btn-icon">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
            </svg>
            Sign Out
          </button>
        </div>
      </header>

      <main className="admin-content">
        {/* Tab Selection Navigation */}
        <div className="admin-tabs-nav">
          <button 
            type="button"
            className={`tab-nav-item ${activeSection === 'ble' ? 'active' : ''}`}
            onClick={() => setActiveSection('ble')}
          >
            📶 BLE Beacon Management
          </button>
          <button 
            type="button"
            className={`tab-nav-item ${activeSection === 'cctv' ? 'active' : ''}`}
            onClick={() => setActiveSection('cctv')}
          >
            🎥 CCTV Camera Settings
          </button>
          <button 
            type="button"
            className="tab-nav-item portal-link-btn"
            onClick={() => navigate('/')}
          >
            🏠 Portal Dashboard
          </button>
        </div>

        {/* Alerts */}
        {error && (
          <div className="admin-alert alert-error">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="alert-icon">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{error}</span>
            <button className="alert-close" onClick={() => setError('')}>&times;</button>
          </div>
        )}

        {successMsg && (
          <div className="admin-alert alert-success">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="alert-icon">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3"/>
            </svg>
            <span>{successMsg}</span>
            <button className="alert-close" onClick={() => setSuccessMsg('')}>&times;</button>
          </div>
        )}

        {activeSection === 'ble' ? (
          <div className="admin-grid">
            {/* Left Column: Registered Devices */}
            <section className="grid-card devices-card">
              <div className="card-header">
                <div>
                  <h2>Registered BLE Devices ({devices.length})</h2>
                  <p>Perangkat BLE yang dikonfigurasi aktif untuk alarm pencurian & pemantauan dashboard.</p>
                </div>
                <button className="btn-primary" onClick={openAddModal}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="btn-icon">
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Tambah Device
                </button>
              </div>

              {loading ? (
                <div className="loading-container">
                  <div className="spinner"></div>
                  <p>Memuat konfigurasi BLE device...</p>
                </div>
              ) : devices.length === 0 ? (
                <div className="empty-state">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="empty-icon">
                    <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3zM6 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3z" />
                  </svg>
                  <p>Belum ada BLE device yang terdaftar.</p>
                  <button className="btn-secondary" style={{ marginTop: '12px' }} onClick={openAddModal}>Daftarkan sekarang</button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Gambar</th>
                        <th>Nama Antena</th>
                        <th>MAC Address</th>
                        <th>Lokasi / Vendor</th>
                        <th>Tinggi Tower</th>
                        <th>Threshold RSSI</th>
                        <th>Status</th>
                        <th>Aksi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {devices.map((device) => (
                        <tr key={device.mac}>
                          <td>
                            <div className="device-thumbnail">
                              {device.image ? (
                                <img src={device.image} alt={device.name} />
                              ) : (
                                <div className="placeholder-thumb">
                                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M5 22h14M12 2v20" />
                                  </svg>
                                </div>
                              )}
                            </div>
                          </td>
                          <td>
                            <span className="device-name">{device.name}</span>
                          </td>
                          <td>
                            <code className="device-mac">{device.mac}</code>
                          </td>
                          <td>
                            <div className="device-location-info">
                              <span>{device.location}</span>
                              <span className="subtext">{device.vendor}</span>
                            </div>
                          </td>
                          <td>{device.height}</td>
                          <td>
                            <span className="device-threshold">{device.rssi_threshold} dBm</span>
                          </td>
                          <td>
                            <span className={`status-badge ${device.is_active ? 'badge-active' : 'badge-inactive'}`}>
                              {device.is_active ? 'Monitored' : 'Disabled'}
                            </span>
                          </td>
                          <td>
                            <div className="table-actions">
                              <button className="btn-icon-only edit-btn" onClick={() => openEditModal(device)} title="Edit Device">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="action-svg">
                                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4z"/>
                                </svg>
                              </button>
                              <button className="btn-icon-only delete-btn" onClick={() => handleDeleteDevice(device.mac)} title="Hapus Device">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="action-svg">
                                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Right Column: Auto Discovery MQTT */}
            <section className="grid-card discovery-card">
              <div className="card-header">
                <div>
                  <h2>MQTT Auto-Discovery</h2>
                  <p>Perangkat BLE terdekat yang baru dideteksi gateway MQTT namun belum terdaftar.</p>
                </div>
                <button className="btn-refresh" onClick={fetchUnregistered} disabled={loadingUnregistered}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className={`btn-icon ${loadingUnregistered ? 'spin' : ''}`}>
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                  </svg>
                </button>
              </div>

              {loadingUnregistered && unregistered.length === 0 ? (
                <div className="loading-container">
                  <div className="spinner"></div>
                  <p>Memindai sinyal MQTT...</p>
                </div>
              ) : unregistered.length === 0 ? (
                <div className="empty-state mini">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="empty-icon">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
                  <p>Tidak ada device baru terdeteksi dalam 24 jam terakhir.</p>
                  <span className="subtext">Sistem terus memantau topik BLE-TEST...</span>
                </div>
              ) : (
                <div className="beacon-list">
                  {unregistered.map((beacon) => (
                    <div className="beacon-item" key={beacon.mac}>
                      <div className="beacon-info">
                        <div className="beacon-header">
                          <span className="beacon-name">{beacon.name || 'Unknown Beacon'}</span>
                          <code className="beacon-mac">{beacon.mac}</code>
                        </div>
                        <div className="beacon-meta">
                          <span className="beacon-rssi">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="rssi-svg">
                              <path d="M12 20h.01M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 14 0M1.5 9.5a15 15 0 0 1 21 0" />
                            </svg>
                            {beacon.rssi} dBm
                          </span>
                          <span className="beacon-time">Last seen: {new Date(beacon.last_seen).toLocaleTimeString()}</span>
                        </div>
                      </div>
                      <button className="btn-primary btn-sm" onClick={() => openAddModalFromDiscovery(beacon)}>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="btn-icon">
                          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                        </svg>
                        Daftar
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        ) : (
          /* CCTV Camera configuration interface */
          <div className="cameras-grid-section">
            <section className="grid-card cameras-card">
              <div className="card-header">
                <div>
                  <h2>CCTV Cameras ({cameras.length})</h2>
                  <p>Konfigurasi parameter RTSP stream, ONVIF endpoint, dan Drawing Detection Zone antena.</p>
                </div>
                <button type="button" className="btn-primary" onClick={openAddCameraModal}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="btn-icon">
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Tambah Kamera
                </button>
              </div>

              {loadingCameras ? (
                <div className="loading-container">
                  <div className="spinner"></div>
                  <p>Memuat daftar kamera...</p>
                </div>
              ) : cameras.length === 0 ? (
                <div className="empty-state">
                  <p>Belum ada kamera CCTV terkonfigurasi di database.</p>
                  <button type="button" className="btn-secondary" style={{ marginTop: '12px' }} onClick={openAddCameraModal}>Tambahkan kamera sekarang</button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Nama Kamera</th>
                        <th>ID Kamera</th>
                        <th>RTSP URL</th>
                        <th>ONVIF Service URL</th>
                        <th>Username</th>
                        <th>Detection Zones</th>
                        <th>Status</th>
                        <th>Aksi</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cameras.map((cam) => (
                        <tr key={cam.camera_id}>
                          <td>
                            <span className="device-name" style={{ fontWeight: 600 }}>{cam.camera_name}</span>
                          </td>
                          <td>
                            <code>{cam.camera_id}</code>
                          </td>
                          <td>
                            <code className="text-truncate" style={{ maxWidth: '220px', display: 'inline-block' }} title={cam.rtsp_url}>{cam.rtsp_url}</code>
                          </td>
                          <td>
                            <code className="text-truncate" style={{ maxWidth: '220px', display: 'inline-block' }} title={cam.onvif_url || ''}>{cam.onvif_url || '-'}</code>
                          </td>
                          <td>{cam.username || '-'}</td>
                          <td>
                            <span className="badge-count" style={{ background: 'rgba(34,211,238,0.1)', color: '#22d3ee', padding: '3px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold' }}>
                              {cam.detection_zones?.length || 0} Antena Zone
                            </span>
                          </td>
                          <td>
                            <span className={`status-badge ${cam.is_active ? 'badge-active' : 'badge-inactive'}`}>
                              {cam.is_active ? 'Active' : 'Disabled'}
                            </span>
                          </td>
                          <td>
                            <div className="table-actions">
                              <button 
                                type="button"
                                className="btn-primary edit-btn" 
                                onClick={() => openEditCameraModal(cam)} 
                                style={{ padding: '8px 14px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: '13px', height: '13px' }}>
                                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4z"/>
                                </svg>
                                Edit & Draw Zones
                              </button>
                              <button 
                                type="button"
                                className="btn-icon-only delete-btn" 
                                onClick={() => handleDeleteCamera(cam.camera_id)} 
                                title="Hapus Kamera"
                                style={{ width: '34px', height: '34px' }}
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="action-svg">
                                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        )}
      </main>

      {/* Add / Edit BLE Device Form Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-container">
            <div className="modal-header">
              <h3>{isEditMode ? 'Edit BLE Device Config' : 'Register New BLE Device'}</h3>
              <button className="modal-close-btn" onClick={() => setIsModalOpen(false)}>&times;</button>
            </div>
            
            <form onSubmit={handleFormSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group full-width">
                  <label htmlFor="device-mac">MAC Address *</label>
                  <input
                    id="device-mac"
                    type="text"
                    value={formMac}
                    onChange={(e) => setFormMac(e.target.value)}
                    placeholder="7C:D9:F4:03:32:47"
                    disabled={isEditMode}
                    required
                  />
                  <small className="help-text">MAC address unik dari perangkat BLE (tidak dapat diubah setelah didaftarkan).</small>
                </div>

                <div className="form-group">
                  <label htmlFor="device-name">Nama Antena *</label>
                  <input
                    id="device-name"
                    type="text"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="Contoh: BTSID TII"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="device-location">Deskripsi Lokasi</label>
                  <input
                    id="device-location"
                    type="text"
                    value={formLocation}
                    onChange={(e) => setFormLocation(e.target.value)}
                    placeholder="Contoh: Sector A - Upper Level"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="device-vendor">Vendor</label>
                  <input
                    id="device-vendor"
                    type="text"
                    value={formVendor}
                    onChange={(e) => setFormVendor(e.target.value)}
                    placeholder="Huawei"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="device-height">Tinggi Pemasangan</label>
                  <input
                    id="device-height"
                    type="text"
                    value={formHeight}
                    onChange={(e) => setFormHeight(e.target.value)}
                    placeholder="38 Meter"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="device-date">Tanggal Instalasi</label>
                  <input
                    id="device-date"
                    type="date"
                    value={formInstallDate}
                    onChange={(e) => setFormInstallDate(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="device-threshold">Batas Alarm RSSI (dBm) *</label>
                  <input
                    id="device-threshold"
                    type="number"
                    value={formRssiThreshold}
                    onChange={(e) => setFormRssiThreshold(Number(e.target.value))}
                    min="-110"
                    max="-30"
                    required
                  />
                  <small className="help-text">Jika sinyal drop di bawah nilai ini (misal -75), alarm pencurian menyala.</small>
                </div>

                {/* Antenna Image Upload Field */}
                <div className="form-group full-width image-upload-group">
                  <label>Gambar / Foto Antena</label>
                  <div className="image-upload-wrapper">
                    {formImagePreview ? (
                      <div className="image-preview-card">
                        <img src={formImagePreview} alt="Preview" />
                        <button type="button" className="remove-preview-btn" onClick={handleRemovePreview} title="Hapus Gambar">
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="action-svg">
                            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <div className="image-upload-placeholder" onClick={() => fileInputRef.current?.click()}>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="upload-icon">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                        </svg>
                        <span>Pilih atau Unggah Foto Antena</span>
                        <span className="subtext">Format yang didukung: JPG, PNG, atau JPEG</span>
                      </div>
                    )}
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept="image/*"
                      style={{ display: 'none' }}
                    />
                  </div>
                </div>

                <div className="form-group full-width checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formIsActive}
                      onChange={(e) => setFormIsActive(e.target.checked)}
                    />
                    <span>Aktifkan pemantauan real-time pada dashboard</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsModalOpen(false)}>Batal</button>
                <button type="submit" className="btn-primary">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="btn-icon">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2zM17 21v-8H7v8M7 3v5h8"/>
                  </svg>
                  Simpan Konfigurasi
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CCTV Camera Edit/Add Modal */}
      {isCameraModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-container camera-modal-container">
            <div className="modal-header">
              <h3>{isCameraEditMode ? `Edit Camera Config: ${selectedCamera?.camera_name}` : 'Add New CCTV Camera'}</h3>
              <button type="button" className="modal-close-btn" onClick={() => setIsCameraModalOpen(false)}>&times;</button>
            </div>
            
            <form onSubmit={handleCameraSubmit} className="modal-form">
              <div className="camera-modal-grid">
                
                {/* Left Side: Form Controls */}
                <div className="camera-form-controls">
                  {!isCameraEditMode && (
                    <div className="form-group">
                      <label htmlFor="cam-id">Camera ID *</label>
                      <input
                        id="cam-id"
                        type="text"
                        value={formCamId}
                        onChange={(e) => setFormCamId(e.target.value)}
                        placeholder="Contoh: cctv3 (tanpa spasi)"
                        required
                      />
                      <small className="help-text">ID unik kamera untuk API (misal cctv3, cctv4).</small>
                    </div>
                  )}

                  <div className="form-group">
                    <label htmlFor="cam-name">Nama Kamera *</label>
                    <input
                      id="cam-name"
                      type="text"
                      value={camName}
                      onChange={(e) => setCamName(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="cam-rtsp">RTSP Stream URL *</label>
                    <input
                      id="cam-rtsp"
                      type="text"
                      value={camRtsp}
                      onChange={(e) => setCamRtsp(e.target.value)}
                      required
                    />
                    <small className="help-text">Contoh: <code>rtsp://10.10.1.170:556/stream1</code></small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="cam-onvif">ONVIF Device Service URL</label>
                    <input
                      id="cam-onvif"
                      type="text"
                      value={camOnvif}
                      onChange={(e) => setCamOnvif(e.target.value)}
                      placeholder="http://10.10.1.170:2023/onvif/device_service"
                    />
                    <small className="help-text">Contoh: <code>http://10.10.1.170:2023/onvif/device_service</code></small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="cam-user">Username</label>
                    <input
                      id="cam-user"
                      type="text"
                      value={camUser}
                      onChange={(e) => setCamUser(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="cam-pass">Password</label>
                    <input
                      id="cam-pass"
                      type="password"
                      value={camPass}
                      onChange={(e) => setCamPass(e.target.value)}
                      placeholder="Biarkan kosong untuk mempertahankan password lama"
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="cam-w">Stream Width</label>
                      <input
                        id="cam-w"
                        type="number"
                        value={camWidth}
                        onChange={(e) => setCamWidth(Number(e.target.value))}
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="cam-h">Stream Height</label>
                      <input
                        id="cam-h"
                        type="number"
                        value={camHeight}
                        onChange={(e) => setCamHeight(Number(e.target.value))}
                      />
                    </div>
                  </div>

                  <div className="form-group checkbox-group">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={camActive}
                        onChange={(e) => setCamActive(e.target.checked)}
                      />
                      <span>Kamera Aktif & Pantau Sinyal</span>
                    </label>
                  </div>

                  {/* Baseline Slots configuration (M, A, N) */}
                  {isCameraEditMode && (
                    <div className="baseline-config-container" style={{ marginTop: '24px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '20px' }}>
                      <h5 style={{ color: '#fff', fontSize: '0.95rem', margin: '0 0 12px 0', fontWeight: 500 }}>BaseLine</h5>
                      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                        {(['morning', 'afternoon', 'night'] as const).map((tod) => {
                          const hasBaseline = baselinesStatus[tod];
                          const labelMap = { morning: 'M', afternoon: 'A', night: 'N' };
                          const nameMap = { morning: 'Pagi', afternoon: 'Siang', night: 'Malam' };
                          
                          return (
                            <div key={tod} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', position: 'relative' }}>
                                <button
                                  type="button"
                                  onClick={() => !hasBaseline && handleCaptureBaselineSlot(tod)}
                                  style={{
                                    width: '42px',
                                    height: '42px',
                                    borderRadius: '50%',
                                    border: hasBaseline ? 'none' : '2px dashed rgba(255,255,255,0.25)',
                                    backgroundColor: hasBaseline ? '#10b981' : 'rgba(255,255,255,0.05)',
                                    color: '#fff',
                                    fontWeight: 'bold',
                                    fontSize: '1.1rem',
                                    cursor: hasBaseline ? 'default' : 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'all 0.2s ease',
                                  }}
                                  title={hasBaseline ? `Baseline ${nameMap[tod]} sudah terekam` : `Klik untuk rekam baseline ${nameMap[tod]}`}
                                >
                                  {labelMap[tod]}
                                </button>
                                
                                {hasBaseline && (
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteBaselineSlot(tod)}
                                    style={{
                                      position: 'absolute',
                                      top: '-4px',
                                      right: '-4px',
                                      backgroundColor: '#ef4444',
                                      color: '#fff',
                                      border: 'none',
                                      borderRadius: '50%',
                                      width: '18px',
                                      height: '18px',
                                      fontSize: '11px',
                                      fontWeight: 'bold',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      cursor: 'pointer',
                                      boxShadow: '0 2px 5px rgba(0,0,0,0.3)',
                                      padding: 0,
                                    }}
                                    title={`Hapus baseline ${nameMap[tod]}`}
                                  >
                                    ×
                                  </button>
                                )}
                              </div>
                              <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
                                {nameMap[tod]}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Side: Interactive Zone Editor Canvas */}
                <div className="camera-zone-editor">
                  <div className="zone-editor-header">
                    <h4>Antenna Detection Zones</h4>
                    <button type="button" className="btn-refresh" onClick={refreshCameraSnapshot} title="Refresh snapshot" disabled={loadingSnapshot}>
                      ↻ Refresh Snapshot
                    </button>
                  </div>

                  <div className="canvas-editor-wrapper">
                    {loadingSnapshot && (
                      <div className="canvas-loading-overlay">
                        <div className="spinner"></div>
                        <p>Mengambil snapshot langsung dari RTSP...</p>
                      </div>
                    )}
                    <img 
                      src={snapshotUrl} 
                      alt="CCTV Snapshot" 
                      className="canvas-bg-img"
                    />
                    <canvas
                      ref={canvasRef}
                      className="cctv-canvas"
                      onMouseDown={handleCanvasMouseDown}
                      onMouseMove={handleCanvasMouseMove}
                      onMouseUp={handleCanvasMouseUp}
                    />
                  </div>
                  
                  <div className="zone-editor-controls-bar">
                    <button type="button" className="btn-primary" onClick={handleAddZone} style={{ padding: '8px 14px' }}>
                      ➕ Tambah Zone Antena
                    </button>
                    <button type="button" className="btn-secondary" onClick={handleClearActiveZone} disabled={activeZoneIndex === null} style={{ padding: '8px 14px' }}>
                      🧹 Clear Active Zone Points
                    </button>
                  </div>

                  <div className="drawn-zones-list">
                    <h5>Daftar Zone Antena Tergambar ({zones.length}):</h5>
                    {zones.length === 0 ? (
                      <p className="no-zones-msg">Belum ada zone yang digambar. Klik "+ Tambah Zone Antena" lalu klik pada gambar untuk meletakkan titik koordinat.</p>
                    ) : (
                      <div className="zones-scroll-list">
                        {zones.map((zone, idx) => (
                          <div className={`zone-list-item ${idx === activeZoneIndex ? 'active' : ''}`} key={idx} onClick={() => setActiveZoneIndex(idx)}>
                            <div className="zone-item-main">
                              <span className="zone-color-indicator" style={{ background: idx === activeZoneIndex ? '#22d3ee' : '#ef4444' }}></span>
                              <input
                                type="text"
                                className="zone-name-input"
                                value={zone.name}
                                onChange={(e) => handleZoneNameChange(idx, e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                                placeholder="Nama Antena (e.g. RS1)"
                              />
                              <span className="points-count">({zone.points.length} titik)</span>
                            </div>
                            <button type="button" className="delete-zone-btn" onClick={(e) => { e.stopPropagation(); handleDeleteZone(idx); }}>
                              &times; Hapus
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    <small className="drag-vertex-hint">💡 Tips: Klik pada gambar untuk menambahkan titik (minimal 3, maksimal 5 titik). Pilih zone di atas lalu drag titik vertex untuk memindahkannya.</small>
                  </div>
                </div>

              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsCameraModalOpen(false)}>Batal</button>
                <button type="submit" className="btn-primary">
                  Simpan Konfigurasi & Zone
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
