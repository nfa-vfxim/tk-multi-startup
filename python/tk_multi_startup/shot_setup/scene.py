"""
The Maya side of Shot Setup: the shot camera, its image plane and the scene
settings, plus a marker node so the automatic setup only ever runs once.

What an update touches (so an artist's own work survives):
  camera       focal length, filmback, film fit. Never its transform/animation.
  image plane  file, frame offset. Never its depth, alpha, colour or placement.
  scene        render resolution and pixel aspect, frame range (only when
               ShotGrid has no cut in/out the plate range is used).
"""

import getpass
import time

import maya.cmds as cmds

MARKER = "NFA_shotSetup"
MM_PER_INCH = 25.4
DEFAULT_CAMERAS = {"persp", "top", "front", "side", "bottom", "back", "left"}
NEAR_CLIP = 10.0          # same as tk-multi-startup's default for new cameras
FAR_CLIP = 1000000.0


# --------------------------------------------------------------------------- marker
def _add_attr(node, name, kind):
    if cmds.attributeQuery(name, node=node, exists=True):
        return
    if kind == "string":
        cmds.addAttr(node, longName=name, dataType="string")
    elif kind == "message":
        cmds.addAttr(node, longName=name, attributeType="message")
    else:
        cmds.addAttr(node, longName=name, attributeType=kind)


def marker(create=False):
    if cmds.objExists(MARKER):
        return MARKER
    if not create:
        return None
    node = cmds.createNode("network", name=MARKER, skipSelect=True)
    for name, kind in (("toolVersion", "string"), ("shotId", "long"), ("shotCode", "string"),
                       ("camera", "message"), ("imagePlane", "message"), ("plate", "string"),
                       ("focal", "double"), ("filmbackWidth", "double"), ("filmbackHeight", "double"),
                       ("setupAt", "string"), ("setupBy", "string"), ("updatedAt", "string")):
        _add_attr(node, name, kind)
    return node


def _linked(attr):
    node = marker()
    if not node or not cmds.attributeQuery(attr, node=node, exists=True):
        return None
    src = cmds.listConnections("%s.%s" % (node, attr), source=True, destination=False) or []
    return src[0] if src else None


def _link(attr, target):
    node = marker(create=True)
    plug = "%s.%s" % (node, attr)
    for old in cmds.listConnections(plug, source=True, destination=False, plugs=True) or []:
        cmds.disconnectAttr(old, plug)
    if target:
        cmds.connectAttr("%s.message" % target, plug, force=True)


def _set_str(attr, value):
    cmds.setAttr("%s.%s" % (marker(create=True), attr), value or "", type="string")


def was_set_up():
    return marker() is not None


def is_empty_scene():
    """No DAG content besides Maya's default cameras."""
    tops = cmds.ls(assemblies=True) or []
    return not [t for t in tops if t not in DEFAULT_CAMERAS]


# --------------------------------------------------------------------------- state
def _shape(transform, kind):
    if not transform or not cmds.objExists(transform):
        return None
    if cmds.nodeType(transform) == kind:
        return transform
    shapes = cmds.listRelatives(transform, shapes=True, type=kind, fullPath=True) or []
    return shapes[0] if shapes else None


def camera():
    """(transform, shape) of the shot camera, or (None, None)."""
    t = _linked("camera")
    s = _shape(t, "camera")
    return (t, s) if s else (None, None)


def image_plane():
    """imagePlane shape of the shot camera, or None."""
    node = _linked("imagePlane")
    shape = _shape(node, "imagePlane")
    if shape:
        return shape
    _t, cam = camera()
    if cam:
        for ip in cmds.listConnections(cam + ".imagePlane", source=True, destination=False) or []:
            shape = _shape(ip, "imagePlane")
            if shape:
                return shape
    return None


def state():
    """What is in the scene now (for the dialog)."""
    t, s = camera()
    ip = image_plane()
    out = {"marker": was_set_up(), "camera": t, "focal": None, "filmback": None,
           "image_plane": ip, "plate": None, "offset": None}
    if s:
        out["focal"] = round(cmds.getAttr(s + ".focalLength"), 3)
        out["filmback"] = (round(cmds.getAttr(s + ".horizontalFilmAperture") * MM_PER_INCH, 3),
                           round(cmds.getAttr(s + ".verticalFilmAperture") * MM_PER_INCH, 3))
    if ip:
        out["plate"] = cmds.getAttr(ip + ".imageName") or ""
        out["offset"] = cmds.getAttr(ip + ".frameOffset")
    return out


# --------------------------------------------------------------------------- build
def _unique(name):
    if not cmds.objExists(name):
        return name
    i = 1
    while cmds.objExists("%s%d" % (name, i)):
        i += 1
    return "%s%d" % (name, i)


