"""
NFA Shot Setup — a ready shot the first time you open it.

The first time a shot is opened through ShotGrid in Maya (an empty scene in a
Shot context) this creates:
  * a shot camera with the shot's focal length and the filmback of the camera
    linked to the shot on ShotGrid (Maya's defaults when nothing is filled in)
  * an image plane on that camera with the plate (newest p-version, EXR first)
  * the render resolution of the plate and the shot's frame range
A marker node (NFA_shotSetup) makes sure it only happens once per scene.

ShotGrid > Shot Setup... shows what was found and updates the scene later.

    import nfa_shot_setup
    nfa_shot_setup.show()
"""

import os
import traceback

from . import scene, sg_data

__version__ = "1.3.0"
__author__ = "Luuk Kamphuis"

HERE = os.path.dirname(os.path.abspath(__file__))
HELP_PATH = os.path.join(HERE, "HELP.html")
CHANGELOG_PATH = os.path.join(HERE, "CHANGELOG.md")

_WINDOW = None
_RUNNING = False


def _log(text, warning=False):
    import maya.cmds as cmds
    if warning:
        cmds.warning("[NFA Shot Setup] %s" % text)
    else:
        print("[NFA Shot Setup] %s" % text)


def _engine():
    try:
        import sgtk
    except ImportError:
        return None
    return sgtk.platform.current_engine()


def current_source():
    """ShotSource for the running engine, or raise sg_data.NotAvailable."""
    engine = _engine()
    if engine is None:
        raise sg_data.NotAvailable(
            "ShotGrid is not running in this Maya.\n\n"
            "Start Maya from ShotGrid Desktop and open your shot through ShotGrid > File Open."
        )
    return sg_data.ShotSource.from_engine(engine)


# --------------------------------------------------------------------------- automatic setup
def auto_enabled():
    return os.environ.get("NFA_SHOT_SETUP_AUTO", "1").strip().lower() not in ("0", "false", "off", "no")


ASKED_OPTIONVAR = "nfaShotSetupAsked"


def auto_mode():
    """
    'auto' -> new, unsaved, empty shot scene: set it up without asking.
    'ask'  -> a saved work file that is empty and was never set up: ask once.
    None   -> leave the scene alone.
    """
    import maya.cmds as cmds
    if not auto_enabled() or cmds.about(batch=True):
        return None
    engine = _engine()
    entity = engine.context.entity if engine else None
    if not entity or entity.get("type") != "Shot":
        return None
    if scene.was_set_up() or not scene.is_empty_scene():
        return None
    path = cmds.file(query=True, sceneName=True)
    if not path:
        return "auto"
    return None if _was_asked(path) else "ask"


def should_auto_setup():
    return auto_mode() is not None


def _asked_list():
    import maya.cmds as cmds
    if not cmds.optionVar(exists=ASKED_OPTIONVAR):
        return []
    v = cmds.optionVar(query=ASKED_OPTIONVAR)
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _norm(path):
    return os.path.normcase(os.path.normpath(path))


def _was_asked(path):
    return _norm(path) in [_norm(p) for p in _asked_list() if p]


def _remember_asked(path):
    import maya.cmds as cmds
    cmds.optionVar(stringValueAppend=(ASKED_OPTIONVAR, path))
    # Keep the list short
    items = _asked_list()
    if len(items) > 500:
        cmds.optionVar(remove=ASKED_OPTIONVAR)
        for p in items[-400:]:
            cmds.optionVar(stringValueAppend=(ASKED_OPTIONVAR, p))


def _ask(path):
    """Yes/No: set up this empty work file? Asked once per file."""
    from . import dialog
    box = dialog.QtWidgets.QMessageBox(dialog.maya_main_window())
    box.setWindowTitle("NFA Shot Setup")
    box.setIcon(dialog.QtWidgets.QMessageBox.Question)
    box.setText("This shot scene is empty.\n\nCreate the shot camera and the plate (backplate) now?")
    box.setInformativeText("You won't be asked again for this file. You can always do it later with "
                           "ShotGrid > Shot Setup...")
    yes = box.addButton("Create camera + plate", dialog.QtWidgets.QMessageBox.AcceptRole)
    box.addButton("Not now", dialog.QtWidgets.QMessageBox.RejectRole)
    box.setDefaultButton(yes)
    dialog._exec(box)
    _remember_asked(path)
    return box.clickedButton() is yes


def auto_setup():
    """Set up a fresh shot scene (or ask, for an empty saved file). Never raises."""
    global _RUNNING
    if _RUNNING:
        return None
    _RUNNING = True
    try:
        import maya.cmds as cmds
        mode = auto_mode()
        if mode is None:
            return None
        if mode == "ask" and not _ask(cmds.file(query=True, sceneName=True)):
            return None
        data = sg_data.load(current_source())
        done = scene.build(data, __version__)
        _log("Set up shot %s: %s" % (data.shot_code, ", ".join(done)))
        _toast("Shot Setup: camera %.4g mm%s" % (
            data.focal, (" + plate " + (data.plate.version or "")) if data.plate else " (no plate found)"))
        if mode == "auto":
            # A freshly set-up new scene shouldn't ask to be saved before anyone touched it
            cmds.file(modified=False)
        return done
    except Exception:
        _log("Automatic setup failed:\n%s" % traceback.format_exc(), warning=True)
        return None
    finally:
        _RUNNING = False


def schedule_auto_setup():
    """Wait until Maya (and Workfiles) are done with the scene, then check."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return
    cmds.evalDeferred(auto_setup, lowestPriority=True)


def _toast(text):
    try:
        import maya.cmds as cmds
        cmds.inViewMessage(assistMessage=text, position="topCenter", fade=True, fadeStayTime=3500)
    except Exception:
        pass


# --------------------------------------------------------------------------- window
def show():
    global _WINDOW
    from . import dialog
    try:
        src = current_source()
    except sg_data.NotAvailable as e:
        dialog.message("NFA Shot Setup", str(e), error=True)
        return None
    try:
        if _WINDOW is not None:
            _WINDOW.close()
            _WINDOW.deleteLater()
    except Exception:
        pass
    _WINDOW = dialog.ShotSetupDialog(src, __version__, __author__)
    _WINDOW.show()
    _WINDOW.raise_()
    return _WINDOW
