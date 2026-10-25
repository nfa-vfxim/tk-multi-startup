"""
Everything Shot Setup reads: the shot's lens and camera from ShotGrid and the
plate on disk. No Maya imports here, so it can be tested outside Maya.

ShotGrid fields used:
    Shot.sg_focal_length              number (mm)
    Shot.sg_camera                    -> Camera
    Camera.sg_filmback_width/_height  text (mm, "36", "36 mm" and "36,0" all work)
    Shot.sg_cut_in / sg_cut_out       frame range
Nothing filled in -> Maya's defaults (35 mm lens, 36 x 24 mm filmback).
"""

import glob
import json
import os
import re
import struct

DEFAULT_FOCAL = 35.0
DEFAULT_FILMBACK = (36.0, 24.0)      # Maya's own default (1.417 x 0.945 inch)

PLATE_EXT = (".exr", ".dpx", ".tif", ".tiff", ".png", ".jpg", ".jpeg")
# Preferred plate format when a version has several (exr wins)
EXT_RANK = {".exr": 0, ".dpx": 1, ".tif": 2, ".tiff": 2, ".png": 3, ".jpg": 4, ".jpeg": 4}
# Plate folders that are not the plate itself
SKIP_DIRS = {"denoise", "denoised", "undistort", "undistorted", "exports", "3de", "ref", "proxy", "thumbs"}
FOOTAGE_TYPE_MARKERS = ("plate", "footage", "image", "scan")

SHOT_FIELDS = ["code", "sg_sequence", "sg_focal_length", "sg_camera", "sg_cut_in", "sg_cut_out",
               "sg_head_in", "sg_tail_out", "sg_resolution"]
CAMERA_FIELDS = ["code", "sg_filmback_width", "sg_filmback_height"]

_FRAME_RE = re.compile(r"^(?P<head>.*?)(?P<frame>\d+)(?P<ext>\.[A-Za-z0-9]+)$")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


class NotAvailable(Exception):
    """Shot Setup can't run here; the message is shown to the artist."""


# --------------------------------------------------------------------------- small helpers
def natural_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(text or ""))]


def parse_mm(value):
    """'36', '36 mm', '36,0', 36 -> 36.0. Empty / unreadable / <= 0 -> None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    m = _NUMBER_RE.search(str(value))
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", "."))
    except ValueError:
        return None
    return v if v > 0 else None


def sequence_name(shot):
    seq = shot.get("sg_sequence") or {}
    return seq.get("name") or seq.get("code") or ""


def sequence_folder_names(seq):
    """'WFT' and 'scWFT' (and '0040' / 'sc0040') both occur on disk."""
    names = [seq]
    if re.match(r"^sc(?=[A-Z0-9])", seq):
        names.append(seq[2:])
    else:
        names.append("sc" + seq)
    return [n for n in dict.fromkeys(names) if n]


# --------------------------------------------------------------------------- plates
class Plate(object):
    """One image sequence on disk."""

    def __init__(self, folder, head, ext, padding, frames, source, version=None):
        self.folder = folder
        self.head = head              # 'p27451_sc998_0010_plate_p001.'
        self.ext = ext                # '.exr'
        self.padding = padding
        self.frames = sorted(frames)
        self.source = source          # where it was found, shown in the dialog
        self.version = version        # 'p001' or None
        self._size = None

    @property
    def first(self):
        return self.frames[0]

    @property
    def last(self):
        return self.frames[-1]

    @property
    def count(self):
        return len(self.frames)

    def frame_path(self, frame):
        name = "%s%0*d%s" % (self.head, self.padding, frame, self.ext)
        return os.path.join(self.folder, name).replace("\\", "/")

    @property
    def first_file(self):
        return self.frame_path(self.first)

    @property
    def display_path(self):
        return os.path.join(self.folder, "%s%s%s" % (self.head, "#" * self.padding, self.ext)).replace("\\", "/")

    @property
    def label(self):
        v = (self.version + " · ") if self.version else ""
        return "%s%s  (%d-%d, %d frames)" % (v, self.ext.lstrip(".").upper(), self.first, self.last, self.count)

    def size(self):
        """(width, height, pixel_aspect) of the first frame, or None."""
        if self._size is None:
            self._size = image_size(self.first_file) or False
        return self._size or None

    def key(self):
        return os.path.normcase(os.path.normpath(self.display_path))

    def __repr__(self):
        return "Plate(%s, %s)" % (self.display_path, self.source)


def sequences_in(folder, source, version=None):
    """All image sequences directly inside *folder* (largest first)."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    groups = {}
    for n in names:
        m = _FRAME_RE.match(n)
        if not m:
            continue
        ext = m.group("ext").lower()
        if ext not in PLATE_EXT:
            continue
        key = (m.group("head"), m.group("ext"), len(m.group("frame")))
        groups.setdefault(key, []).append(int(m.group("frame")))
    out = []
    for (head, ext, pad), frames in groups.items():
        if len(frames) < 2 and not head:
            continue
        out.append(Plate(folder, head, ext, pad, frames, source, version))
    out.sort(key=lambda p: (-p.count, EXT_RANK.get(p.ext.lower(), 9)))
    return out