def ensure_camera(data, plate=None):
    """Create the shot camera, or update the lens of the existing one."""
    t, s = camera()
    if not s:
        t, s = cmds.camera()
        t = cmds.rename(t, _unique("shotCam_%s" % data.node_suffix))
        s = cmds.rename(_shape(t, "camera"), t.split("|")[-1] + "Shape")
        s = _shape(t, "camera")
        cmds.setAttr(s + ".nearClipPlane", NEAR_CLIP)
        cmds.setAttr(s + ".farClipPlane", FAR_CLIP)
        cmds.setAttr(s + ".displayResolution", 1)
        cmds.setAttr(s + ".displayGateMask", 1)
        cmds.setAttr(s + ".overscan", 1.1)
        _link("camera", t)
    cmds.setAttr(s + ".focalLength", float(data.focal))
    fb = data.camera_filmback(plate)
    cmds.setAttr(s + ".horizontalFilmAperture", fb[0] / MM_PER_INCH)
    cmds.setAttr(s + ".verticalFilmAperture", fb[1] / MM_PER_INCH)
    cmds.setAttr(s + ".filmFit", 1)          # horizontal, like the plate
    node = marker(create=True)
    cmds.setAttr(node + ".focal", float(data.focal))
    cmds.setAttr(node + ".filmbackWidth", float(fb[0]))
    cmds.setAttr(node + ".filmbackHeight", float(fb[1]))
    return t


def plate_offset(plate, start):
    """
    frameOffset so the right plate frame shows: when the scene's first frame is
    inside the plate's frame numbers they line up 1:1 (offset 0), otherwise the
    plate's first frame is put on the scene's first frame.
    """
    if start is None or plate.first <= start <= plate.last:
        return 0
    return int(plate.first - start)


def _frame_expression(ip):
    """imagePlane.frameExtension = frame (what Maya's Attribute Editor makes)."""
    plug = ip + ".frameExtension"
    if cmds.listConnections(plug, source=True, destination=False):
        return
    cmds.expression(string="%s = frame;" % plug, object="", alwaysEvaluate=True,
                    unitConversion="all", name=_unique("%s_frameExt" % ip.split("|")[-1]))


def ensure_image_plane(data, plate, start=None):
    """Put *plate* on the shot camera's image plane (creates it if needed)."""
    t, cam = camera()
    if not cam:
        t = ensure_camera(data, plate)
        t, cam = camera()
    ip = image_plane()
    path = plate.first_file
    if not ip:
        nodes = cmds.imagePlane(camera=cam, fileName=path, showInAllViews=False)
        transform = cmds.rename(nodes[0], _unique("plate_%s" % data.node_suffix))
        cmds.rename(_shape(transform, "imagePlane"), transform.split("|")[-1] + "Shape")
        ip = _shape(transform, "imagePlane")
        cmds.setAttr(ip + ".fit", 2)                 # horizontal, matches filmFit
        cmds.setAttr(ip + ".depth", FAR_CLIP * 0.5)
        cmds.setAttr(ip + ".displayOnlyIfCurrent", 1)
    else:
        cmds.setAttr(ip + ".imageName", path, type="string")
    cmds.setAttr(ip + ".useFrameExtension", 1)
    _frame_expression(ip)
    if start is None and data.frame_range:
        start = data.frame_range[0]
    cmds.setAttr(ip + ".frameOffset", plate_offset(plate, start))
    _link("imagePlane", cmds.listRelatives(ip, parent=True, fullPath=True)[0])
    _set_str("plate", plate.display_path)
    return ip


def apply_scene_settings(data, plate):
    """Render resolution from the plate, and the frame range."""
    size = plate.size() if plate else None
    if size:
        w, h, par = size
        cmds.setAttr("defaultResolution.aspectLock", 0)
        cmds.setAttr("defaultResolution.width", int(w))
        cmds.setAttr("defaultResolution.height", int(h))
        cmds.setAttr("defaultResolution.pixelAspect", float(par))
        cmds.setAttr("defaultResolution.deviceAspectRatio", float(w) * par / float(h))
    rng = data.frame_range
    if rng:
        start, end = rng
        cmds.playbackOptions(edit=True, animationStartTime=start, minTime=start,
                             animationEndTime=end, maxTime=end)
        cmds.currentTime(start)


def look_through():
    """Show the shot camera in the main perspective viewport."""
    t, _s = camera()
    if not t:
        return
    panels = cmds.getPanel(type="modelPanel") or []
    focus = cmds.getPanel(withFocus=True)
    target = focus if focus in panels else None
    if not target:
        for p in panels:
            cam = cmds.modelPanel(p, query=True, camera=True)
            if cam and cam.split("|")[-1] in ("persp", "perspShape"):
                target = p
                break
    if target:
        try:
            cmds.lookThru(target, t)
        except RuntimeError:
            pass


def build(data, version, do_camera=True, do_plate=True, do_scene=True, plate=None):
    """
    Run (part of) the setup. Returns a list of short lines describing what changed.
    One undo chunk, so Ctrl+Z takes it all back.
    """
    plate = plate or data.plate
    done = []
    cmds.undoInfo(openChunk=True, chunkName="NFA Shot Setup")
    try:
        first_time = not was_set_up()
        node = marker(create=True)
        cmds.setAttr(node + ".shotId", int(data.shot_id or 0))
        _set_str("shotCode", data.shot_code)
        _set_str("toolVersion", version)
        stamp = time.strftime("%Y-%m-%d %H:%M")
        if first_time:
            _set_str("setupAt", stamp)
            _set_str("setupBy", getpass.getuser())
        _set_str("updatedAt", stamp)

        if do_scene:
            apply_scene_settings(data, plate)
            done.append("scene settings")
        if do_camera:
            ensure_camera(data, plate)
            done.append("camera %.4g mm" % data.focal)
        if do_plate and plate:
            ensure_image_plane(data, plate)
            done.append("image plane %s" % (plate.version or plate.ext.lstrip(".")))
        if do_camera and first_time:
            look_through()
    finally:
        cmds.undoInfo(closeChunk=True)
    return done
