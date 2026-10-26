"""
ShotGrid > Shot Setup... — what Shot Setup found for this shot next to what is
in the scene, with buttons to bring the scene up to date. Same dark look as
Shot Context and the Review tool's preview.
"""

import os
import webbrowser

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

from . import scene, sg_data

BG = "#1b1c1f"
CARD = "#25272b"
PANEL = "#2f3237"
BORDER = "#34373d"
TEXT = "#e6e7ea"
DIM = "#8b8f98"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#5a97f8"
ACCENT_PRESSED = "#2f6ad0"
GREEN, AMBER, RED = "#4ade80", "#fbbf24", "#f87171"

STYLE = """
QDialog#ShotSetup {{ background-color: {bg}; }}
QDialog#ShotSetup QLabel {{ color: {text}; background: transparent; }}
QDialog#ShotSetup QLabel#Title {{ font-size: 16px; font-weight: 600; }}
QDialog#ShotSetup QLabel#Section {{ font-size: 13px; font-weight: 600; }}
QDialog#ShotSetup QLabel#Muted, QDialog#ShotSetup QLabel#Key {{ color: {muted}; }}
QDialog#ShotSetup QLabel#Foot {{ color: {muted}; font-size: 11px; }}
QDialog#ShotSetup QLabel#Chip {{
    border-radius: 9px; padding: 1px 9px; font-size: 11px; font-weight: 600; color: #111;
}}
QFrame#Card, QFrame#Footer {{
    background-color: {surface}; border: 1px solid {border}; border-radius: 10px;
}}
QPushButton#SecondaryButton, QPushButton#GhostButton {{
    color: {text}; background-color: transparent; border: 1px solid {border};
    border-radius: 8px; padding: 7px 14px; font-weight: 500;
}}
QPushButton#SecondaryButton:hover, QPushButton#GhostButton:hover {{ background-color: {surface_hover}; }}
QPushButton#SecondaryButton:disabled {{ color: {muted}; }}
QPushButton#GhostButton {{ padding: 4px 10px; }}
QPushButton#PrimaryButton {{
    color: #ffffff; background-color: {accent}; border: none; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background-color: {accent_hover}; }}
QPushButton#PrimaryButton:pressed {{ background-color: {accent_pressed}; }}
QComboBox {{
    color: {text}; background-color: {bg}; border: 1px solid {border}; border-radius: 6px;
    padding: 4px 8px; min-height: 20px;
}}
QComboBox QAbstractItemView {{
    color: {text}; background-color: {surface}; selection-background-color: {accent};
    border: 1px solid {border};
}}
QTextBrowser {{ color: {text}; background-color: {surface}; border: 1px solid {border}; border-radius: 8px; }}
""".format(bg=BG, text=TEXT, muted=DIM, surface=CARD, surface_hover=PANEL, border=BORDER,
           accent=ACCENT, accent_hover=ACCENT_HOVER, accent_pressed=ACCENT_PRESSED)

OK, UPDATE, MISSING = "OK", "UPDATE", "MISSING"
CHIP_COLOURS = {OK: GREEN, UPDATE: AMBER, MISSING: RED, "NONE": DIM}


def maya_main_window():
    try:
        from maya import OpenMayaUI
        try:
            from shiboken6 import wrapInstance
        except ImportError:
            from shiboken2 import wrapInstance
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None
    except Exception:
        return None


def _exec(dlg):
    return dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()


def message(title, text, error=False):
    box = QtWidgets.QMessageBox(maya_main_window())
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QtWidgets.QMessageBox.Warning if error else QtWidgets.QMessageBox.Information)
    _exec(box)