def sequences_below(folder, source, max_depth=4):
    """Image sequences up to *max_depth* folders deep, skipping helper folders."""
    found = []
    base_depth = folder.rstrip("\\/").count(os.sep)
    for dirpath, dirnames, _files in os.walk(folder):
        depth = dirpath.rstrip("\\/").count(os.sep) - base_depth
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith(".")]
        if depth >= max_depth:
            dirnames[:] = []
        found += sequences_in(dirpath, source)
    found.sort(key=lambda p: (EXT_RANK.get(p.ext.lower(), 9), -p.count))
    return found


def image_size(path):
    """(width, height, pixel_aspect) for EXR (header) or other formats (Qt), else None."""
    if path.lower().endswith(".exr"):
        try:
            return exr_size(path)
        except Exception:
            return None
    try:
        try:
            from PySide6 import QtGui
        except ImportError:
            from PySide2 import QtGui
        reader = QtGui.QImageReader(path)
        s = reader.size()
        if s.isValid() and s.width() > 0:
            return s.width(), s.height(), 1.0
    except Exception:
        pass
    return None


def exr_size(path):
    """Read displayWindow and pixelAspectRatio from an OpenEXR header."""
    with open(path, "rb") as fh:
        if struct.unpack("<i", fh.read(4))[0] != 20000630:
            return None
        fh.read(4)  # version / flags
        display = data = None
        aspect = 1.0
        for _ in range(500):
            name = _read_cstr(fh)
            if not name:
                break
            atype = _read_cstr(fh)
            size = struct.unpack("<i", fh.read(4))[0]
            raw = fh.read(size)
            if atype == "box2i" and name in ("displayWindow", "dataWindow"):
                x0, y0, x1, y1 = struct.unpack("<iiii", raw)
                if name == "displayWindow":
                    display = (x1 - x0 + 1, y1 - y0 + 1)
                else:
                    data = (x1 - x0 + 1, y1 - y0 + 1)
            elif name == "pixelAspectRatio" and atype == "float":
                aspect = struct.unpack("<f", raw)[0] or 1.0
        wh = display or data
        if not wh:
            return None
        return wh[0], wh[1], round(float(aspect), 4)


def _read_cstr(fh, limit=256):
    out = b""
    while len(out) < limit:
        c = fh.read(1)
        if not c or c == b"\0":
            break
        out += c
    return out.decode("ascii", "replace")


# --------------------------------------------------------------------------- shot source
class ShotSource(object):
    """
    The bits of a Toolkit context Shot Setup needs. Built from the engine in
    Maya (from_engine) or by hand in tests.
    """

    def __init__(self, sg, project, shot, root, tk=None, project_code=""):
        self.sg = sg
        self.project = project
        self.shot = shot            # {'type': 'Shot', 'id': ..}
        self.root = root            # project root on disk
        self.tk = tk
        self.project_code = project_code

    @classmethod
    def from_engine(cls, engine):
        ctx = engine.context
        entity = ctx.entity
        if not entity or entity.get("type") != "Shot":
            where = entity.get("type").lower() if entity else "a project without a shot"
            raise NotAvailable(
                "Shot Setup only works inside a shot.\n\n"
                "Maya is currently in %s. Open your shot through ShotGrid > File Open and try again." % where
            )
        tk = engine.sgtk
        roots = getattr(tk, "roots", None) or {}
        root = roots.get("primary") or next(iter(roots.values()), None)
        code = ""
        try:
            p = engine.shotgun.find_one("Project", [["id", "is", ctx.project["id"]]], ["sg_projectcode"])
            code = (p or {}).get("sg_projectcode") or ""
        except Exception:
            pass
        return cls(engine.shotgun, ctx.project, entity, root, tk=tk, project_code=code)


class ShotData(object):
    """What the shot should look like in Maya."""

    def __init__(self):
        self.shot_id = None
        self.shot_code = ""
        self.sequence = ""
        self.focal = DEFAULT_FOCAL
        self.focal_from_sg = False
        self.camera_name = ""
        self.filmback = DEFAULT_FILMBACK
        self.filmback_from_sg = False
        self.cut_in = None
        self.cut_out = None
        self.plates = []            # candidates, best first
        self.plate = None           # chosen one

    @property
    def node_suffix(self):
        """Valid Maya name part, e.g. '998_0010' (the caller adds a prefix, names can't start with a digit)."""
        raw = "%s_%s" % (self.sequence, self.shot_code) if self.sequence else self.shot_code
        return re.sub(r"[^A-Za-z0-9_]", "_", raw)

    @property
    def frame_range(self):
        """(start, end) from ShotGrid, else from the plate, else None."""
        if self.cut_in is not None and self.cut_out is not None and self.cut_out >= self.cut_in:
            return int(self.cut_in), int(self.cut_out)
        if self.plate:
            return self.plate.first, self.plate.last
        return None


