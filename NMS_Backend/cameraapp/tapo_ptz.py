from onvif import ONVIFCamera
import time

def get_ptz_controller(cam1):
    camera = ONVIFCamera(
        cam1["ip"],
        2020,
        cam1["username"],
        cam1["password"]
    )

    ptz = camera.create_ptz_service()
    media = camera.create_media_service()
    profile = media.GetProfiles()[0]

    return ptz, profile.token

def get_ptz_controller2(cam2):
    camera = ONVIFCamera(
        cam2["ip2"],
        2020,
        cam2["username2"],
        cam2["password2"]
    )

    ptz = camera.create_ptz_service()
    media = camera.create_media_service()
    profile = media.GetProfiles()[0]

    return ptz, profile.token

def move_ptz1(cam1, x, y, duration=0.3):
    ptz, token = get_ptz_controller(cam1)

    req = ptz.create_type("ContinuousMove")
    req.ProfileToken = token
    req.Velocity = {"PanTilt": {"x": x, "y": y}}

    ptz.ContinuousMove(req)
    time.sleep(duration)
    ptz.Stop({"ProfileToken": token})

def move_ptz2(cam2, x, y, duration=0.3):
    ptz, token = get_ptz_controller2(cam2)

    req = ptz.create_type("ContinuousMove")
    req.ProfileToken = token
    req.Velocity = {"PanTilt": {"x": x, "y": y}}

    ptz.ContinuousMove(req)
    time.sleep(duration)
    ptz.Stop({"ProfileToken": token})