import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';
import './TowerSentinel.css';
import { FaBolt, FaDoorClosed, FaDoorOpen, FaCog, FaCamera, FaSun, FaMoon } from 'react-icons/fa';
import { PiSiren } from 'react-icons/pi';
import CCTVStreamCard from './CCTVStreamCard';

interface AQMSData {
  suhu: number;
  kelembapan: number;
  tekanan: number;
  kecepatan_angin: number;
  arah_angin: number;
  cahaya: number;
  radiasi: number;
  pm25: number;
  pm10: number;
  ion_negatif: number;
}

const TowerSentinel: React.FC = () => {
  const navigate = useNavigate();

  // Canvas and HTML Element Refs
  const towerCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const ringCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const feedRefs = [
    useRef<HTMLCanvasElement | null>(null),
    useRef<HTMLCanvasElement | null>(null),
    useRef<HTMLCanvasElement | null>(null),
    useRef<HTMLCanvasElement | null>(null)
  ];

  const labelNmsRef = useRef<HTMLDivElement | null>(null);
  const labelAqmsRef = useRef<HTMLDivElement | null>(null);
  const labelVertiRef = useRef<HTMLDivElement | null>(null);

  // States
  const [activeModal, setActiveModal] = useState<'nms' | 'aqms' | 'verti' | null>(null);
  const [activeFeed, setActiveFeed] = useState<number>(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [mobileView, setMobileView] = useState<'tower' | 'data' | 'alerts' | 'feeds' | 'settings'>('tower');

  const [aqmsData, setAqmsData] = useState<AQMSData>({
    suhu: 32.1,
    kelembapan: 40.81,
    tekanan: 101.06,
    kecepatan_angin: 1.29,
    arah_angin: 340,
    cahaya: 30994,
    radiasi: 244,
    pm25: 0,
    pm10: 1,
    ion_negatif: 138
  });

  // Reference functions for canvas zoom resets
  const zoomToSystemRef = useRef<((key: 'nms' | 'aqms' | 'verti') => void) | null>(null);
  const resetViewRef = useRef<(() => void) | null>(null);
  const toggleAutoRotateRef = useRef<((val?: boolean) => void) | null>(null);
  const toggleWireframeRef = useRef<(() => void) | null>(null);
  const zoomInRef = useRef<(() => void) | null>(null);
  const zoomOutRef = useRef<(() => void) | null>(null);
  const lastKnownNotifIdRef = useRef<string | null>(null);

  const [isAutoRotate, setIsAutoRotate] = useState<boolean>(true);
  const [isWireframe, setIsWireframe] = useState<boolean>(false);

  // Theme State synced with global NMS theme
  const [theme, setTheme] = useState<string>(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) return savedTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.className = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Notification Center States
  interface UnifiedNotification {
    id: string;
    type: 'camera' | 'pir' | 'door';
    title: string;
    subtitle: string;
    timestamp: string;
    rawTime: string;
    imageUrl?: string;
    status?: string;
  }

  const [notifications, setNotifications] = useState<UnifiedNotification[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'semua' | 'gerakan' | 'sensor'>('semua');
  const [fullscreenPhotoUrl, setFullscreenPhotoUrl] = useState<string | null>(null);
  const [fullscreenPhotoTitle, setFullscreenPhotoTitle] = useState<string>('');

  // NMS Modal State and variables
  const [nmsStatus, setNmsStatus] = useState({
    plnStatus: 'OFF',
    plnTime: '-',
    doorStatus: 'Closed',
    doorTime: '-',
    pirDetected: false,
    pirTime: '-',
    powerVolts: 224.2,
    powerAmps: 7.8
  });

  // Verticality (Structural Health Monitoring) State
  const [vertiStatus, setVertiStatus] = useState({
    pitch: 0.0,
    roll: 0.0,
    totalTilt: 0.0,
    windSpeed: 0.0,
    sway: 0.0,
    indikator: 'tolerance',
    timestamp: '-'
  });


  const [isLampuOn, setIsLampuOn] = useState<boolean>(false);
  const [isLampuLoading, setIsLampuLoading] = useState<boolean>(false);
  const [sirineStatus, setSirineStatus] = useState<string | null>(null);
  const [volume, setVolume] = useState<number>(50);


  // Lampu (Rotary Light) active API handler
  const toggleLampu = async () => {
    if (isLampuLoading) return;
    const nextState = isLampuOn ? 0 : 1;
    try {
      setIsLampuLoading(true);
      await fetch('/api/send-rotary/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: nextState })
      });
      setIsLampuOn(nextState === 1);
    } catch (err) {
      console.error("Failed to toggle rotary light:", err);
    } finally {
      setIsLampuLoading(false);
    }
  };

  // Sirine (Audio Control) active API handler
  const triggerSirine = async (soundName: string) => {
    const isDeactivating = sirineStatus === soundName;
    const nextSirine = isDeactivating ? null : soundName;
    setSirineStatus(nextSirine);

    try {
      if (nextSirine) {
        const soundMap: Record<string, string> = {
          'Suara 1': '1',
          'Suara 2': '2',
          'Suara 3': '3',
          'Polisi': '4',
          'Darurat': '5',
          'Beep': '6'
        };
        const num = soundMap[soundName] || '1';
        await fetch('/api/send/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ command: `SIREN${num}ON`, volume: volume })
        });
      } else {
        await fetch('/api/send/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ command: 'SIREN#OFF' })
        });
      }
    } catch (err) {
      console.error("Failed to trigger siren:", err);
    }
  };

  // Send volume to MQTT
  const sendVolumeToMqtt = async (vol: number) => {
    try {
      await fetch('/api/send/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ volume: vol })
      });
    } catch (err) {
      console.error("Failed to send volume to MQTT:", err);
    }
  };


  // Poll NMS states
  useEffect(() => {
    const fetchNmsStatus = async () => {
      try {
        const plnRes = await fetch('/api/get-pln-status/');
        const plnData = await plnRes.json();
        
        const doorRes = await fetch('/api/get-door-status/');
        const doorData = await doorRes.json();

        const endpoints = [
          '/api/get-motion1-status/',
          '/api/get-motion2-status/',
          '/api/get-motion3-status/',
          '/api/get-motion4-status/'
        ];
        const pirResults = await Promise.all(
          endpoints.map(ep => fetch(ep).then(res => res.ok ? res.json() : { status: 'Standby', last_updated: '-' }))
        );

        const pirDetected = pirResults.some(s => s.status?.toLowerCase() === 'detected');
        const validPirTimes = pirResults.map(s => s.last_updated).filter(t => t && t !== '-');
        const pirTime = validPirTimes.length > 0 ? validPirTimes[0] : '-';

        const plnOn = plnData.status === 'Active' || plnData.status === 'ON';

        setNmsStatus({
          plnStatus: plnData.status || 'OFF',
          plnTime: plnData.last_updated || '-',
          doorStatus: doorData.status || 'Closed',
          doorTime: doorData.last_updated || '-',
          pirDetected,
          pirTime,
          powerVolts: plnOn ? 224.2 : 0,
          powerAmps: plnOn ? 7.8 : 0
        });
      } catch (err) {
        console.error("Error fetching NMS status:", err);
      }
    };

    fetchNmsStatus();
    const interval = setInterval(fetchNmsStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  // Poll Verticality Status
  useEffect(() => {
    const fetchVertiStatus = async () => {
      try {
        const res = await fetch('/api/verticality/sensor-data/latest/?device_id=E32_VER_WS');
        if (res.ok) {
          const data = await res.json();
          if (data) {
            setVertiStatus({
              pitch: data.pitch || 0.0,
              roll: data.roll || 0.0,
              totalTilt: data.total_tilt || 0.0,
              windSpeed: data.wind_speed || 0.0,
              sway: data.sway || 0.0,
              indikator: data.indikator || 'tolerance',
              timestamp: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : '-'
            });
          }
        }
      } catch (err) {
        console.error("Error fetching Verticality status:", err);
      }
    };

    fetchVertiStatus();
    const interval = setInterval(fetchVertiStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll AQMS Status
  useEffect(() => {
    const fetchAqmsStatus = async () => {
      try {
        const res = await fetch('/api/sensor-readings/latest/');
        if (res.ok) {
          const data = await res.json();
          if (data) {
            setAqmsData({
              suhu: data.temperature || 32.1,
              kelembapan: data.humidity || 40.81,
              tekanan: data.pressure || 101.06,
              kecepatan_angin: data.wind_speed || 1.29,
              arah_angin: data.wind_direction || 340,
              cahaya: data.light || 30994,
              radiasi: data.radiation || 244,
              pm25: data.pm25 || 0,
              pm10: data.pm10 || 1,
              ion_negatif: data.negative_ion || 138
            });
          }
        }
      } catch (err) {
        console.error("Error fetching AQMS status:", err);
      }
    };

    fetchAqmsStatus();
    const interval = setInterval(fetchAqmsStatus, 5000);
    return () => clearInterval(interval);
  }, []);


  // Poll Notifications
  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        // 1. Fetch CCTV/PIR alerts
        const cctvRes = await fetch('/api/cctv/alerts/?category=all');
        const cctvData = cctvRes.ok ? await cctvRes.json() : [];

        // 2. Fetch Door logs
        const doorRes = await fetch('/api/door-logs/?page=1&limit=10');
        const doorJson = doorRes.ok ? await doorRes.json() : { logs: [] };
        const doorData = doorJson.logs || [];

        // 3. Map CCTV/PIR alerts
        const cctvMapped = cctvData.map((item: any) => ({
          id: item.id,
          type: item.type as 'camera' | 'pir',
          title: item.title || (item.type === 'camera' ? `Orang terdeteksi` : `Gerakan terdeteksi`),
          subtitle: `NAYAKA WS (PRR-01-004) &middot; ${item.camera}`,
          timestamp: item.timestamp,
          rawTime: item.raw_time,
          imageUrl: item.url
        }));

        // 4. Map Door logs
        const doorMapped = doorData.map((item: any) => ({
          id: `door_${item.id}`,
          type: 'door' as 'door',
          title: item.status === 'OPEN' ? 'Pintu Terbuka' : 'Pintu Tertutup',
          subtitle: `NAYAKA WS (PRR-01-004) &middot; Access Control`,
          timestamp: item.timestamp,
          rawTime: item.raw_time || new Date().toISOString(),
          imageUrl: undefined,
          status: item.status
        }));

        // 5. Combine and Sort
        const combined = [...cctvMapped, ...doorMapped];
        combined.sort((a, b) => new Date(b.rawTime).getTime() - new Date(a.rawTime).getTime());

        // Play notification sound if a new notification arrives
        if (combined.length > 0) {
          const latestNotifId = combined[0].id;
          if (lastKnownNotifIdRef.current !== null && lastKnownNotifIdRef.current !== latestNotifId) {
            try {
              const audio = new Audio('/notification.wav');
              audio.volume = 0.7;
              audio.play().catch(err => {
                console.log("Audio autoplay waiting for user interaction:", err);
              });
            } catch (soundErr) {
              console.error("Error playing notification sound:", soundErr);
            }
          }
          lastKnownNotifIdRef.current = latestNotifId;
        }

        setNotifications(combined);
      } catch (err) {
        console.error("Failed to fetch notifications:", err);
      }
    };

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 5000);
    return () => clearInterval(interval);
  }, []);

  // Filtered Notifications based on tab and search query
  const filteredNotifications = notifications.filter(item => {
    if (activeTab === 'gerakan' && item.type === 'door') return false;
    if (activeTab === 'sensor' && item.type !== 'door') return false;

    if (searchQuery.trim() === '') return true;
    const query = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(query) ||
      item.subtitle.toLowerCase().includes(query) ||
      item.timestamp.toLowerCase().includes(query)
    );
  });

  // --- Draw Ring Chart (Tower Status) ---
  useEffect(() => {
    const canvas = ringCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cx = 55, cy = 55, r = 46, lw = 10;
    const segments = [
      { value: 89 / 112, color: '#22c55e' },
      { value: 16 / 112, color: '#f59e0b' },
      { value: 7 / 112, color: '#ef4444' }
    ];
    const start = -Math.PI / 2;
    let current = start;

    ctx.clearRect(0, 0, 110, 110);

    // Track background
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = lw;
    ctx.stroke();

    // Colored segments
    segments.forEach(seg => {
      const end = current + seg.value * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, current, end);
      ctx.strokeStyle = seg.color;
      ctx.lineWidth = lw;
      ctx.lineCap = 'round';
      ctx.stroke();
      current = end + 0.04;
    });
  }, []);

  // --- Fake Live Feeds (2D Canvas Animation) ---
  useEffect(() => {
    let animationId: number;
    let feedT = 0;

    const feedColors = [
      ['#1a2a1a', '#2a4020', '#1e3015'],
      ['#1a1a2a', '#20203a', '#15152a'],
      ['#2a2020', '#3a2525', '#2a1818'],
      ['#1a2020', '#203030', '#152a2a'],
    ];

    const feedTowers = [
      { x: 130, y: 20, scale: 0.70 },
      { x: 120, y: 18, scale: 0.65 },
      { x: 140, y: 22, scale: 0.75 },
      { x: 125, y: 19, scale: 0.68 },
    ];

    const drawFeedFrame = (canvas: HTMLCanvasElement, idx: number, t: number) => {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const W = canvas.width, H = canvas.height;
      const cols = feedColors[idx];

      // Background sky/ground gradient
      const grad = ctx.createLinearGradient(0, 0, 0, H);
      grad.addColorStop(0, '#0a0e18');
      grad.addColorStop(0.5, cols[0]);
      grad.addColorStop(1, cols[2]);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // Animated noise/grain
      const imageData = ctx.getImageData(0, 0, W, H);
      const data = imageData.data;
      for (let i = 0; i < data.length; i += 4) {
        const noise = (Math.random() - 0.5) * 18;
        data[i] += noise;
        data[i + 1] += noise;
        data[i + 2] += noise;
      }
      ctx.putImageData(imageData, 0, 0);

      // Trees / foliage silhouette
      ctx.fillStyle = '#0d1a0d';
      for (let x = 0; x < W; x += 14) {
        const h = 25 + Math.sin(x * 0.15 + t * 0.3) * 8 + Math.random() * 5;
        ctx.beginPath();
        ctx.moveTo(x, H);
        ctx.lineTo(x + 7, H - h);
        ctx.lineTo(x + 14, H);
        ctx.fill();
      }

      // Simple tower silhouette
      const tw = feedTowers[idx];
      const tx = tw.x, ty = tw.y, sc = tw.scale;
      const tH = H * 0.75 * sc;
      const tW = 8 * sc;

      // Main mast
      ctx.fillStyle = '#888';
      ctx.fillRect(tx - tW / 2, ty, tW, tH);

      // Crossbars
      for (let i = 0; i < 6; i++) {
        const y = ty + (tH / 6) * i;
        const w = tW * (1 + (6 - i) * 0.3);
        ctx.fillStyle = '#777';
        ctx.fillRect(tx - w / 2, y, w, 2 * sc);
      }

      // Antenna top
      ctx.fillStyle = '#aaa';
      ctx.fillRect(tx - 1, ty - 15 * sc, 2, 15 * sc);

      // Dishes
      ctx.strokeStyle = '#999';
      ctx.lineWidth = 1.5 * sc;
      ctx.beginPath();
      ctx.arc(tx + 6 * sc, ty + tH * 0.35, 8 * sc, 0, Math.PI, true);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(tx - 6 * sc, ty + tH * 0.55, 7 * sc, 0, Math.PI, false);
      ctx.stroke();

      // Scanline overlay
      ctx.fillStyle = 'rgba(0,0,0,0.15)';
      for (let y = 0; y < H; y += 3) {
        ctx.fillRect(0, y, W, 1);
      }

      // Timestamp
      ctx.fillStyle = 'rgba(255,255,255,0.5)';
      ctx.font = '10px monospace';
      const now = new Date();
      ctx.fillText(now.toTimeString().slice(0, 8), W - 58, H - 8);
    };

    const animateFeeds = () => {
      feedT += 0.05;
      feedRefs.forEach((ref, idx) => {
        const canvas = ref.current;
        if (canvas) {
          drawFeedFrame(canvas, idx, feedT);
        }
      });
      animationId = requestAnimationFrame(animateFeeds);
    };

    animateFeeds();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, []);

  // --- Three.js 3D Tower Visualization ---
  useEffect(() => {
    const canvas = towerCanvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0d1020, 0.010);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 300);
    camera.position.set(0, 12, 38);
    camera.lookAt(0, 11, 0);

    // Resize handling
    const resize = () => {
      if (!canvas.parentElement) return;
      const w = canvas.parentElement.clientWidth;
      const h = canvas.parentElement.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    window.addEventListener('resize', resize);

    // --- Lights ---
    scene.add(new THREE.AmbientLight(0x4060a0, 2.5));

    const dirLight = new THREE.DirectionalLight(0xffffff, 4.5);
    dirLight.position.set(10, 30, 10);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.set(2048, 2048);
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 150;
    dirLight.shadow.camera.top = dirLight.shadow.camera.right = 40;
    dirLight.shadow.camera.bottom = dirLight.shadow.camera.left = -40;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x8ab4f8, 2.0);
    fillLight.position.set(-8, 20, 15);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x22d3ee, 1.5);
    rimLight.position.set(0, 25, -20);
    scene.add(rimLight);

    const bluePoint = new THREE.PointLight(0x3b82f6, 5, 50);
    bluePoint.position.set(-5, 5, 5);
    scene.add(bluePoint);

    const cyanPoint = new THREE.PointLight(0x22d3ee, 4, 40);
    cyanPoint.position.set(5, 15, -5);
    scene.add(cyanPoint);

    const groundLight = new THREE.PointLight(0x3b82f6, 3, 25);
    groundLight.position.set(0, 0.5, 0);
    scene.add(groundLight);

    // --- Materials ---
    const metalRed = new THREE.MeshStandardMaterial({ color: 0xcc2222, metalness: 0.85, roughness: 0.25 });
    const metalGray = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.90, roughness: 0.20 });
    const metalDark = new THREE.MeshStandardMaterial({ color: 0x444444, metalness: 0.70, roughness: 0.30 });
    const metalWhite = new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.60, roughness: 0.35 });
    const concreteMat = new THREE.MeshStandardMaterial({ color: 0x555566, metalness: 0.10, roughness: 0.80 });

    const towerGroup = new THREE.Group();
    scene.add(towerGroup);

    // --- Build Tower Geometry ---
    const SECTIONS = 10;
    const TOWER_HEIGHT = 22;
    const getCornerRadius = (t: number) => 3.0 - t * 2.6; // 3.0 -> 0.4

    // 4 vertical tapered poles
    const verticalPoles: THREE.Vector3[][] = [];
    for (let c = 0; c < 4; c++) {
      const angle = (c / 4) * Math.PI * 2 + Math.PI / 4;
      const path: THREE.Vector3[] = [];
      for (let s = 0; s <= SECTIONS; s++) {
        const t = s / SECTIONS;
        const r = getCornerRadius(t);
        path.push(new THREE.Vector3(Math.cos(angle) * r, t * TOWER_HEIGHT, Math.sin(angle) * r));
      }
      verticalPoles.push(path);
    }

    // Draw alternating red/gray vertical segments
    for (let c = 0; c < 4; c++) {
      const path = verticalPoles[c];
      for (let s = 0; s < SECTIONS; s++) {
        const mat = (s % 2 === 0) ? metalRed : metalGray;
        const p1 = path[s], p2 = path[s + 1];
        const len = p1.distanceTo(p2);
        const geo = new THREE.CylinderGeometry(0.1, 0.12, len, 8);
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.copy(p1).lerp(p2, 0.5);
        mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p2.clone().sub(p1).normalize());
        mesh.castShadow = true;
        towerGroup.add(mesh);
      }
    }

    // Horizontal ring bars
    for (let s = 0; s <= SECTIONS; s++) {
      const t = s / SECTIONS;
      const y = t * TOWER_HEIGHT;
      const r = getCornerRadius(t);
      for (let c = 0; c < 4; c++) {
        const nc = (c + 1) % 4;
        const a1 = (c / 4) * Math.PI * 2 + Math.PI / 4;
        const a2 = (nc / 4) * Math.PI * 2 + Math.PI / 4;
        const x1 = Math.cos(a1) * r, z1 = Math.sin(a1) * r;
        const x2 = Math.cos(a2) * r, z2 = Math.sin(a2) * r;
        const len = Math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2);
        const geo = new THREE.CylinderGeometry(0.07, 0.07, len, 6);
        const mesh = new THREE.Mesh(geo, metalGray);
        mesh.position.set((x1 + x2) / 2, y, (z1 + z2) / 2);
        mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(x2 - x1, 0, z2 - z1).normalize());
        mesh.castShadow = true;
        towerGroup.add(mesh);
      }
    }

    // Diagonal X-braces
    for (let s = 0; s < SECTIONS; s++) {
      const t1 = s / SECTIONS, t2 = (s + 1) / SECTIONS;
      const y1 = t1 * TOWER_HEIGHT, y2 = t2 * TOWER_HEIGHT;
      const r1 = getCornerRadius(t1), r2 = getCornerRadius(t2);
      for (let c = 0; c < 4; c++) {
        const nc = (c + 1) % 4;
        const a1 = (c / 4) * Math.PI * 2 + Math.PI / 4;
        const a2 = (nc / 4) * Math.PI * 2 + Math.PI / 4;

        // Brace 1
        const p1 = new THREE.Vector3(Math.cos(a1) * r1, y1, Math.sin(a1) * r1);
        const p2 = new THREE.Vector3(Math.cos(a2) * r2, y2, Math.sin(a2) * r2);
        const geo1 = new THREE.CylinderGeometry(0.05, 0.05, p1.distanceTo(p2), 5);
        const m1 = new THREE.Mesh(geo1, metalDark);
        m1.position.copy(p1).lerp(p2, 0.5);
        m1.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p2.clone().sub(p1).normalize());
        m1.castShadow = true;
        towerGroup.add(m1);

        // Brace 2 (cross)
        const p3 = new THREE.Vector3(Math.cos(a2) * r1, y1, Math.sin(a2) * r1);
        const p4 = new THREE.Vector3(Math.cos(a1) * r2, y2, Math.sin(a1) * r2);
        const geo2 = new THREE.CylinderGeometry(0.05, 0.05, p3.distanceTo(p4), 5);
        const m2 = new THREE.Mesh(geo2, metalDark);
        m2.position.copy(p3).lerp(p4, 0.5);
        m2.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p4.clone().sub(p3).normalize());
        m2.castShadow = true;
        towerGroup.add(m2);
      }
    }

    // Antenna mast
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.1, 3.5, 8), metalGray);
    mast.position.set(0, TOWER_HEIGHT + 1.25, 0);
    mast.castShadow = true;
    towerGroup.add(mast);

    // Cone tip
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.8, 8), metalRed);
    tip.position.set(0, TOWER_HEIGHT + 3.4, 0);
    tip.castShadow = true;
    towerGroup.add(tip);

    // Microwave dishes
    const addDish = (px: number, py: number, pz: number, rotY: number, scale = 1) => {
      const dGroup = new THREE.Group();
      dGroup.position.set(px, py, pz);
      dGroup.rotation.y = rotY;

      const dish = new THREE.Mesh(
        new THREE.SphereGeometry(0.8 * scale, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2),
        metalWhite
      );
      dish.rotation.x = Math.PI / 2;
      dish.castShadow = true;
      dGroup.add(dish);

      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.8 * scale, 6), metalGray);
      arm.rotation.z = Math.PI / 2;
      arm.position.x = -0.5 * scale;
      dGroup.add(arm);

      towerGroup.add(dGroup);
    };

    addDish(1.5, 14, 0, 0, 1);
    addDish(-1.5, 10, 0, Math.PI, 0.8);
    addDish(0, 7, 1.5, -Math.PI / 2, 1.1);
    addDish(0, 18, -1, Math.PI / 3, 0.7);

    // Panel antennas
    const addPanel = (px: number, py: number, pz: number, rotY: number) => {
      const panel = new THREE.Mesh(new THREE.BoxGeometry(0.15, 2, 0.5), metalDark);
      panel.position.set(px, py, pz);
      panel.rotation.y = rotY;
      panel.castShadow = true;
      towerGroup.add(panel);
    };
    addPanel(0.5, 20, 0.3, 0);
    addPanel(-0.5, 20, 0.3, 0);
    addPanel(0.3, 20, -0.4, Math.PI / 3);
    addPanel(-0.3, 20, -0.4, -Math.PI / 3);
    addPanel(0.3, 17, 0.4, Math.PI / 6);
    addPanel(-0.3, 17, 0.4, -Math.PI / 6);

    // Shelter base
    const shelter = new THREE.Mesh(new THREE.BoxGeometry(3.5, 1.8, 2.8), concreteMat);
    shelter.position.set(0, 0.9, -1.5);
    shelter.castShadow = shelter.receiveShadow = true;
    towerGroup.add(shelter);

    const door = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.4, 0.05), metalDark);
    door.position.set(0, 0.7, -2.88);
    towerGroup.add(door);

    const ac = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.4, 0.3), metalGray);
    ac.position.set(1, 1.9, -1.5);
    towerGroup.add(ac);

    // Foundation
    const base = new THREE.Mesh(new THREE.CylinderGeometry(4.5, 5, 0.4, 32), concreteMat);
    base.position.y = -0.25;
    base.receiveShadow = true;
    towerGroup.add(base);

    // Ground plane
    const groundMeshMat = new THREE.MeshStandardMaterial({
      color: 0x050a05, roughness: 1, metalness: 0.0,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1
    });
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(25, 48),
      groundMeshMat
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.01;
    ground.receiveShadow = true;
    scene.add(ground);

    // Fence (Pagar memutari tower dan shelter)
    const fenceGroup = new THREE.Group();
    const postMat = metalGray;
    const railMat = metalGray;
    const meshMat = metalDark;
    const xMin = -4.5, xMax = 4.5;
    const zMin = -6.0, zMax = 3.0;
    const fenceHeight = 1.6;

    // Corner posts
    const corners = [
      { x: xMin, z: zMin },
      { x: xMax, z: zMin },
      { x: xMax, z: zMax },
      { x: xMin, z: zMax }
    ];
    corners.forEach(c => {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, fenceHeight, 8), postMat);
      post.position.set(c.x, fenceHeight / 2, c.z);
      post.castShadow = true;
      fenceGroup.add(post);
    });

    // Fence line segments (Intermediate posts, top/bottom rails, vertical wire grids)
    const addFenceLine = (x1: number, z1: number, x2: number, z2: number) => {
      const dx = x2 - x1;
      const dz = z2 - z1;
      const length = Math.sqrt(dx * dx + dz * dz);
      const angle = Math.atan2(dz, dx);

      // Intermediate posts
      const numInter = Math.floor(length / 2.0);
      for (let i = 1; i <= numInter; i++) {
        const t = i / (numInter + 1);
        const px = x1 + dx * t;
        const pz = z1 + dz * t;
        // Skip gate entrance at the front (x = -0.8 to 0.8 at zMax)
        if (Math.abs(z1 - zMax) < 0.1 && Math.abs(z2 - zMax) < 0.1 && Math.abs(px) < 0.8) continue;

        const post = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, fenceHeight, 8), postMat);
        post.position.set(px, fenceHeight / 2, pz);
        post.castShadow = true;
        fenceGroup.add(post);
      }

      // Rails
      const makeRail = (y: number) => {
        const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, length, 6), railMat);
        rail.position.set((x1 + x2) / 2, y, (z1 + z2) / 2);
        rail.rotation.y = -angle;
        rail.rotation.z = Math.PI / 2;
        rail.castShadow = true;
        fenceGroup.add(rail);
      };
      makeRail(fenceHeight - 0.1);
      makeRail(0.15);

      // Vertical wire lines
      const numWires = Math.floor(length / 0.35);
      for (let i = 1; i < numWires; i++) {
        const t = i / numWires;
        const px = x1 + dx * t;
        const pz = z1 + dz * t;
        // Skip gate
        if (Math.abs(z1 - zMax) < 0.1 && Math.abs(z2 - zMax) < 0.1 && Math.abs(px) < 0.8) continue;

        const wire = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, fenceHeight - 0.25, 4), meshMat);
        wire.position.set(px, fenceHeight / 2, pz);
        fenceGroup.add(wire);
      }
    };

    addFenceLine(xMin, zMax, xMax, zMax); // Front
    addFenceLine(xMin, zMin, xMax, zMin); // Back
    addFenceLine(xMin, zMin, xMin, zMax); // Left
    addFenceLine(xMax, zMin, xMax, zMax); // Right
    towerGroup.add(fenceGroup);

    // Warning light
    const warnGeo = new THREE.SphereGeometry(0.18, 8, 8);
    const warnMat = new THREE.MeshStandardMaterial({ color: 0xff4444, emissive: 0xff2200, emissiveIntensity: 2 });
    const warnLight = new THREE.Mesh(warnGeo, warnMat);
    warnLight.position.set(0, TOWER_HEIGHT + 3.9, 0);
    towerGroup.add(warnLight);

    const warnPointLight = new THREE.PointLight(0xff3300, 3, 8);
    warnPointLight.position.copy(warnLight.position);
    towerGroup.add(warnPointLight);

    // Stars background
    const starCount = 800;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPos[i] = (Math.random() - 0.5) * 200;
      starPos[i + 1] = Math.abs((Math.random() - 0.1)) * 100 + 5;
      starPos[i + 2] = (Math.random() - 0.5) * 200;
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.15, transparent: true, opacity: 0.7 })));

    // --- Modules (NMS, AQMS, Verticality) ---
    const nmsBoxMat = new THREE.MeshStandardMaterial({ color: 0x1a3a6e, metalness: 0.7, roughness: 0.3 });
    const aqmsMat = new THREE.MeshStandardMaterial({ color: 0x0e4a3a, metalness: 0.6, roughness: 0.35 });
    const vertiMat = new THREE.MeshStandardMaterial({ color: 0x4a1a6e, metalness: 0.7, roughness: 0.3 });
    const legMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.9, roughness: 0.2 });
    const sensorMat = new THREE.MeshStandardMaterial({ color: 0xdddddd, metalness: 0.5, roughness: 0.4 });
    const cctvBodyMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.8, roughness: 0.25 });
    const lensMat = new THREE.MeshStandardMaterial({ color: 0x88ccff, metalness: 0.3, roughness: 0.1, emissive: 0x224466, emissiveIntensity: 0.5 });

    // NMS Panel box
    const nmsGroup = new THREE.Group();
    towerGroup.add(nmsGroup);

    const nmsPanelMesh = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.0, 0.6), nmsBoxMat);
    nmsPanelMesh.position.set(2.5, 7.0, 0);
    nmsPanelMesh.castShadow = true;
    nmsGroup.add(nmsPanelMesh);

    const nmsScreenMat = new THREE.MeshStandardMaterial({ color: 0x0055ff, emissive: 0x0033cc, emissiveIntensity: 1.5, metalness: 0.1, roughness: 0.9 });
    const nmsScreen = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.65, 0.05), nmsScreenMat);
    nmsScreen.position.set(2.5, 7.05, 0.33);
    nmsGroup.add(nmsScreen);

    [-0.5, 0.5].forEach(ox => {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.5, 6), legMat);
      leg.position.set(2.5 + ox, 6.25, 0);
      nmsGroup.add(leg);
    });

    const makeCCTV = (px: number, py: number, pz: number, rotY: number) => {
      const g = new THREE.Group();
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.18, 0.45), cctvBodyMat);
      body.castShadow = true; g.add(body);
      const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.09, 0.14, 10), lensMat);
      lens.rotation.x = Math.PI / 2;
      lens.position.z = 0.27; g.add(lens);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.35, 0.07), legMat);
      arm.position.y = 0.24; g.add(arm);
      const plate = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.06, 0.22), legMat);
      plate.position.y = 0.43; g.add(plate);
      g.position.set(px, py, pz);
      g.rotation.y = rotY;
      towerGroup.add(g);
      return g;
    };
    makeCCTV(1.6, 8.5, 1.2, 0.5);
    makeCCTV(-1.6, 8.5, -1.2, -2.2);

    // AQMS Anemometer/Weather Module
    const aqmsGroup = new THREE.Group();
    towerGroup.add(aqmsGroup);

    const makeWeatherSensor = (px: number, py: number, pz: number, rotY: number) => {
      const g = new THREE.Group();
      const housing = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.7, 10), aqmsMat);
      housing.castShadow = true; g.add(housing);

      const cap = new THREE.Mesh(new THREE.SphereGeometry(0.18, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), sensorMat);
      cap.position.y = 0.35; g.add(cap);

      const spinGroup = new THREE.Group();
      spinGroup.position.y = 0.55;
      g.add(spinGroup);

      const cupMat = new THREE.MeshStandardMaterial({ color: 0xeeeeee, metalness: 0.3, roughness: 0.5 });
      for (let i = 0; i < 3; i++) {
        const angle = (i / 3) * Math.PI * 2;
        const arm2 = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.28, 5), sensorMat);
        arm2.rotation.z = Math.PI / 2;
        arm2.position.set(Math.cos(angle) * 0.14, 0, Math.sin(angle) * 0.14);
        arm2.rotation.y = angle;
        spinGroup.add(arm2);

        const cup = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6, 0, Math.PI * 2, 0, Math.PI / 2), cupMat);
        cup.rotation.x = Math.PI / 2;
        cup.position.set(Math.cos(angle) * 0.28, 0, Math.sin(angle) * 0.28);
        spinGroup.add(cup);
      }
      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.35, 6), sensorMat);
      shaft.position.y = 0.72; g.add(shaft);

      const mountArm = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.8, 6), legMat);
      mountArm.rotation.z = Math.PI / 2;
      mountArm.position.x = -0.4; g.add(mountArm);

      const pmBox = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.35, 0.18), aqmsMat);
      pmBox.position.set(0, -0.2, 0.22); g.add(pmBox);
      const pmLed = new THREE.MeshStandardMaterial({ color: 0x00ff88, emissive: 0x00ff88, emissiveIntensity: 2 });
      const led = new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 6), pmLed);
      led.position.set(0.1, -0.1, 0.32); g.add(led);

      g.position.set(px, py, pz);
      g.rotation.y = rotY;
      towerGroup.add(g);
      return { group: g, spin: spinGroup };
    };
    const aqmsSensor1 = makeWeatherSensor(2.0, 11.5, 0.5, 0);
    const aqmsSensor2 = makeWeatherSensor(-1.8, 10.2, -0.5, Math.PI);

    // Verticality Module
    const vertiGroup = new THREE.Group();
    towerGroup.add(vertiGroup);

    const vertiBox = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.4, 0.55), vertiMat);
    vertiBox.castShadow = true;
    vertiGroup.add(vertiBox);

    const vertiLedMat = new THREE.MeshStandardMaterial({ color: 0xcc44ff, emissive: 0xaa22ee, emissiveIntensity: 2 });
    const vertiLed = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 8), vertiLedMat);
    vertiLed.position.set(0, 0.23, 0.2);
    vertiGroup.add(vertiLed);

    const probe = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.5, 8), sensorMat);
    probe.position.y = 0.45;
    vertiGroup.add(probe);

    const bracket = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.5, 0.08), legMat);
    bracket.position.set(-0.35, 0, 0);
    vertiGroup.add(bracket);
    vertiGroup.position.set(0.6, 19.0, 0.6);

    // Wind vane
    const vaneGroup = new THREE.Group();
    const vaneMat = new THREE.MeshStandardMaterial({ color: 0xffcc00, emissive: 0xffaa00, emissiveIntensity: 0.8, metalness: 0.5, roughness: 0.3 });
    const arrowHead = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.45, 6), vaneMat);
    arrowHead.rotation.z = -Math.PI / 2;
    arrowHead.position.x = 0.32;
    vaneGroup.add(arrowHead);

    const arrowTail = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 0.5), vaneMat);
    arrowTail.position.x = -0.25;
    vaneGroup.add(arrowTail);

    const vaneShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.7, 8), legMat);
    vaneGroup.add(vaneShaft);

    const vaneMountArm = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.8, 6), legMat);
    vaneMountArm.rotation.z = Math.PI / 2;
    vaneMountArm.position.x = -0.6;
    vaneGroup.add(vaneMountArm);
    vaneGroup.position.set(-2.0, 13.2, -0.5);
    towerGroup.add(vaneGroup);

    // Vane direction angles
    let aqmsSpinSpeed1 = 0.05;
    let aqmsSpinSpeed2 = 0.04;
    let targetVaneAngle = -340 * Math.PI / 180;
    let currentVaneAngle = targetVaneAngle;

    // --- Hotspots setup ---
    const makeHotspot = (color: number, wx3d: number, wy3d: number, wz3d: number) => {
      const mat = new THREE.MeshStandardMaterial({
        color, emissive: color, emissiveIntensity: 2.5,
        transparent: true, opacity: 0.9
      });
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 12), mat);
      sphere.position.set(wx3d, wy3d, wz3d);
      towerGroup.add(sphere);

      const ringMat = new THREE.MeshStandardMaterial({
        color, emissive: color, emissiveIntensity: 1,
        transparent: true, opacity: 0.35, wireframe: true
      });
      const ring = new THREE.Mesh(new THREE.SphereGeometry(0.44, 10, 10), ringMat);
      ring.position.set(wx3d, wy3d, wz3d);
      towerGroup.add(ring);

      return { sphere, ring, mat, ringMat };
    };

    const hotspotNMS = makeHotspot(0xf59e0b, 3.5, 7.0, 0);
    const hotspotAQMS = makeHotspot(0x22d3ee, 2.0, 11.5, 0.5);
    const hotspotVerti = makeHotspot(0xc084fc, 0.6, 19.0, 0.6);

    const allHotspots = [
      { key: 'nms' as const, hs: hotspotNMS, lookAtY: 7, dist: 14, rotX: 0.06, rotY: 0.6, labelRef: labelNmsRef },
      { key: 'aqms' as const, hs: hotspotAQMS, lookAtY: 11.5, dist: 14, rotX: 0.08, rotY: 0.4, labelRef: labelAqmsRef },
      { key: 'verti' as const, hs: hotspotVerti, lookAtY: 19, dist: 12, rotX: 0.05, rotY: -0.3, labelRef: labelVertiRef },
    ];

    // Raycaster for clicking hotspots
    const raycaster = new THREE.Raycaster();
    const mouse2D = new THREE.Vector2();
    const hotspotMeshes = allHotspots.map(h => h.hs.sphere);

    const handleCanvasClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse2D.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse2D.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse2D, camera);
      const hits = raycaster.intersectObjects(hotspotMeshes);
      if (hits.length > 0) {
        const hit = hits[0].object;
        const info = allHotspots.find(h => h.hs.sphere === hit);
        if (info) {
          setActiveModal(info.key);
          zoomToSystem(info.key);
        }
      }
    };
    canvas.addEventListener('click', handleCanvasClick);

    // --- Orbit and camera views ---
    let currentLookAtY = 11, targetLookAtY = 11;
    let rotX = 0.12, rotY = 0, targetRotX = 0.12, targetRotY = 0;
    let autoRotate = true;
    let camDist = 38, targetDist = 38;
    let isDragging = false, lastX = 0, lastY = 0;

    const zoomToSystem = (key: 'nms' | 'aqms' | 'verti') => {
      const info = allHotspots.find(h => h.key === key);
      if (!info) return;
      autoRotate = false;
      setIsAutoRotate(false);
      targetRotX = info.rotX;
      targetRotY = info.rotY;
      targetDist = info.dist;
      targetLookAtY = info.lookAtY;

      // Remove active classes
      document.querySelectorAll('.system-label').forEach(el => el.classList.remove('active'));
      const lbl = info.labelRef.current;
      if (lbl) lbl.classList.add('active');
    };
    zoomToSystemRef.current = zoomToSystem;

    const resetView = () => {
      targetRotX = 0.12;
      targetRotY = 0;
      targetDist = 38;
      autoRotate = true;
      setIsAutoRotate(true);
      targetLookAtY = 11;
      document.querySelectorAll('.system-label').forEach(el => el.classList.remove('active'));
    };
    resetViewRef.current = resetView;

    toggleAutoRotateRef.current = (val?: boolean) => {
      const nextVal = val !== undefined ? val : !autoRotate;
      autoRotate = nextVal;
      setIsAutoRotate(nextVal);
    };

    toggleWireframeRef.current = () => {
      setIsWireframe(prev => {
        const next = !prev;
        towerGroup.traverse(obj => {
          if ((obj as THREE.Mesh).isMesh) {
            const mesh = obj as THREE.Mesh;
            if (Array.isArray(mesh.material)) {
              mesh.material.forEach(m => m.wireframe = next);
            } else if (mesh.material) {
              mesh.material.wireframe = next;
            }
          }
        });
        return next;
      });
    };

    zoomInRef.current = () => {
      targetDist = Math.max(8, targetDist - 4);
    };

    zoomOutRef.current = () => {
      targetDist = Math.min(50, targetDist + 4);
    };

    // Orbit drag listeners
    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      autoRotate = false;
      setIsAutoRotate(false);
    };
    const handleMouseUp = () => {
      isDragging = false;
    };
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      targetRotY += (e.clientX - lastX) * 0.008;
      targetRotX = Math.max(-0.5, Math.min(1.0, targetRotX + (e.clientY - lastY) * 0.005));
      lastX = e.clientX;
      lastY = e.clientY;
    };

    canvas.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('mousemove', handleMouseMove);

    // Touch orbit
    let lastTX = 0, lastTY = 0;
    const handleTouchStart = (e: TouchEvent) => {
      isDragging = true;
      lastTX = e.touches[0].clientX;
      lastTY = e.touches[0].clientY;
      autoRotate = false;
      setIsAutoRotate(false);
    };
    const handleTouchEnd = () => {
      isDragging = false;
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (!isDragging) return;
      targetRotY += (e.touches[0].clientX - lastTX) * 0.008;
      targetRotX = Math.max(-0.5, Math.min(1.0, targetRotX + (e.touches[0].clientY - lastTY) * 0.005));
      lastTX = e.touches[0].clientX;
      lastTY = e.touches[0].clientY;
    };

    canvas.addEventListener('touchstart', handleTouchStart, { passive: true });
    canvas.addEventListener('touchend', handleTouchEnd, { passive: true });
    canvas.addEventListener('touchmove', handleTouchMove, { passive: true });

    // Wheel zoom
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      targetDist = Math.max(10, Math.min(70, targetDist + e.deltaY * 0.05));
    };
    canvas.addEventListener('wheel', handleWheel, { passive: false });

    // --- Main Animation Loop ---
    let t = 0;
    let animationId: number;

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      t += 0.016;

      if (autoRotate) targetRotY += 0.006;

      // Interpolation
      rotX += (targetRotX - rotX) * 0.06;
      rotY += (targetRotY - rotY) * 0.06;
      camDist += (targetDist - camDist) * 0.06;
      currentLookAtY += (targetLookAtY - currentLookAtY) * 0.07;

      camera.position.set(
        camDist * Math.sin(rotY) * Math.cos(rotX),
        camDist * Math.sin(rotX) + currentLookAtY,
        camDist * Math.cos(rotY) * Math.cos(rotX)
      );
      camera.lookAt(0, currentLookAtY, 0);

      // Warning light blinking
      const blink = Math.sin(t * 2.5) > 0;
      warnMat.emissiveIntensity = blink ? 3 : 0.1;
      warnPointLight.intensity = blink ? 5 : 0;

      // Pulse ground glow
      groundLight.intensity = 3 + Math.sin(t * 0.8) * 1.2;

      // Rotate anemometers
      aqmsSensor1.spin.rotation.y += aqmsSpinSpeed1;
      aqmsSensor2.spin.rotation.y -= aqmsSpinSpeed2;

      // Wind vane rotation
      currentVaneAngle += (targetVaneAngle - currentVaneAngle) * 0.03;
      vaneGroup.rotation.y = currentVaneAngle;

      // Pulse hotspots
      allHotspots.forEach((h, i) => {
        const phase = t * 3 + i * 1.2;
        const p = 0.8 + Math.sin(phase) * 0.2;
        h.hs.ring.scale.setScalar(p);
        h.hs.ringMat.opacity = 0.25 + Math.sin(phase) * 0.15;
      });

      // Project label locations (3D -> 2D)
      const rect = canvas.getBoundingClientRect();
      allHotspots.forEach(h => {
        const lbl = h.labelRef.current;
        if (!lbl) return;

        const worldPos = new THREE.Vector3();
        h.hs.sphere.getWorldPosition(worldPos);
        const proj = worldPos.clone().project(camera);

        const px = ((proj.x + 1) / 2) * rect.width;
        const py = ((-proj.y + 1) / 2) * rect.height;

        if (proj.z > 1) {
          lbl.style.opacity = '0';
          return;
        }
        lbl.style.opacity = '1';
        lbl.style.left = px + 'px';
        lbl.style.top = py + 'px';
      });

      renderer.render(scene, camera);
    };

    animate();

    // --- Cleanup ---
    return () => {
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('click', handleCanvasClick);
      canvas.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('touchstart', handleTouchStart);
      canvas.removeEventListener('touchend', handleTouchEnd);
      canvas.removeEventListener('touchmove', handleTouchMove);
      canvas.removeEventListener('wheel', handleWheel);
      cancelAnimationFrame(animationId);
      renderer.dispose();
    };
  }, []);

  // Update dynamic logic from state
  const aqiLevel = Math.max(aqmsData.pm25, aqmsData.pm10 * 0.5);

  const getAqiDetails = () => {
    if (aqiLevel > 55) {
      return { text: 'Berbahaya', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)' };
    } else if (aqiLevel > 35) {
      return { text: 'Tidak Sehat', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)' };
    } else if (aqiLevel > 12) {
      return { text: 'Sedang', color: '#eab308', bg: 'rgba(234,179,8,0.12)', border: 'rgba(234,179,8,0.3)' };
    } else {
      return { text: 'Baik', color: '#22c55e', bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.25)' };
    }
  };

  const getBarColor = (val: number) => {
    if (val > 55) return 'linear-gradient(to right,#f59e0b,#ef4444)';
    if (val > 12) return 'linear-gradient(to right,#eab308,#f59e0b)';
    return 'linear-gradient(to right,#22c55e,#22d3ee)';
  };

  const aqiInfo = getAqiDetails();
  const windDir = aqmsData.arah_angin;
  const dirLabels = ['U', 'TL', 'T', 'TG', 'S', 'BD', 'B', 'BL'];
  const dirLabel = dirLabels[Math.round(windDir / 45) % 8];

  const handleCloseModal = () => {
    setActiveModal(null);
    if (resetViewRef.current) {
      resetViewRef.current();
    }
  };

  const handleMobileNav = (view: typeof mobileView, btnId: string) => {
    setMobileView(view);
    document.querySelectorAll('.mob-nav-item').forEach(b => b.classList.remove('active'));
    document.getElementById(btnId)?.classList.add('active');

    if (view === 'tower') {
      setIsSidebarOpen(false);
    } else if (view === 'feeds') {
      setIsSidebarOpen(true);
    } else {
      setIsSidebarOpen(true);
      const targetMap: Record<string, string> = {
        alerts: '.alerts-list',
        settings: '#aqms-weather-card'
      };
      const targetSelector = targetMap[view];
      if (targetSelector) {
        setTimeout(() => {
          document.querySelector(targetSelector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 350);
      }
    }
  };

  return (
    <div className="tower-sentinel-portal">
      {/* ===== NAVBAR ===== */}
      <nav className="navbar">
        <button
          className="hamburger-btn"
          id="hamburger-btn"
          aria-label="Menu"
          onClick={() => setIsSidebarOpen(prev => !prev)}
        >
          &#9776;
        </button>
        <div className="nav-logo" onClick={() => navigate('/')}>
          <div className="nav-logo-icon">📡</div>
          TOWER SENTINEL
        </div>
        <div className="status-badge">
          <div className="status-dot"></div>
          <span className="badge-text">ACTIVE</span>
        </div>
        <div className="nav-search">
          <span className="nav-search-icon">🔍</span>
          <input type="text" placeholder="Search towers, cameras, alerts..." id="search-input" />
        </div>
        <div className="nav-actions">
          <button 
            className="theme-toggle-btn"
            onClick={toggleTheme}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: 'var(--text-muted)', 
              fontSize: '1.2rem', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              marginRight: '12px',
              transition: 'color 0.2s'
            }}
            title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
          >
            {theme === 'light' ? <FaMoon /> : <FaSun />}
          </button>
        </div>

      </nav>

      {/* ===== MAIN LAYOUT ===== */}
      <div className="main-layout">
        {/* Sidebar Icons */}
        <div className="sidebar-icons">
          <div
            className={`s-icon ${activeModal === null ? 'active' : ''}`}
            title="Beranda"
            onClick={() => {
              setActiveModal(null);
              if (resetViewRef.current) resetViewRef.current();
            }}
          >
            📡
          </div>
          <div
            className={`s-icon ${activeModal === 'nms' ? 'active' : ''}`}
            title="NMS Dashboard"
            onClick={() => {
              setActiveModal('nms');
              zoomToSystemRef.current?.('nms');
            }}
          >
            🖥️
          </div>
          <div
            className={`s-icon ${activeModal === 'verti' ? 'active' : ''}`}
            title="Verticality Dashboard"
            onClick={() => {
              setActiveModal('verti');
              zoomToSystemRef.current?.('verti');
            }}
          >
            ⚠️
          </div>
          <div
            className={`s-icon ${activeModal === 'aqms' ? 'active' : ''}`}
            title="AQMS Dashboard"
            onClick={() => {
              setActiveModal('aqms');
              zoomToSystemRef.current?.('aqms');
            }}
          >
            📊
          </div>
          <div className="s-icon" title="Settings" style={{ marginTop: 'auto' }}>⚙️</div>
        </div>

        {/* Left Panel */}
        <div className={`left-panel ${isSidebarOpen && mobileView !== 'feeds' ? 'open' : ''}`}>
                    {/* AQMS Weather Panel */}
          <div>
            <div className="panel-section-title">
              AQMS &middot; Weather
              <span className="view-all" style={{ color: 'var(--accent-green)' }} id="aqms-live-badge">Live</span>
            </div>
            <div className="weather-card" id="aqms-weather-card">
              <div className="aqms-top-row">
                <div className="aqms-temp-block">
                  <div className="weather-icon" id="aqms-icon">☀️</div>
                  <div>
                    <div className="weather-temp" id="aqms-suhu">{aqmsData.suhu.toFixed(1)}&deg;C</div>
                    <div className="weather-label" id="aqms-label">Cerah</div>
                  </div>
                </div>
                <div
                  className="aqi-badge"
                  id="aqi-badge"
                  style={{
                    background: aqiInfo.bg,
                    borderColor: aqiInfo.border
                  }}
                >
                  <div className="aqi-value" id="aqi-value" style={{ color: aqiInfo.color }}>{aqiInfo.text}</div>
                  <div className="aqi-sub">AQI</div>
                </div>
              </div>

              <div className="aqms-row">
                <span className="aqms-row-icon">💨</span>
                <span className="aqms-row-label">Angin</span>
                <span className="aqms-row-val">
                  <span id="aqms-angin">{aqmsData.kecepatan_angin.toFixed(2)} m/s</span>
                  <span className="aqms-dir" id="aqms-dir">{windDir}&deg; {dirLabel}</span>
                </span>
              </div>
              <div className="aqms-row">
                <span className="aqms-row-icon">💧</span>
                <span className="aqms-row-label">Lembap</span>
                <span className="aqms-row-val" id="aqms-lembap">{aqmsData.kelembapan.toFixed(1)}%</span>
              </div>
              <div className="aqms-row">
                <span className="aqms-row-icon">🌡️</span>
                <span className="aqms-row-label">Tekanan</span>
                <span className="aqms-row-val" id="aqms-tekanan">{aqmsData.tekanan.toFixed(2)} hPa</span>
              </div>
              <div className="aqms-row">
                <span className="aqms-row-icon">☀️</span>
                <span className="aqms-row-label">Cahaya</span>
                <span className="aqms-row-val" id="aqms-cahaya">{Number(aqmsData.cahaya).toLocaleString()} lux</span>
              </div>
              <div className="aqms-row">
                <span className="aqms-row-icon">⚡</span>
                <span className="aqms-row-label">Radiasi</span>
                <span className="aqms-row-val" id="aqms-radiasi">{aqmsData.radiasi} W/m&sup2;</span>
              </div>

              <div className="aqms-pm-row">
                <div className="aqms-pm-item">
                  <div className="aqms-pm-label">PM2.5</div>
                  <div className="aqms-pm-val" id="aqms-pm25">{aqmsData.pm25} &mu;g/m&sup3;</div>
                  <div className="aqms-pm-bar">
                    <div
                      className="aqms-pm-fill"
                      id="aqms-pm25-bar"
                      style={{
                        width: `${Math.max(2, Math.min(100, aqmsData.pm25 / 0.75))}%`,
                        background: getBarColor(aqmsData.pm25)
                      }}
                    ></div>
                  </div>
                </div>
                <div className="aqms-pm-item">
                  <div className="aqms-pm-label">PM10</div>
                  <div className="aqms-pm-val" id="aqms-pm10">{aqmsData.pm10} &mu;g/m&sup3;</div>
                  <div className="aqms-pm-bar">
                    <div
                      className="aqms-pm-fill"
                      id="aqms-pm10-bar"
                      style={{
                        width: `${Math.max(2, Math.min(100, aqmsData.pm10 / 1.5))}%`,
                        background: getBarColor(aqmsData.pm10)
                      }}
                    ></div>
                  </div>
                </div>
                <div className="aqms-pm-item">
                  <div className="aqms-pm-label">Ion-</div>
                  <div className="aqms-pm-val" id="aqms-ion">{aqmsData.ion_negatif}</div>
                  <div className="aqms-pm-bar">
                    <div
                      className="aqms-pm-fill"
                      id="aqms-ion-bar"
                      style={{
                        width: `${Math.min(100, aqmsData.ion_negatif / 10)}%`,
                        background: '#c084fc'
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <hr style={{ border: 'none', borderTop: '1px solid var(--border)' }} />

          {/* VERTICALITY — Structural Health */}
          <div className="verti-sidebar-panel">
            <div className="panel-section-title">
              Verticality
              <span className="view-all" style={{ color: 'var(--accent-cyan)' }}>● Live</span>
            </div>

            {/* Big Status Indicator */}
            <div className={`verti-indicator-badge ${
              vertiStatus.indikator === 'critical' ? 'critical' :
              vertiStatus.indikator === 'warning' ? 'warning' : 'normal'
            }`}>
              <span className="verti-indicator-icon">
                {vertiStatus.indikator === 'critical' ? '🔴' :
                 vertiStatus.indikator === 'warning' ? '⚠️' : '✅'}
              </span>
              <div className="verti-indicator-text">
                <span className="verti-indicator-label">Status Tower</span>
                <span className="verti-indicator-value">
                  {vertiStatus.indikator === 'critical' ? 'KRITIS' :
                   vertiStatus.indikator === 'warning' ? 'PERINGATAN' : 'NORMAL'}
                </span>
              </div>
            </div>

            {/* 4-Metric Grid */}
            <div className="verti-metrics-grid">
              <div className="verti-metric-item">
                <span className="verti-metric-val">{vertiStatus.pitch.toFixed(1)}°</span>
                <span className="verti-metric-label">Pitch</span>
              </div>
              <div className="verti-metric-item">
                <span className="verti-metric-val">{vertiStatus.roll.toFixed(1)}°</span>
                <span className="verti-metric-label">Roll</span>
              </div>
              <div className="verti-metric-item">
                <span className="verti-metric-val">{vertiStatus.totalTilt.toFixed(1)}°</span>
                <span className="verti-metric-label">Total Tilt</span>
              </div>
              <div className="verti-metric-item">
                <span className="verti-metric-val">{vertiStatus.windSpeed.toFixed(1)}</span>
                <span className="verti-metric-label">Wind m/s</span>
              </div>
            </div>

            {/* Tilt Gauge Bar */}
            <div className="verti-gauge-wrap">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                <span>Tilt Gauge</span>
                <span>{vertiStatus.totalTilt.toFixed(2)}° / 5° maks</span>
              </div>
              <div className="verti-gauge-track">
                <div
                  className="verti-gauge-fill"
                  style={{
                    width: `${Math.min((vertiStatus.totalTilt / 5) * 100, 100)}%`,
                    background: vertiStatus.indikator === 'critical'
                      ? 'linear-gradient(to right,#f59e0b,#ef4444)'
                      : vertiStatus.indikator === 'warning'
                      ? 'linear-gradient(to right,#fde68a,#f59e0b)'
                      : 'linear-gradient(to right,#22c55e,#22d3ee)'
                  }}
                />
              </div>
            </div>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border)' }} />

                    {/* SITE STATUS — NMS Live */}
          <div className="site-status-panel">
            <div className="panel-section-title">
              Site Status
              <span className="view-all" style={{ color: 'var(--accent-green)' }}>● Live</span>
            </div>

            {/* Sensor Status Rows */}
            <div className="sidebar-sensor-list">
              {/* PLN Power */}
              <div className="sidebar-sensor-row">
                <div className="sidebar-sensor-left">
                  <span className="sidebar-sensor-icon yellow">⚡</span>
                  <span className="sidebar-sensor-label">PLN Power</span>
                </div>
                <span className={`sidebar-sensor-pill ${
                  nmsStatus.plnStatus === 'ON' || nmsStatus.plnStatus === 'Active' ? 'green' : 'gray'
                }`}>
                  {nmsStatus.plnStatus === 'ON' || nmsStatus.plnStatus === 'Active' ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>

              {/* Door Sensor */}
              <div className="sidebar-sensor-row">
                <div className="sidebar-sensor-left">
                  <span className="sidebar-sensor-icon cyan">🚪</span>
                  <span className="sidebar-sensor-label">Door Sensor</span>
                </div>
                <span className={`sidebar-sensor-pill ${
                  nmsStatus.doorStatus === 'Open' || nmsStatus.doorStatus === 'OPEN' ? 'red' : 'green'
                }`}>
                  {nmsStatus.doorStatus === 'Open' || nmsStatus.doorStatus === 'OPEN' ? 'OPEN' : 'CLOSED'}
                </span>
              </div>

              {/* PIR Motion */}
              <div className="sidebar-sensor-row">
                <div className="sidebar-sensor-left">
                  <span className="sidebar-sensor-icon orange">👁️</span>
                  <span className="sidebar-sensor-label">Motion PIR</span>
                </div>
                <span className={`sidebar-sensor-pill ${nmsStatus.pirDetected ? 'red-pulse' : 'green'}`}>
                  {nmsStatus.pirDetected ? 'DETECTED' : 'STANDBY'}
                </span>
              </div>
            </div>

            {/* CCTV Mini Cards */}
            <div className="sidebar-cctv-label">CCTV Live Feed</div>
            <div className="sidebar-cctv-grid">
              <CCTVStreamCard streamId="cctv" cameraName="Kamera #1" />
              <CCTVStreamCard streamId="cctv2" cameraName="Kamera #2" />
            </div>
          </div>
        </div>

        {/* Center Panel (3D Tower) */}
        <div className="center-panel" style={{ position: 'relative' }}>
          <div className="center-header">
            <div>
              <div className="tower-view-title">TOWER VIEW</div>
              <div className="tower-selector">
                NAYAKA WS
              </div>
            </div>
          </div>

          <div className="center-panel-body">
            {/* 3D WebGL Canvas */}
            <canvas ref={towerCanvasRef} id="tower-canvas"></canvas>

            {/* Side Tool Buttons */}
            <div className="side-tools">
              <div className="side-tool-btn" title="Home View" onClick={() => resetViewRef.current?.()}>🏠</div>
              <div
                className="side-tool-btn"
                title="Auto Rotate"
                onClick={() => toggleAutoRotateRef.current?.()}
                style={{ color: isAutoRotate ? 'var(--accent-cyan)' : '' }}
              >
                🔄
              </div>
              <div className="side-tool-btn" title="Zoom In" onClick={() => zoomInRef.current?.()}>🔍</div>
              <div className="side-tool-btn" title="Zoom Out" onClick={() => zoomOutRef.current?.()}>🔎</div>
            </div>

            {/* Ground Glow Overlay */}
            <div className="ground-glow"></div>

            {/* Drag Hint */}
            <div className="rotate-hint">🖱️ Drag to rotate &middot; Scroll to zoom</div>

            {/* System Hotspot Labels (positions updated via JS in requestAnimationFrame) */}
            <div
              ref={labelNmsRef}
              id="label-nms"
              className="system-label"
              onClick={() => {
                setActiveModal('nms');
                zoomToSystemRef.current?.('nms');
              }}
            >
              <div className="sys-dot" style={{ background: '#f59e0b', boxShadow: '0 0 8px #f59e0b' }}></div>
              <div className="sys-content">
                <div className="sys-title">NMS</div>
                <div className="sys-sub">Panel &middot; 2 CCTV</div>
              </div>
            </div>

            <div
              ref={labelAqmsRef}
              id="label-aqms"
              className="system-label"
              onClick={() => {
                setActiveModal('aqms');
                zoomToSystemRef.current?.('aqms');
              }}
            >
              <div className="sys-dot" style={{ background: '#22d3ee', boxShadow: '0 0 8px #22d3ee' }}></div>
              <div className="sys-content">
                <div className="sys-title">AQMS</div>
                <div className="sys-sub">2 Weather Sensor</div>
              </div>
            </div>

            <div
              ref={labelVertiRef}
              id="label-verti"
              className="system-label"
              onClick={() => {
                setActiveModal('verti');
                zoomToSystemRef.current?.('verti');
              }}
            >
              <div className="sys-dot" style={{ background: '#c084fc', boxShadow: '0 0 8px #c084fc' }}></div>
              <div className="sys-content">
                <div className="sys-title">Verticality</div>
                <div className="sys-sub">Tilt Sensor</div>
              </div>
            </div>
          </div>

          {/* Bottom Toolbar */}
          <div className="center-toolbar">
            <div className="tool-btn active" title="3D View">🗼</div>
            <div
              className={`tool-btn ${isWireframe ? 'active' : ''}`}
              title="Wireframe"
              id="wireframe-btn"
              onClick={() => toggleWireframeRef.current?.()}
            >
              ⬡
            </div>
            <div className="tool-btn" title="Info">ℹ️</div>
            <div className="tool-sep"></div>
            <div className="tool-btn" title="Camera 1">📷</div>
            <div className="tool-btn" title="Camera 2">📷</div>
            <div className="tool-btn" title="Measure">📏</div>
            <div className="tool-btn" title="Download">⬇️</div>
            <div
              className="fullscreen-btn"
              title="Fullscreen"
              id="fullscreen-btn"
              onClick={() => {
                if (!document.fullscreenElement) {
                  document.documentElement.requestFullscreen();
                } else {
                  document.exitFullscreen();
                }
              }}
            >
              ⛶
            </div>
          </div>
        </div>

        {/* Right Panel (Notification Center / Peringatan Langsung) */}
        <div className={`right-panel ${isSidebarOpen && mobileView === 'feeds' ? 'open' : ''}`}>
          <div className="right-header">
            <div className="right-header-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🔔 Peringatan Langsung</span>
              {notifications.length > 0 && (
                <span className="notif-badge-header">{notifications.length}</span>
              )}
            </div>
            <button className="close-right-panel" onClick={() => setIsSidebarOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem', display: 'none' }}>&times;</button>
          </div>

          <div className="notif-search-container">
            <span className="notif-search-icon">🔍</span>
            <input
              type="text"
              className="notif-search-input"
              placeholder="Cari peringatan, sensor..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Categories Tab Row */}
          <div className="notif-tabs-row">
            {(['semua', 'gerakan', 'sensor'] as const).map((tab) => (
              <button
                key={tab}
                className={`notif-tab-btn ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'semua' && 'Semua'}
                {tab === 'gerakan' && 'Gerakan'}
                {tab === 'sensor' && 'Sensor'}
              </button>
            ))}
          </div>

          <div className="notif-list-container">
            {filteredNotifications.length === 0 ? (
              <div className="notif-empty-state">Tidak ada peringatan</div>
            ) : (
              filteredNotifications.map((item) => (
                <div
                  key={item.id}
                  className={`notif-item-card ${item.type}`}
                  onClick={() => {
                    if (item.imageUrl) {
                      setFullscreenPhotoUrl(item.imageUrl);
                      setFullscreenPhotoTitle(item.title);
                    }
                  }}
                >
                  <div className="notif-item-left">
                    <div className={`notif-icon-circle ${item.type}`}>
                      {item.type === 'camera' && <FaCamera />}
                      {item.type === 'pir' && <PiSiren />}
                      {item.type === 'door' && (item.status === 'OPEN' ? <FaDoorOpen /> : <FaDoorClosed />)}
                    </div>
                    <div className="notif-item-details">
                      <span className="notif-item-title">{item.title}</span>
                      <span className="notif-item-subtitle" dangerouslySetInnerHTML={{ __html: item.subtitle }}></span>
                      <span className="notif-item-time">{item.timestamp}</span>
                    </div>
                  </div>
                  {item.imageUrl && (
                    <div className="notif-item-right-thumb">
                      <img src={item.imageUrl} alt="alert thumbnail" />
                      <span className="expand-hint">🔎</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Fullscreen Photo Preview Modal */}
        {fullscreenPhotoUrl && (
          <div className="portal-photo-modal" onClick={() => setFullscreenPhotoUrl(null)}>
            <div className="photo-modal-wrapper" onClick={(e) => e.stopPropagation()}>
              <button className="photo-close-btn" onClick={() => setFullscreenPhotoUrl(null)}>&times;</button>
              <img src={fullscreenPhotoUrl} alt="Preview" className="photo-large" />
              <div className="photo-title">{fullscreenPhotoTitle}</div>
            </div>
          </div>
        )}

      </div>
      {/* Backdrop overlay (mobile drawer) */}
      {isSidebarOpen && (
        <div
          className="panel-backdrop active"
          id="panel-backdrop"
          onClick={() => {
            setIsSidebarOpen(false);
            setMobileView('tower');
          }}
        ></div>
      )}

      {/* ===== PORTAL MODAL OVERLAY & CONTENT ===== */}
      {activeModal && (
        <div className="portal-modal-overlay" onClick={handleCloseModal}>
          {activeModal === 'nms' && (
            <div className="nms-drawer" onClick={(e) => e.stopPropagation()}>
              <div className="nms-drawer-header">
                <div className="nms-header-left">
                  <div className="nms-title-row">
                    <h2>NAYAKA WS</h2>
                    <span className="status-badge-inline green">Online</span>
                  </div>
                  <p className="nms-subtitle">
                    PRR-01-004 &middot; Blok AX no, Jl. Kav. Marinir No.18, RT.14/RW.7, Duren Sawit, Jakarta Timur
                  </p>
                </div>
                <div className="nms-header-actions">
                  <button
                    className="nms-action-btn border primary"
                    onClick={() => {
                      setActiveModal(null);
                      if (resetViewRef.current) resetViewRef.current();
                      navigate('/site-detail');
                    }}
                  >
                    Lihat Detail
                  </button>
                  <button className="nms-close-btn" onClick={handleCloseModal}>&times;</button>
                </div>
              </div>

              <div className="nms-drawer-body">
                {/* SENSOR STATUS */}
                <div className="nms-section">
                  <h3 className="nms-section-title">SENSOR STATUS</h3>
                  <div className="nms-status-grid">
                    {/* Power Device */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper yellow"><FaBolt /></span>
                          <span className="card-name">Power Device</span>
                        </div>
                        <span className={`card-status-pill ${nmsStatus.plnStatus === 'ON' || nmsStatus.plnStatus === 'Active' ? 'green' : 'gray'}`}>
                          {nmsStatus.plnStatus === 'ON' || nmsStatus.plnStatus === 'Active' ? 'ON' : 'OFF'}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{nmsStatus.plnTime}</span>
                      </div>
                    </div>

                    {/* Pintu */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper cyan">
                            {nmsStatus.doorStatus === 'Open' || nmsStatus.doorStatus === 'OPEN' ? <FaDoorOpen /> : <FaDoorClosed />}
                          </span>
                          <span className="card-name">Door Sensor</span>
                        </div>
                        <span className={`card-status-pill ${nmsStatus.doorStatus === 'Open' || nmsStatus.doorStatus === 'OPEN' ? 'red-glow' : 'green'}`}>
                          {nmsStatus.doorStatus === 'Open' || nmsStatus.doorStatus === 'OPEN' ? 'OPEN' : 'CLOSED'}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{nmsStatus.doorTime}</span>
                      </div>
                    </div>

                    {/* PIR */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper orange"><PiSiren /></span>
                          <span className="card-name">Motion PIR</span>
                        </div>
                        <span className={`card-status-pill ${nmsStatus.pirDetected ? 'red-glow' : 'green'}`}>
                          {nmsStatus.pirDetected ? 'DETECTED' : 'STANDBY'}
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{nmsStatus.pirTime}</span>
                      </div>
                    </div>
                  </div>
                </div>


                {/* DEVICE CONTROL */}
                <div className="nms-section">
                  <h3 className="nms-section-title">DEVICE CONTROL</h3>
                  
                  {/* Lampu switch */}
                  <div className="nms-control-row">
                    <div className="control-info">
                      <span className="control-icon">💡</span>
                      <div className="control-text">
                        <span className="control-name">Lampu Rotary</span>
                        <span className="control-sub">Aktifkan lampu alarm rotary</span>
                      </div>
                    </div>
                    <div className="control-action">
                      <span className="switch-label-text" style={{ marginRight: '8px', fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                        {isLampuOn ? 'ON' : 'OFF'}
                      </span>
                      <button 
                        className={`toggle-switch-btn ${isLampuOn ? 'on' : 'off'}`}
                        onClick={toggleLampu}
                        disabled={isLampuLoading}
                      >
                        <span className="toggle-switch-slider"></span>
                      </button>
                    </div>
                  </div>

                  {/* Sirene control with Volume slider and buttons */}
                  <div className="nms-siren-control" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div className="siren-header">
                      <span className="control-icon">🔊</span>
                      <div className="control-text">
                        <span className="control-name">Sirene Audio Broadcast</span>
                        <span className="control-sub">Pilih suara untuk disiarkan ke site</span>
                      </div>
                    </div>

                    {/* Volume Slider */}
                    <div className="volume-slider-container" style={{ padding: '0 4px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
                        <span>Volume Speaker</span>
                        <span style={{ fontWeight: '700', color: 'var(--accent-blue)' }}>{volume}%</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '0.85rem' }}>🔈</span>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={volume}
                          onChange={(e) => {
                            const vol = parseInt(e.target.value);
                            setVolume(vol);
                            sendVolumeToMqtt(vol);
                          }}
                          style={{
                            flex: 1,
                            accentColor: 'var(--accent-blue)',
                            height: '4px',
                            cursor: 'pointer'
                          }}
                        />
                        <span style={{ fontSize: '0.85rem' }}>🔊</span>
                      </div>
                    </div>

                    <div className="siren-buttons-grid">
                      {['Suara 1', 'Suara 2', 'Suara 3', 'Polisi', 'Darurat', 'Beep'].map((soundName) => (
                        <button
                          key={soundName}
                          className={`siren-action-btn ${sirineStatus === soundName ? 'active' : ''}`}
                          onClick={() => triggerSirine(soundName)}
                        >
                          {soundName}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* CCTV */}
                <div className="nms-section">
                  <h3 className="nms-section-title">CCTV</h3>
                  <div className="nms-cctv-grid">
                    <CCTVStreamCard streamId="cctv-modal-1" cameraName="Kamera #1" />
                    <CCTVStreamCard streamId="cctv-modal-2" cameraName="Kamera #2" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeModal === 'verti' && (
            <div className="nms-drawer" onClick={(e) => e.stopPropagation()}>
              <div className="nms-drawer-header">
                <div className="nms-header-left">
                  <div className="nms-title-row">
                    <h2>NAYAKA WS</h2>
                    <span className={`status-badge-inline ${vertiStatus.indikator === 'tolerance' ? 'green' : 'red'}`}>
                      {vertiStatus.indikator === 'tolerance' ? 'Tolerance' : 'Intolerance'}
                    </span>
                  </div>
                  <p className="nms-subtitle">
                    20TS10B1529 &middot; SST 42m &middot; structural verticality monitoring
                  </p>
                </div>
                <div className="nms-header-actions">
                  <button
                    className="nms-action-btn border primary"
                    onClick={() => {
                      setActiveModal(null);
                      if (resetViewRef.current) resetViewRef.current();
                      navigate('/verticality/E32_VER_WS');
                    }}
                  >
                    Lihat Detail
                  </button>
                  <button className="nms-close-btn" onClick={handleCloseModal}>&times;</button>
                </div>
              </div>

              <div className="nms-drawer-body">
                {/* SENSOR STATUS */}
                <div className="nms-section">
                  <h3 className="nms-section-title">VERTICALITY TELEMETRY</h3>
                  <div className="nms-status-grid">
                    {/* Total Tilt */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper purple">📊</span>
                          <span className="card-name">Total Tilt</span>
                        </div>
                        <span className={`card-status-pill ${vertiStatus.indikator === 'tolerance' ? 'green' : 'red-glow'}`}>
                          {vertiStatus.totalTilt.toFixed(3)}&deg;
                        </span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{vertiStatus.timestamp}</span>
                      </div>
                    </div>

                    {/* Wind Speed */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper yellow">💨</span>
                          <span className="card-name">Wind Speed</span>
                        </div>
                        <span className="card-val">{vertiStatus.windSpeed.toFixed(1)} Knot</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{vertiStatus.timestamp}</span>
                      </div>
                    </div>

                    {/* Pitch */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper cyan">↕️</span>
                          <span className="card-name">Pitch Angle</span>
                        </div>
                        <span className="card-val">{vertiStatus.pitch.toFixed(3)}&deg;</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{vertiStatus.timestamp}</span>
                      </div>
                    </div>

                    {/* Roll */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper blue">↔️</span>
                          <span className="card-name">Roll Angle</span>
                        </div>
                        <span className="card-val">{vertiStatus.roll.toFixed(3)}&deg;</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{vertiStatus.timestamp}</span>
                      </div>
                    </div>

                    {/* Sway */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper green">🔄</span>
                          <span className="card-name">Sway Displacement</span>
                        </div>
                        <span className="card-val">{vertiStatus.sway.toFixed(1)} mm</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">{vertiStatus.timestamp}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="nms-section" style={{ borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
                  <h3 className="nms-section-title">SISTEM KETERANGAN</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Tipe Tower:</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>Self Supporting Tower (SST)</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Tinggi Tower:</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>42 Meter</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Lokasi:</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>Jakarta Timur</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeModal === 'aqms' && (
            <div className="nms-drawer" onClick={(e) => e.stopPropagation()}>
              <div className="nms-drawer-header">
                <div className="nms-header-left">
                  <div className="nms-title-row">
                    <h2>NAYAKA WS</h2>
                    <span className="status-badge-inline green">Online</span>
                  </div>
                  <p className="nms-subtitle">
                    20TS10B1529 &middot; SST 42m &middot; air quality monitoring system
                  </p>
                </div>
                <div className="nms-header-actions">
                  <button
                    className="nms-action-btn border primary"
                    onClick={() => {
                      setActiveModal(null);
                      if (resetViewRef.current) resetViewRef.current();
                      navigate('/aqms');
                    }}
                  >
                    Lihat Detail
                  </button>
                  <button className="nms-close-btn" onClick={handleCloseModal}>&times;</button>
                </div>
              </div>

              <div className="nms-drawer-body">
                {/* SENSOR STATUS */}
                <div className="nms-section">
                  <h3 className="nms-section-title">AQMS TELEMETRY</h3>
                  <div className="nms-status-grid">
                    {/* PM2.5 */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper purple">🌾</span>
                          <span className="card-name">PM2.5</span>
                        </div>
                        <span className="card-val">{aqmsData.pm25.toFixed(1)} ug/m³</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">Partikulat Debu</span>
                      </div>
                    </div>

                    {/* PM10 */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper purple">🌾</span>
                          <span className="card-name">PM10</span>
                        </div>
                        <span className="card-val">{aqmsData.pm10.toFixed(1)} ug/m³</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">Partikulat Debu</span>
                      </div>
                    </div>

                    {/* Temperature */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper yellow">🌡️</span>
                          <span className="card-name">Suhu</span>
                        </div>
                        <span className="card-val">{aqmsData.suhu.toFixed(1)}&deg;C</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">Suhu Udara</span>
                      </div>
                    </div>

                    {/* Humidity */}
                    <div className="nms-status-card">
                      <div className="card-header">
                        <div className="card-title-group">
                          <span className="card-icon-wrapper blue">💧</span>
                          <span className="card-name">Lembap</span>
                        </div>
                        <span className="card-val">{aqmsData.kelembapan.toFixed(1)}%</span>
                      </div>
                      <div className="card-footer">
                        <span className="card-time">Kelembapan Relatif</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="nms-section" style={{ borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
                  <h3 className="nms-section-title">AQMS OVERVIEW</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Sensor Status:</span>
                      <span style={{ color: 'var(--accent-green)', fontWeight: 'bold' }}>📡 OK (Normal)</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Ion Negatif:</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{aqmsData.ion_negatif} ion/cm³</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Intensitas Cahaya:</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{aqmsData.cahaya} lux</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}



      {/* Mobile bottom navigation */}
      <nav className="mobile-bottom-nav" id="mobile-bottom-nav">
        <button
          className="mob-nav-item active"
          id="mob-tower"
          onClick={() => handleMobileNav('tower', 'mob-tower')}
        >
          <span>📡</span><span className="mob-nav-label">Tower</span>
        </button>
        <button
          className="mob-nav-item"
          id="mob-data"
          onClick={() => handleMobileNav('data', 'mob-data')}
        >
          <span>📊</span><span className="mob-nav-label">Data</span>
        </button>
        <button
          className="mob-nav-item"
          id="mob-alerts"
          onClick={() => handleMobileNav('alerts', 'mob-alerts')}
        >
          <span>⚠️</span><span className="mob-nav-label">Alert</span>
        </button>
        <button
          className="mob-nav-item"
          id="mob-feeds"
          onClick={() => handleMobileNav('feeds', 'mob-feeds')}
        >
          <span>🔔</span><span className="mob-nav-label">Notifikasi</span>
        </button>
        <button
          className="mob-nav-item"
          id="mob-settings"
          onClick={() => handleMobileNav('settings', 'mob-settings')}
        >
          <span>⚙️</span><span className="mob-nav-label">More</span>
        </button>
      </nav>
    </div>
  );
};

export default TowerSentinel;
