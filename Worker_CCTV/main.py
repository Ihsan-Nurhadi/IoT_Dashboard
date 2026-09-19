import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from camera_streamer import CameraStreamer
from onvif_client import OnvifGatewayClient

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("gateway_main")

# Initialize global instances
streamer = CameraStreamer()
onvif_client = OnvifGatewayClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start background RTSP streamer
    logger.info("Initializing CCTV Gateway Worker...")
    streamer.start()

    # Attempt background ONVIF handshake
    try:
        onvif_client.connect()
    except Exception as e:
        logger.warning(f"Initial ONVIF handshake deferred: {e}")

    yield

    # Shutdown: cleanly close resources
    logger.info("Shutting down CCTV Gateway Worker...")
    streamer.stop()


app = FastAPI(
    title="CCTV RTSP & ONVIF Gateway API",
    description="Microservice worker that bridges VPN-restricted RTSP camera stream and ONVIF controls into public HTTP/REST APIs.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for all origins so React / Vue / external dashboards can consume APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    err_tb = traceback.format_exc()
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}\n{err_tb}")
    return HTMLResponse(
        content=f"<h3>500 Internal Server Error</h3><p><b>{exc}</b></p><pre>{err_tb}</pre>",
        status_code=500,
    )


# -----------------------------------------------------------------------------
# Web UI & Health
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, tags=["Web Dashboard"])
async def dashboard_view():
    """
    Renders the modern interactive Web Dashboard with live video stream,
    PTZ controls, telemetry stats, and quick links.
    """
    if os.path.exists(INDEX_HTML_PATH):
        try:
            with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except Exception as e:
            logger.error(f"Error reading index.html: {e}")
            return HTMLResponse(f"<h3>Error loading index.html: {e}</h3>", status_code=500)

    return HTMLResponse(
        "<h2>Worker CCTV Gateway</h2><p>index.html not found. <a href='/docs'>Swagger API Docs</a></p>"
    )


@app.get("/api/health", tags=["Telemetry & Status"])
async def health_check():
    """
    Simple health check for Docker, load balancers, or uptime monitors.
    """
    return {"status": "ok", "service": "Worker_CCTV_Gateway"}


@app.get("/api/status", tags=["Telemetry & Status"])
async def get_stream_status():
    """
    Returns real-time telemetry from the RTSP streamer (FPS, resolution, connection status).
    """
    status_data = streamer.get_status()
    status_data["onvif_connected"] = onvif_client.connected
    return status_data


# -----------------------------------------------------------------------------
# Video Streaming & Snapshot
# -----------------------------------------------------------------------------

@app.get("/api/stream", tags=["Video Stream"])
async def get_live_mjpeg_stream():
    """
    Streams live MJPEG video over HTTP (multipart/x-mixed-replace).
    Can be loaded directly in any HTML `<img src="/api/stream">`,
    VLC media player, React Dashboard, or mobile browser without VPN.
    """
    return StreamingResponse(
        streamer.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close",
        },
    )


@app.get("/api/snapshot", tags=["Video Stream"])
async def get_instant_snapshot():
    """
    Captures and downloads a single real-time JPEG snapshot from the camera stream.
    """
    jpeg_bytes = streamer.get_snapshot()
    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Content-Disposition": "inline; filename=snapshot.jpg",
        },
    )


# -----------------------------------------------------------------------------
# ONVIF REST API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/onvif/device-info", tags=["ONVIF Control"])
async def get_onvif_device_info():
    """
    Retrieves device information (Manufacturer, Model, Firmware, Serial Number).
    """
    return onvif_client.get_device_info()


@app.get("/api/onvif/profiles", tags=["ONVIF Control"])
async def get_onvif_profiles():
    """
    Lists media encoding profiles available on the camera.
    """
    return onvif_client.get_profiles()


