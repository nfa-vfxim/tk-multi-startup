"""Run: python tests/test_sg_data.py  (no Maya or ShotGrid needed)."""

import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python", "tk_multi_startup", "shot_setup"))
import sg_data  # noqa: E402


def write_exr(path, w, h, aspect=1.0):
    def attr(name, kind, data):
        return name.encode() + b"\0" + kind.encode() + b"\0" + struct.pack("<i", len(data)) + data
    head = struct.pack("<i", 20000630) + struct.pack("<i", 2)
    head += attr("dataWindow", "box2i", struct.pack("<iiii", 0, 0, w - 1, h - 1))
    head += attr("displayWindow", "box2i", struct.pack("<iiii", 0, 0, w - 1, h - 1))
    head += attr("pixelAspectRatio", "float", struct.pack("<f", aspect))
    with open(path, "wb") as fh:
        fh.write(head + b"\0")


class FakeSG(object):
    def __init__(self, shot, camera=None, pubs=()):
        self.shot, self.camera, self.pubs = shot, camera, list(pubs)

    def find_one(self, entity, filters, fields):
        return {"Shot": self.shot, "Camera": self.camera}.get(entity)

    def find(self, entity, filters, fields, **kw):
        return self.pubs if entity == "PublishedFile" else []


class Tests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def touch_seq(self, folder, head, frames, ext=".exr", size=(1920, 1080)):
        os.makedirs(folder, exist_ok=True)
        for f in frames:
            p = os.path.join(folder, "%s%04d%s" % (head, f, ext))
            if ext == ".exr":
                write_exr(p, *size)
            else:
                open(p, "wb").close()

    def test_parse_mm(self):
        self.assertEqual(sg_data.parse_mm("36"), 36.0)
        self.assertEqual(sg_data.parse_mm("24,89 mm"), 24.89)
        self.assertEqual(sg_data.parse_mm(50), 50.0)
        self.assertIsNone(sg_data.parse_mm(""))
        self.assertIsNone(sg_data.parse_mm("n/a"))
        self.assertIsNone(sg_data.parse_mm(0))

    def test_exr_size(self):
        p = os.path.join(self.root, "a.exr")
        write_exr(p, 4096, 1716, 2.0)
        self.assertEqual(sg_data.exr_size(p), (4096, 1716, 2.0))

    def test_defaults_and_plate_search(self):
        base = os.path.join(self.root, "02_source", "sc998", "0010")
        self.touch_seq(os.path.join(base, "p001", "plates", "exr"), "x_p001.", range(1001, 1011))
        self.touch_seq(os.path.join(base, "p002", "plates", "exr"), "x_p002.", range(1001, 1021), size=(3840, 2160))
        self.touch_seq(os.path.join(base, "p002", "plates", "exr", "denoise"), "x_dn.", range(1001, 1021))
        self.touch_seq(os.path.join(base, "p002", "plates", "jpg"), "x_p002.", range(1001, 1021), ext=".jpg")
        shot = {"id": 1, "code": "0010", "sg_sequence": {"name": "998"}, "sg_cut_in": None, "sg_cut_out": None}
        src = sg_data.ShotSource(FakeSG(shot), {"id": 9}, {"type": "Shot", "id": 1}, self.root)
        d = sg_data.load(src)
        self.assertEqual(d.focal, sg_data.DEFAULT_FOCAL)
        self.assertEqual(d.filmback, sg_data.DEFAULT_FILMBACK)
        self.assertFalse(d.focal_from_sg or d.filmback_from_sg)
        self.assertEqual([(p.version, p.ext) for p in d.plates], [("p002", ".exr"), ("p002", ".jpg"), ("p001", ".exr")])
        self.assertEqual(d.plate.size()[:2], (3840, 2160))
        self.assertEqual(d.frame_range, (1001, 1020))
        self.assertEqual(d.node_suffix, "998_0010")

    def test_shotgrid_values_and_shot_manager_folder(self):
        chosen = os.path.join(self.root, "elsewhere", "plates")
        self.touch_seq(chosen, "chosen.", range(1, 50))
        os.makedirs(os.path.join(self.root, ".nfa_shot_manager"))
        with open(os.path.join(self.root, ".nfa_shot_manager", "paths.json"), "w") as fh:
            json.dump({"version": 1, "shots": {"1": {"footage": os.path.dirname(chosen)}}}, fh)
        shot = {"id": 1, "code": "0010", "sg_sequence": {"name": "WFT"}, "sg_focal_length": 50,
                "sg_camera": {"type": "Camera", "id": 3, "name": "Venice"}, "sg_cut_in": 1001, "sg_cut_out": 1048}
        cam = {"code": "Venice", "sg_filmback_width": "24.89 mm", "sg_filmback_height": "18,66"}
        d = sg_data.load(sg_data.ShotSource(FakeSG(shot, cam), {"id": 9}, {"type": "Shot", "id": 1}, self.root))
        self.assertEqual((d.focal, d.filmback, d.camera_name), (50.0, (24.89, 18.66), "Venice"))
        self.assertEqual(d.plate.source, "Shot Manager footage folder")
        self.assertEqual((d.plate.first, d.plate.last), (1, 49))
        self.assertEqual(d.frame_range, (1001, 1048))

    def test_no_plate(self):
        shot = {"id": 1, "code": "0010", "sg_sequence": None}
        d = sg_data.load(sg_data.ShotSource(FakeSG(shot), {"id": 9}, {"type": "Shot", "id": 1}, self.root))
        self.assertIsNone(d.plate)
        self.assertIsNone(d.frame_range)


if __name__ == "__main__":
    unittest.main(verbosity=2)
