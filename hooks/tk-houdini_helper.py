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

import sgtk
import hou

HookBaseClass = sgtk.get_hook_baseclass()


class Helper(HookBaseClass):
    """
    Helper hook implementation for the tk-houdini engine.
    """

    def get_file_path(self):
        """
        Get the file path of the currently opened file
        """
        return hou.hipFile.path()

    def set_frame_range(self, frame_range_start, frame_range_end):
        """Set the Houdini frame range and playback range to the input data."""

        # set the frame range to frameRangeStart - frameRangeEnd
        hou.playbar.setFrameRange(frame_range_start, frame_range_end)

        # set the playback range to frameRangeStart - frameRangeEnd
        hou.playbar.setPlaybackRange(frame_range_start, frame_range_end)

        # set the timeline to the first frame
        hou.setFrame(frame_range_start)

    def set_fps(self, fps):
        """
        Set the framerate of the scene
        """
        hou.setFps(fps)

    def other_settings(self, env):
        """
        This function is for all the extra commands that have to be executed on startup.
        """
        # Add to Houdini Aliases for persistent values
        for key, value in env.items():
            hou.hscript(f"set -g {key} = {value}")
