# MIT License

# Copyright (c) 2023 Netherlands Film Academy

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os

import sgtk


class TkMultiStartup(sgtk.platform.Application):
    def init_app(self):
        """Initialise the app."""
        startup = self.import_module("tk_multi_startup")
        self._shot_setup = None
        self._new_scene_job = None

        startup.Handler(self)

        if self.engine.name == "tk-maya":
            # Imported only in Maya: it needs maya.cmds
            import importlib

            self._init_shot_setup(importlib.import_module(startup.__name__ + ".shot_setup"))

    # ---- NFA Shot Setup (Maya): shot camera + plate image plane on first open
    def _init_shot_setup(self, shot_setup):
        self._shot_setup = shot_setup
        menu_name = self.get_setting("shot_setup_menu_name")
        if menu_name and self.context.entity and self.context.entity.get("type") == "Shot":
            self.engine.register_command(
                "%s..." % menu_name,
                shot_setup.show,
                {
                    "short_name": "shot_setup",
                    "description": "Shot camera with the right focal length, plate on an image plane",
                    "icons": {"dark": {"png": os.path.join(
                        os.path.dirname(shot_setup.__file__), "icon_256.png")}},
                },
            )
        if not self.get_setting("shot_setup_auto"):
            return
        # Engine start or a new environment: check once Maya is idle
        shot_setup.schedule_auto_setup()
        # File > New inside Maya while in this shot
        try:
            import maya.cmds as cmds

            if not cmds.about(batch=True):
                self._new_scene_job = cmds.scriptJob(
                    event=["NewSceneOpened", shot_setup.schedule_auto_setup]
                )
        except Exception as e:
            self.logger.debug("Shot Setup: no NewSceneOpened job: %s" % e)

    def post_context_change(self, old_context, new_context):
        # Workfiles New/Open into another shot reuses this app (init_app doesn't
        # run again), so check the scene for Shot Setup here.
        if self._shot_setup and self.get_setting("shot_setup_auto"):
            self._shot_setup.schedule_auto_setup()

    def destroy_app(self):
        if self._new_scene_job:
            try:
                import maya.cmds as cmds

                if cmds.scriptJob(exists=self._new_scene_job):
                    cmds.scriptJob(kill=self._new_scene_job, force=True)
            except Exception:
                pass
            self._new_scene_job = None
