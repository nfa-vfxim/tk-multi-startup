# NFA Shot Setup — Changelog

## tk-multi-startup 3.0.3 — 2026-10-26 (Luuk)
- Shot Setup is only for the first setup. Once a matchmove camera from the **3D Camera Track USD Import**
  (Lucas) is in the scene, that track is leading: the window shows *Matchmove camera found*, all update
  buttons are off (no more changes to camera, plate, resolution or frame range) and **Remove shot camera**
  deletes `shotCam_…` and its plate so only the tracked camera is left (one undo step).

## tk-multi-startup 3.0.2 — 2026-10-26 (Luuk)
- The filmback height now follows the plate's aspect (width from ShotGrid or 36 mm, height = width / plate
  aspect incl. pixel aspect), so the film gate and the resolution gate line up. A 16:9 plate on a 36 mm
  filmback gives 36 × 20.25 mm; the usual 2134 × 1422 pulls stay 36 × 24 mm.

## tk-multi-startup 3.0.1 — 2026-10-25 (Luuk)
- Fix: the app failed to load on a new, unsaved scene ("Tried to extract fields from path '.'"), so Shot
  Setup never ran. The work-file fields are now skipped when there is no saved work file, and a failing
  startup setting no longer stops the app.
- Released as 3.0.0/3.0.1 (the 0.3.0 mentioned below is the same code).

## [1.1.0] — 2026-10-25 (Luuk)
- An existing work file that is still empty (and was never set up) asks once: *Create camera + plate* or
  *Not now*. The answer is remembered per file on this computer, so it never asks twice.

## [1.0.1] — 2026-10-25 (Luuk)
- The automatic setup only runs on a new, unsaved scene. Opening an existing work file (also an empty one)
  no longer creates a camera.

## [1.0.0] — 2026-10-25 (Luuk)
- First version, built into `tk-multi-startup` 0.3.0 (Maya, shot tasks).
- **Automatic setup** the first time a shot is opened through ShotGrid (an empty scene in a Shot context):
  - shot camera `shotCam_<seq>_<shot>` with the shot's **Focal Length** and the **filmback** of the
    camera linked to the shot on ShotGrid (`Shot.sg_camera` → `Camera.sg_filmback_width/height`, mm).
    Nothing filled in → Maya's defaults (35 mm, 36 × 24 mm).
  - image plane `plate_<seq>_<shot>` on that camera with the plate: Shot Manager footage folder, then
    `02_source/sc<seq>/<shot>/p###/plates/<ext>` (newest p-version, EXR first), then published plates.
    Frame numbers line up 1:1; if the scene range lies outside the plate's numbers, the plate's first
    frame is put on the first frame of the shot.
  - render resolution and pixel aspect from the plate (EXR header), frame range from ShotGrid cut in/out
    (or the plate when ShotGrid has none).
  - one undo step; marker node `NFA_shotSetup` so it never runs twice in a scene.
- **ShotGrid > Shot Setup...**: what was found vs. what is in the scene (OK / UPDATE / MISSING), choose a
  plate version, Update camera / image plane / scene settings or everything. Updates keep the camera's
  animation and the image plane's placement.
- `shot_setup_auto: false` in the tk-multi-startup config, or `NFA_SHOT_SETUP_AUTO=0` on a machine, turns the automatic part off.