def _mm(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def _same(a, b, tol=0.01):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def _norm(path):
    return os.path.normcase(os.path.normpath(path or "")).replace("\\", "/")


class ShotSetupDialog(QtWidgets.QDialog):
    def __init__(self, src, version, author, parent=None):
        super(ShotSetupDialog, self).__init__(parent or maya_main_window())
        self.src = src
        self.version = version
        self.setObjectName("ShotSetup")
        self.setWindowTitle("NFA Shot Setup")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setStyleSheet(STYLE)
        self.setMinimumWidth(640)
        self.data = None

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        head = QtWidgets.QHBoxLayout()
        titles = QtWidgets.QVBoxLayout()
        titles.setSpacing(0)
        self.title = QtWidgets.QLabel("Shot Setup")
        self.title.setObjectName("Title")
        self.subtitle = QtWidgets.QLabel("")
        self.subtitle.setObjectName("Muted")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles, 1)
        for text, slot in (("Reload", self.reload), ("Help", self.open_help), ("Changelog", self.open_changelog)):
            b = self._button(text, "GhostButton", slot)
            head.addWidget(b, 0, QtCore.Qt.AlignTop)
        root.addLayout(head)

        # Camera
        self.cam_card, cam, head = self._card("Camera")
        self.cam_chip = self._chip_label()
        head.addWidget(self.cam_chip)
        self.focal_lbl = self._row(cam, 0, "Focal length")
        self.filmback_lbl = self._row(cam, 1, "Filmback")
        self.cam_scene_lbl = self._row(cam, 2, "In scene")
        self.cam_btn = self._button("Update camera", "SecondaryButton", self.update_camera)
        cam.addWidget(self.cam_btn, 3, 1, QtCore.Qt.AlignLeft)
        root.addWidget(self.cam_card)

        # Plate
        self.plate_card, pl, head = self._card("Plate")
        self.plate_chip = self._chip_label()
        head.addWidget(self.plate_chip)
        key = QtWidgets.QLabel("Plate")
        key.setObjectName("Key")
        self.plate_combo = QtWidgets.QComboBox()
        self.plate_combo.currentIndexChanged.connect(self._refresh_status)
        pl.addWidget(key, 0, 0)
        pl.addWidget(self.plate_combo, 0, 1)
        self.plate_path_lbl = self._row(pl, 1, "Path")
        self.plate_info_lbl = self._row(pl, 2, "Image")
        self.plate_scene_lbl = self._row(pl, 3, "In scene")
        self.plate_btn = self._button("Update image plane", "SecondaryButton", self.update_plate)
        pl.addWidget(self.plate_btn, 4, 1, QtCore.Qt.AlignLeft)
        root.addWidget(self.plate_card)

        # Scene
        self.scene_card, sc, head = self._card("Scene")
        self.scene_chip = self._chip_label()
        head.addWidget(self.scene_chip)
        self.range_lbl = self._row(sc, 0, "Frame range")
        self.res_lbl = self._row(sc, 1, "Resolution")
        self.scene_btn = self._button("Update scene settings", "SecondaryButton", self.update_scene)
        sc.addWidget(self.scene_btn, 2, 1, QtCore.Qt.AlignLeft)
        root.addWidget(self.scene_card)

        # Footer
        footer = QtWidgets.QFrame()
        footer.setObjectName("Footer")
        foot = QtWidgets.QHBoxLayout(footer)
        foot.setContentsMargins(16, 10, 10, 10)
        info = QtWidgets.QVBoxLayout()
        info.setSpacing(2)
        self.status = QtWidgets.QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        credit = QtWidgets.QLabel("v%s · %s" % (version, author))
        credit.setObjectName("Foot")
        info.addWidget(self.status)
        info.addWidget(credit)
        foot.addLayout(info, 1)
        self.all_btn = self._button("Set up shot", "PrimaryButton", self.update_all)
        foot.addWidget(self.all_btn)
        foot.addWidget(self._button("Close", "SecondaryButton", self.close))
        root.addWidget(footer)

        self.reload()

    # ------------------------------------------------------------------ widgets
    def _button(self, text, name, slot):
        b = QtWidgets.QPushButton(text)
        b.setObjectName(name)
        b.setAutoDefault(False)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _chip_label(self):
        lbl = QtWidgets.QLabel("")
        lbl.setObjectName("Chip")
        return lbl

    def _set_chip(self, lbl, state, tip=""):
        lbl.setText(state)
        lbl.setToolTip(tip)
        lbl.setStyleSheet("background-color: %s;" % CHIP_COLOURS.get(state, DIM))

    def _card(self, title):
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        outer = QtWidgets.QVBoxLayout(card)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(8)
        head = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(title)
        lbl.setObjectName("Section")
        head.addWidget(lbl)
        head.addStretch(1)
        outer.addLayout(head)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        outer.addLayout(grid)
        return card, grid, head

    def _row(self, grid, row, key):
        k = QtWidgets.QLabel(key)
        k.setObjectName("Key")
        v = QtWidgets.QLabel("")
        v.setWordWrap(True)
        v.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        grid.addWidget(k, row, 0, QtCore.Qt.AlignTop)
        grid.addWidget(v, row, 1)
        return v

    # ------------------------------------------------------------------ data
    def reload(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.data = sg_data.load(self.src)
        except Exception as e:
            QtWidgets.QApplication.restoreOverrideCursor()
            message("NFA Shot Setup", "Could not read the shot from ShotGrid:\n\n%s" % e, error=True)
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        d = self.data
        self.subtitle.setText("%s  ·  shot %s" % (("Sequence " + d.sequence) if d.sequence else "", d.shot_code))

        self.focal_lbl.setText("%s mm  %s" % (_mm(d.focal), "(ShotGrid)" if d.focal_from_sg else "(default)"))

        self.plate_combo.blockSignals(True)
        self.plate_combo.clear()
        for p in d.plates:
            self.plate_combo.addItem("%s  —  %s" % (p.label, p.source), p)
        if not d.plates:
            self.plate_combo.addItem("No plate found", None)
        self.plate_combo.setEnabled(bool(d.plates))
        self.plate_combo.blockSignals(False)
        self._refresh_status()

    def selected_plate(self):
        return self.plate_combo.currentData() if self.plate_combo.count() else None

    def _refresh_status(self, *_):
        d = self.data
        if d is None:
            return
        st = scene.state()
        want = d.camera_filmback(self.selected_plate())

        # Filmback: width from ShotGrid (or default), height from the plate aspect
        fb_txt = "%s × %s mm" % (_mm(want[0]), _mm(want[1]))
        if d.filmback_from_sg:
            fb_txt += "  (width from camera %s" % (d.camera_name or "on ShotGrid")
        elif d.camera_name:
            fb_txt += "  (default width, camera %s has no filmback" % d.camera_name
        else:
            fb_txt += "  (default width"
        fb_txt += ", height from the plate)" if not _same(want[1], d.filmback[1]) else ")"
        self.filmback_lbl.setText(fb_txt)

        # Camera
        if not st["camera"]:
            self.cam_scene_lbl.setText("No shot camera yet")
            self._set_chip(self.cam_chip, MISSING)
        else:
            fb = st["filmback"] or (0, 0)
            self.cam_scene_lbl.setText("%s  ·  %s mm  ·  %s × %s mm" % (
                st["camera"].split("|")[-1], _mm(st["focal"]), _mm(fb[0]), _mm(fb[1])))
            ok = (_same(st["focal"], d.focal) and _same(fb[0], want[0]) and _same(fb[1], want[1]))
            self._set_chip(self.cam_chip, OK if ok else UPDATE,
                           "" if ok else "The camera's lens differs from ShotGrid")

        # Plate
        plate = self.selected_plate()
        if plate:
            self.plate_path_lbl.setText(plate.display_path)
            size = plate.size()
            self.plate_info_lbl.setText(
                ("%d × %d%s" % (size[0], size[1], ("  ·  pixel aspect %g" % size[2]) if size[2] != 1 else "")
                 if size else "size unknown") + "  ·  frames %d-%d" % (plate.first, plate.last))
        else:
            self.plate_path_lbl.setText("Nothing in 02_source, the Shot Manager footage folder or the "
                                        "shot's ShotGrid publishes.")
            self.plate_info_lbl.setText("")
        if not st["image_plane"]:
            self.plate_scene_lbl.setText("No image plane yet")
            self._set_chip(self.plate_chip, MISSING if plate else "NONE")
            if not plate:
                self.plate_chip.setText("NO PLATE")
        else:
            current = st["plate"] or ""
            self.plate_scene_lbl.setText("%s  ·  frame offset %d" % (current, st["offset"] or 0))
            ok = bool(plate) and _norm(current) == _norm(plate.first_file)
            self._set_chip(self.plate_chip, OK if ok else (UPDATE if plate else "NONE"))
        self.plate_btn.setEnabled(bool(plate))

        # Scene
        import maya.cmds as cmds
        rng = d.frame_range
        now = (int(cmds.playbackOptions(q=True, min=True)), int(cmds.playbackOptions(q=True, max=True)))
        src = "ShotGrid cut in/out" if (d.cut_in is not None and d.cut_out is not None) else "plate"
        self.range_lbl.setText(("%d-%d (%s)" % (rng[0], rng[1], src) if rng else "not on ShotGrid, no plate")
                               + "  ·  scene %d-%d" % now)
        size = plate.size() if plate else None
        res_now = (cmds.getAttr("defaultResolution.width"), cmds.getAttr("defaultResolution.height"))
        self.res_lbl.setText(("%d × %d from the plate" % size[:2] if size else "from the plate (no plate)")
                             + "  ·  scene %d × %d" % res_now)
        ok = (not rng or tuple(rng) == now) and (not size or tuple(size[:2]) == tuple(res_now))
        self._set_chip(self.scene_chip, OK if ok else UPDATE)

        self.all_btn.setText("Update shot" if st["marker"] else "Set up shot")
        if st["marker"]:
            self.status.setText("Set up before in this scene. Updates keep your camera animation and "
                                "image plane placement.")
        else:
            self.status.setText("This scene hasn't been set up yet.")

    # ------------------------------------------------------------------ actions
    def _run(self, **parts):
        import maya.cmds as cmds
        try:
            done = scene.build(self.data, self.version, plate=self.selected_plate(), **parts)
        except Exception as e:
            message("NFA Shot Setup", "Something went wrong:\n\n%s" % e, error=True)
            return
        self._refresh_status()
        self.status.setText("Updated: %s. Ctrl+Z undoes it." % ", ".join(done))
        cmds.refresh()

    def update_camera(self):
        self._run(do_camera=True, do_plate=False, do_scene=False)

    def update_plate(self):
        self._run(do_camera=False, do_plate=True, do_scene=False)

    def update_scene(self):
        self._run(do_camera=False, do_plate=False, do_scene=True)

    def update_all(self):
        self._run(do_camera=True, do_plate=True, do_scene=True)

    def open_help(self):
        from . import HELP_PATH
        webbrowser.open("file:///" + HELP_PATH.replace("\\", "/"))

    def open_changelog(self):
        from . import CHANGELOG_PATH
        dlg = QtWidgets.QDialog(self)
        dlg.setObjectName("ShotSetup")
        dlg.setStyleSheet(STYLE)
        dlg.setWindowTitle("NFA Shot Setup · Changelog")
        dlg.resize(620, 480)
        lay = QtWidgets.QVBoxLayout(dlg)
        view = QtWidgets.QTextBrowser()
        try:
            with open(CHANGELOG_PATH, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            text = "Changelog not found."
        if hasattr(view, "setMarkdown"):
            view.setMarkdown(text)
        else:
            view.setPlainText(text)
        lay.addWidget(view)
        _exec(dlg)
