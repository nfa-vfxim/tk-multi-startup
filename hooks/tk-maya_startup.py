# MIT License

# Copyright (c) 2022 Netherlands Film Academy

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

import sgtk
import maya.cmds as cmds
import maya.mel as mel

HookBaseClass = sgtk.get_hook_baseclass()


class Startup(HookBaseClass):
    def startup(self):
        """This method will be called at the start of a new Maya session."""

        # Setting FPS
        fps = self._get_default_fps
        self._set_fps(fps)

        # Setting frame range
        frame_start = self._get_default_frame_range[0]
        frame_end = self._get_default_frame_range[1]
        self._set_frame_range(frame_start, frame_end)

        # Other settings
        self._other_settings()

    # private methods

    @staticmethod
    def _set_frame_range(frame_range_start, frame_range_end):
        """Set the Maya frame range and playback range to the input data."""

        # set the frame range to frameRangeStart - frameRangeEnd
        cmds.playbackOptions(edit=True, animationStartTime=frame_range_start)
        cmds.playbackOptions(edit=True, animationEndTime=frame_range_end)

        # set the playback range to frameRangeStart - frameRangeEnd
        cmds.playbackOptions(edit=True, minTime=frame_range_start)
        cmds.playbackOptions(edit=True, maxTime=frame_range_end)

        # set the timeline to the first frame
        cmds.currentTime(frame_range_start)

    @staticmethod
    def _set_fps(fps):
        fps = str(fps) + "fps"
        cmds.currentUnit(time=fps)

    @property
    def _get_default_fps(self):
        """Get the configured fps integer."""

        # get an instance of the app itself
        app = self.parent

        # get fps setting
        try:
            current_engine = self.parent.engine
            sg = current_engine.shotgun
            current_context = current_engine.context
            project_name = current_context.project["name"]

            fps = sg.find_one(
                "Project", [["name", "is", project_name]], ["sg_fps"]
            ).get("sg_fps")

            if fps is None:
                fps = app.get_setting("fps_default")

            return fps

        except Exception as e:
            self.logger.error(
                "An error occurred while getting the default configured frame range. Make sure the configuration for "
                "tk-maya-startup is correct. %s" % str(e)
            )

    @property
    def _get_default_frame_range(self):
        """Get the configured frame range integers."""

        # get an instance of the app itself
        app = self.parent

        # create an empty array to fill with frame range defaults
        frame_range = []

        # populate frame_range with settings
        try:
            frame_range.append(app.get_setting("frame_range_default_start"))
            frame_range.append(app.get_setting("frame_range_default_end"))
        except Exception as e:
            self.logger.error(
                "An error occurred while getting the default configured frame range. Make sure the configuration for "
                "tk-maya-startup is correct. %s" % str(e)
            )

        return frame_range

    def _other_settings(self):
        """This function is for all the extra commands that have to be executed on startup."""

        # Disable highlighting new in release
        self._eval_mel("whatsNewHighlight -highlightOn false;")

        # Disable version warning
        self._eval_mel("optionVar -intValue fileIgnoreVersion true;")

        # Set near and far clip for new created cameras
        self._eval_mel('optionVar -fv "defaultCameraNearClipValue" 10;')
        self._eval_mel('optionVar -fv "defaultCameraFarClipValue" 1000000;')

        # Keep keyframes at frame
        self._eval_mel("optionVar -intValue keepKeysAtCurrentFrame 1;")

        # Force undo to be turned on
        self._eval_mel("undoInfo -state on;")

        # Set undo limit to infinite
        self._eval_mel("undoInfo -infinity on;")

        # Play all viewers
        self._eval_mel('playbackOptions -v "all";')

        # Set Dolly tool to zoom based on location of mouse
        self._eval_mel("dollyCtx -e -dollyTowardsCenter false dollyContext;")

    def _eval_mel(self, command):
        if command:
            try:
                mel.eval(command)

            except Exception as e:
                self.logger.debug(
                    "Mel command (%s) dit not work work because: %s."
                    % (command, str(e))
                )
        else:
            self.logger.debug("No command specified.")