@app.get("/api/onvif/stream-uri", tags=["ONVIF Control"])
async def get_onvif_stream_uri(profile_token: Optional[str] = None):
    """
    Retrieves the camera RTSP Stream URI reported by the ONVIF Media service.
    """
    uri = onvif_client.get_stream_uri(profile_token)
    if not uri:
        raise HTTPException(status_code=404, detail="Stream URI not available")
    return {"stream_uri": uri}


@app.get("/api/onvif/snapshot-uri", tags=["ONVIF Control"])
async def get_onvif_snapshot_uri(profile_token: Optional[str] = None):
    """
    Retrieves the camera HTTP Snapshot URI reported by the ONVIF Media service.
    """
    uri = onvif_client.get_snapshot_uri(profile_token)
    if not uri:
        raise HTTPException(status_code=404, detail="Snapshot URI not available")
    return {"snapshot_uri": uri}


class PtzMoveRequest(BaseModel):
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Pan speed from -1.0 (left) to 1.0 (right)")
    tilt: float = Field(default=0.0, ge=-1.0, le=1.0, description="Tilt speed from -1.0 (down) to 1.0 (up)")
    zoom: float = Field(default=0.0, ge=-1.0, le=1.0, description="Zoom speed from -1.0 (out) to 1.0 (in)")
    profile_token: Optional[str] = Field(default=None, description="Optional profile token")


class PtzStopRequest(BaseModel):
    profile_token: Optional[str] = Field(default=None, description="Optional profile token")


class PtzGotoPresetRequest(BaseModel):
    preset_token: str = Field(description="Token of the preset to move to")
    profile_token: Optional[str] = Field(default=None, description="Optional profile token")


@app.post("/api/onvif/ptz/move", tags=["ONVIF Control"])
async def ptz_continuous_move(req: PtzMoveRequest):
    """
    Controls camera movement in continuous Pan, Tilt, or Zoom.
    """
    res = onvif_client.ptz_continuous_move(
        profile_token=req.profile_token,
        pan=req.pan,
        tilt=req.tilt,
        zoom=req.zoom,
    )
    return res


@app.post("/api/onvif/ptz/stop", tags=["ONVIF Control"])
async def ptz_stop_movement(req: Optional[PtzStopRequest] = None):
    """
    Immediately stops all Pan, Tilt, and Zoom motion on the camera.
    """
    token = req.profile_token if req else None
    res = onvif_client.ptz_stop(profile_token=token)
    return res


@app.get("/api/onvif/ptz/presets", tags=["ONVIF Control"])
async def get_ptz_presets(profile_token: Optional[str] = None):
    """
    Lists saved PTZ presets on the camera.
    """
    return onvif_client.ptz_get_presets(profile_token=profile_token)


@app.post("/api/onvif/ptz/goto-preset", tags=["ONVIF Control"])
async def goto_ptz_preset(req: PtzGotoPresetRequest):
    """
    Moves the camera to a specified preset location.
    """
    return onvif_client.ptz_goto_preset(preset_token=req.preset_token, profile_token=req.profile_token)


# -----------------------------------------------------------------------------
# Transparent ONVIF SOAP Proxy (for External VMS / NVR / ONVIF Device Manager)
# -----------------------------------------------------------------------------

@app.post("/onvif/{service_path:path}", tags=["ONVIF Transparent Proxy"])
@app.post("/onfiv/{service_path:path}", tags=["ONVIF Transparent Proxy"])
async def onvif_soap_proxy(service_path: str, request: Request):
    """
    Transparent reverse-proxy for ONVIF SOAP requests.
    Enables external VMS software, Synology Surveillance, or ONVIF Device Manager
    to connect directly to this gateway without a VPN client.
    """
    body = await request.body()
    incoming_headers = dict(request.headers)
    full_path = f"onvif/{service_path}"

    content, status_code, content_type = onvif_client.proxy_soap_request(
        target_path=full_path,
        body_bytes=body,
        incoming_headers=incoming_headers,
    )
    return Response(content=content, status_code=status_code, media_type=content_type)


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("GATEWAY_PORT", 3001))
    logger.info(f"Starting CCTV API Gateway on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False, workers=1)
