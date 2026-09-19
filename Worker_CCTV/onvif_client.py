import os
import logging
from urllib.parse import urlparse
import httpx
import requests

logger = logging.getLogger("cctv_onvif")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")


class OnvifGatewayClient:
    """
    Client for interacting with ONVIF camera services and forwarding SOAP requests.
    Handles device management, media profiles, PTZ control, and transparent SOAP proxying.
    """

    def __init__(
        self,
        host=None,
        port=None,
        path=None,
        user=None,
        password=None,
        wsdl_dir=None,
    ):
        self.host = host or os.getenv("CAMERA_HOST", "10.10.1.17")
        self.port = int(port or os.getenv("ONVIF_PORT", 2020))
        self.path = path or os.getenv("ONVIF_PATH", "/onfiv/device_service")
        self.user = user or os.getenv("CAMERA_USER", "NMSIOTYOGYA1")
        self.password = password or os.getenv("CAMERA_PASS", "Nayaka2025")

        default_wsdl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wsdl")
        self.wsdl_dir = wsdl_dir or default_wsdl

        self.cam = None
        self.media_service = None
        self.ptz_service = None
        self.connected = False
        self.last_error = None

    def _rewrite_url(self, url_str):
        if not url_str:
            return url_str
        try:
            parsed = urlparse(str(url_str))
            path_and_query = parsed.path
            if parsed.query:
                path_and_query += f"?{parsed.query}"
            return f"http://{self.host}:{self.port}{path_and_query}"
        except Exception:
            return url_str

    def connect(self):
        try:
            from onvif import ONVIFCamera

            logger.info(f"Connecting to ONVIF at http://{self.host}:{self.port}{self.path}...")
            self.cam = ONVIFCamera(
                self.host,
                self.port,
                self.user,
                self.password,
                wsdl_dir=self.wsdl_dir if os.path.exists(self.wsdl_dir) else None,
            )

            # Rewrite all service XAddrs returned by camera to match VPN target IP:port
            for ns, addr in list(self.cam.xaddrs.items()):
                if addr:
                    self.cam.xaddrs[ns] = self._rewrite_url(addr)

            # Initialize Media Service
            try:
                self.media_service = self.cam.create_media_service()
                if hasattr(self.media_service, "ws_client") and hasattr(self.media_service.ws_client, "service"):
                    cur_addr = getattr(self.media_service.ws_client.service, "_binding_options", {}).get("address")
                    if cur_addr:
                        self.media_service.ws_client.service._binding_options["address"] = self._rewrite_url(cur_addr)
            except Exception as e:
                logger.warning(f"Failed to create Media service: {e}")

            # Initialize PTZ Service
            try:
                self.ptz_service = self.cam.create_ptz_service()
                if hasattr(self.ptz_service, "ws_client") and hasattr(self.ptz_service.ws_client, "service"):
                    cur_addr = getattr(self.ptz_service.ws_client.service, "_binding_options", {}).get("address")
                    if cur_addr:
                        self.ptz_service.ws_client.service._binding_options["address"] = self._rewrite_url(cur_addr)
            except Exception as e:
                logger.debug(f"PTZ service not available or not supported: {e}")

            self.connected = True
            self.last_error = None
            logger.info("ONVIF services successfully initialized!")
            return True
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            logger.error(f"Error connecting to ONVIF: {e}")
            return False

    def ensure_connected(self):
        if not self.connected or self.cam is None:
            return self.connect()
        return True

    def get_device_info(self):
        if not self.ensure_connected():
            return {"error": self.last_error or "ONVIF not connected", "connected": False}
        try:
            dev_info = self.cam.devicemgmt.GetDeviceInformation()
            return {
                "connected": True,
                "manufacturer": getattr(dev_info, "Manufacturer", "Unknown"),
                "model": getattr(dev_info, "Model", "Unknown"),
                "firmware_version": getattr(dev_info, "FirmwareVersion", "Unknown"),
                "serial_number": getattr(dev_info, "SerialNumber", "Unknown"),
                "hardware_id": getattr(dev_info, "HardwareId", "Unknown"),
                "onvif_endpoint": f"http://{self.host}:{self.port}{self.path}",
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def get_profiles(self):
        if not self.ensure_connected():
            return []
        try:
            if not self.media_service:
                self.media_service = self.cam.create_media_service()

            profiles = self.media_service.GetProfiles()
            result = []
            for p in profiles:
                token = p.token
                name = p.Name
                vec = getattr(p, "VideoEncoderConfiguration", None)
                res = "Unknown"
                fps = 0
                if vec and hasattr(vec, "Resolution"):
                    res = f"{vec.Resolution.Width}x{vec.Resolution.Height}"
                if vec and hasattr(vec, "RateControl") and hasattr(vec.RateControl, "FrameRateLimit"):
                    fps = vec.RateControl.FrameRateLimit

                result.append({
                    "token": token,
                    "name": name,
                    "resolution": res,
                    "frame_rate_limit": fps,
                })
            return result
        except Exception as e:
            logger.error(f"Error getting ONVIF profiles: {e}")
            return []

    def get_stream_uri(self, profile_token=None):
        if not self.ensure_connected() or not self.media_service:
            return None
        try:
            if not profile_token:
                profiles = self.get_profiles()
                if profiles:
                    profile_token = profiles[0]["token"]
                else:
                    return None

            req = self.media_service.create_type("GetStreamUri")
            req.ProfileToken = profile_token
            req.StreamSetup = {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"},
            }
            uri_obj = self.media_service.GetStreamUri(req)
            return uri_obj.Uri
        except Exception as e:
            logger.error(f"Error getting ONVIF Stream URI: {e}")
            return None

    def get_snapshot_uri(self, profile_token=None):
        if not self.ensure_connected() or not self.media_service:
            return None
        try:
            if not profile_token:
                profiles = self.get_profiles()
                if profiles:
                    profile_token = profiles[0]["token"]
                else:
                    return None

            req = self.media_service.create_type("GetSnapshotUri")
            req.ProfileToken = profile_token
            uri_obj = self.media_service.GetSnapshotUri(req)
            return uri_obj.Uri
        except Exception as e:
            logger.error(f"Error getting ONVIF Snapshot URI: {e}")
            return None

    def ptz_continuous_move(self, profile_token=None, pan=0.0, tilt=0.0, zoom=0.0):
        """
        Move camera continuously with speeds in range [-1.0, 1.0].
        """
        if not self.ensure_connected():
            return {"status": "error", "message": "Camera not connected"}
        if not self.ptz_service:
            return {"status": "error", "message": "PTZ not supported on this camera"}

        try:
            if not profile_token:
                profiles = self.get_profiles()
                if profiles:
                    profile_token = profiles[0]["token"]
                else:
                    return {"status": "error", "message": "No profile found"}

            request = self.ptz_service.create_type("ContinuousMove")
            request.ProfileToken = profile_token
            request.Velocity = {
                "PanTilt": {"x": float(pan), "y": float(tilt)},
                "Zoom": {"x": float(zoom)},
            }
            self.ptz_service.ContinuousMove(request)
            return {"status": "success", "action": "ContinuousMove", "pan": pan, "tilt": tilt, "zoom": zoom}
        except Exception as e:
            logger.error(f"PTZ ContinuousMove failed: {e}")
            return {"status": "error", "message": str(e)}

    def ptz_stop(self, profile_token=None):
        if not self.ensure_connected():
            return {"status": "error", "message": "Camera not connected"}
        if not self.ptz_service:
            return {"status": "error", "message": "PTZ not supported on this camera"}

        try:
            if not profile_token:
                profiles = self.get_profiles()
                if profiles:
                    profile_token = profiles[0]["token"]
                else:
                    return {"status": "error", "message": "No profile found"}

            request = self.ptz_service.create_type("Stop")
            request.ProfileToken = profile_token
            request.PanTilt = True
            request.Zoom = True
            self.ptz_service.Stop(request)
            return {"status": "success", "action": "Stop"}
        except Exception as e:
            logger.error(f"PTZ Stop failed: {e}")
            return {"status": "error", "message": str(e)}

    def ptz_get_presets(self, profile_token=None):
        if not self.ensure_connected() or not self.ptz_service:
            return []
        try:
            if not profile_token:
                profiles = self.get_profiles()
                if profiles:
                    profile_token = profiles[0]["token"]
                else:
                    return []

            request = self.ptz_service.create_type("GetPresets")
            request.ProfileToken = profile_token
            presets = self.ptz_service.GetPresets(request)
            result = []
            for p in presets:
                result.append({
                    "token": p.token,
                    "name": getattr(p, "Name", p.token),
                })
            return result
        except Exception as e:
            logger.error(f"PTZ GetPresets failed: {e}")
            return []

    def ptz_goto_preset(self, preset_token, profile_token=None):
        if not self.ensure_connected() or not self.ptz_service:
            return {"status": "error", "message": "PTZ not available"}
        try:
            if not profile_token:
                profiles = self.get_profiles()
                if profiles:
                    profile_token = profiles[0]["token"]
                else:
                    return {"status": "error", "message": "No profile found"}

            request = self.ptz_service.create_type("GotoPreset")
            request.ProfileToken = profile_token
            request.PresetToken = preset_token
            self.ptz_service.GotoPreset(request)
            return {"status": "success", "action": "GotoPreset", "preset_token": preset_token}
        except Exception as e:
            logger.error(f"PTZ GotoPreset failed: {e}")
            return {"status": "error", "message": str(e)}

    def proxy_soap_request(self, target_path, body_bytes, incoming_headers):
        """
        Transparently proxies incoming ONVIF SOAP requests to the camera.
        Rewrites camera host in response if needed.
        """
        # Clean path
        target_path = target_path.lstrip("/")
        target_url = f"http://{self.host}:{self.port}/{target_path}"

        # Clean headers for forwarding
        headers = {}
        for k, v in incoming_headers.items():
            if k.lower() not in ["host", "content-length"]:
                headers[k] = v

        try:
            resp = requests.post(
                target_url,
                data=body_bytes,
                headers=headers,
                timeout=10.0,
                auth=requests.auth.HTTPDigestAuth(self.user, self.password),
            )
            # Forward status and content
            response_content = resp.content
            # Optionally rewrite camera internal IP with public host
            content_type = resp.headers.get("Content-Type", "application/soap+xml; charset=utf-8")
            return response_content, resp.status_code, content_type
        except Exception as e:
            logger.error(f"Error in SOAP proxy to {target_url}: {e}")
            error_soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <soap:Fault>
      <soap:Code><soap:Value>soap:Receiver</soap:Value></soap:Code>
      <soap:Reason><soap:Text xml:lang="en">Gateway failed to reach camera: {e}</soap:Text></soap:Reason>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""
            return error_soap.encode("utf-8"), 502, "application/soap+xml; charset=utf-8"
