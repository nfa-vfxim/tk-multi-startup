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

import maya.cmds as cmds
import maya.mel as mel

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class Helper(HookBaseClass):
    """
    Helper hook implementation for the tk-houdini engine.
    """

    def get_file_path(self):
        """
        Get the file path of the currently opened file
        """
        return cmds.file(q=True, sn=True)

    def set_frame_range(self, frame_range_start, frame_range_end):
        """Set the Houdini frame range and playback range to the input data."""

        # set the frame range to frameRangeStart - frameRangeEnd
        cmds.playbackOptions(edit=True, animationStartTime=frame_range_start)
        cmds.playbackOptions(edit=True, animationEndTime=frame_range_end)

        # set the playback range to frameRangeStart - frameRangeEnd
        cmds.playbackOptions(edit=True, minTime=frame_range_start)
        cmds.playbackOptions(edit=True, maxTime=frame_range_end)

        # set the timeline to the first frame
        cmds.currentTime(frame_range_start)

    def set_fps(self, fps):
        """
        Set the framerate of the scene
        """
        fps = str(fps) + "fps"
        cmds.currentUnit(time=fps)

    def additional_startup_settings(self, env):
        """
        This function is for all the extra commands that have to be executed on startup.
        """

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
