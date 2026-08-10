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

  // Modal & Form States
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

  // Load registered devices and unregistered beacons
  useEffect(() => {
    fetchDevices();
    fetchUnregistered();
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
        setError(errData.error || errData.detail || 'Gagal menyimpan konfigurasi BLE Device');
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
          <button className="btn-secondary" onClick={() => navigate('/')}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="btn-icon">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Kembali ke Portal
          </button>
          <button className="btn-danger" onClick={handleLogout}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="btn-icon">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
            </svg>
            Sign Out
          </button>
        </div>
      </header>

      <main className="admin-content">
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
                        <span className="beacon-time">
                          Last seen: {new Date(beacon.last_seen).toLocaleTimeString('id-ID')}
                        </span>
                      </div>
                    </div>
                    <button className="btn-register" onClick={() => handleQuickRegister(beacon)}>
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
      </main>

      {/* Add / Edit Form Modal */}
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
    </div>
  );
};

export default AdminDashboard;