def load(src):
    """Read the shot from ShotGrid and find its plates. Returns ShotData."""
    d = ShotData()
    shot = src.sg.find_one("Shot", [["id", "is", src.shot["id"]]], SHOT_FIELDS) or {}
    d.shot_id = src.shot["id"]
    d.shot_code = shot.get("code") or src.shot.get("name") or ""
    d.sequence = sequence_name(shot)
    d.cut_in = shot.get("sg_cut_in")
    d.cut_out = shot.get("sg_cut_out")

    focal = parse_mm(shot.get("sg_focal_length"))
    if focal:
        d.focal, d.focal_from_sg = focal, True

    cam = shot.get("sg_camera")
    if cam and cam.get("id"):
        row = src.sg.find_one("Camera", [["id", "is", cam["id"]]], CAMERA_FIELDS) or {}
        d.camera_name = row.get("code") or cam.get("name") or ""
        w, h = parse_mm(row.get("sg_filmback_width")), parse_mm(row.get("sg_filmback_height"))
        if w and h:
            d.filmback, d.filmback_from_sg = (w, h), True
        elif w:
            # Only a width: keep Maya's default aspect
            d.filmback, d.filmback_from_sg = (w, w * DEFAULT_FILMBACK[1] / DEFAULT_FILMBACK[0]), True

    d.plates = find_plates(src, shot or src.shot, d.sequence, d.shot_code)
    d.plate = d.plates[0] if d.plates else None
    return d


# --------------------------------------------------------------------------- plate search
def find_plates(src, shot, seq, code):
    """
    Plate candidates, best first:
      1. the footage folder chosen in Shot Manager (.nfa_shot_manager/paths.json)
      2. 02_source/sc<seq>/<shot>/p###/plates/<ext>/  (newest p-version first, EXR first)
      3. published plates on ShotGrid
    """
    out, seen = [], set()

    def add(plates):
        for p in plates:
            if p.key() not in seen:
                seen.add(p.key())
                out.append(p)

    add(_shot_manager_plates(src, shot, seq, code))
    add(_source_plates(src, seq, code))
    add(_published_plates(src, shot))
    return out


def _shot_manager_plates(src, shot, seq, code):
    if not src.root:
        return []
    record = os.path.join(src.root, ".nfa_shot_manager", "paths.json")
    try:
        with open(record) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    folders = []
    entry = (data.get("shots") or {}).get(str(shot.get("id"))) or {}
    if entry.get("footage"):
        folders.append(entry["footage"])
    proj = (data.get("project") or {}).get("footage")
    if proj:
        for s in sequence_folder_names(seq):
            folders.append(os.path.join(proj, s, code))
    plates = []
    for f in folders:
        if os.path.isdir(f):
            plates += sequences_below(f, "Shot Manager footage folder")
        if plates:
            break
    return plates


def _source_plates(src, seq, code):
    if not src.root:
        return []
    version_dirs = []
    for s in sequence_folder_names(seq):
        version_dirs += glob.glob(os.path.join(src.root, "02_source", s, code, "p[0-9]*"))
    version_dirs = sorted(set(d for d in version_dirs if os.path.isdir(d)),
                          key=lambda d: natural_key(os.path.basename(d)), reverse=True)
    plates = []
    for vdir in version_dirs:
        version = os.path.basename(vdir)
        here = []
        for fmt_dir in glob.glob(os.path.join(vdir, "plates", "*")):
            if os.path.basename(fmt_dir).lower() in SKIP_DIRS or not os.path.isdir(fmt_dir):
                continue
            here += sequences_in(fmt_dir, "02_source", version)
        here.sort(key=lambda p: (EXT_RANK.get(p.ext.lower(), 9), -p.count))
        plates += here
    return plates


def _published_plates(src, shot):
    try:
        pubs = src.sg.find(
            "PublishedFile", [["entity", "is", {"type": "Shot", "id": shot["id"]}]],
            ["code", "published_file_type", "path", "created_at"],
            order=[{"field_name": "created_at", "direction": "desc"}], limit=50)
    except Exception:
        return []
    plates = []
    for pub in pubs:
        ptype = ((pub.get("published_file_type") or {}).get("name") or "").lower()
        if not any(m in ptype for m in FOOTAGE_TYPE_MARKERS):
            continue
        path = (pub.get("path") or {}).get("local_path") or ""
        if not path.lower().endswith(PLATE_EXT):
            continue
        folder = os.path.dirname(path)
        if os.path.isdir(folder):
            plates += sequences_in(folder, "ShotGrid publish")
    return plates
