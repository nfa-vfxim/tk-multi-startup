# MIT License

# Copyright (c) 2020 Netherlands Film Academy

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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class Startup(HookBaseClass):
    def startup(self):
        """This method will be called at the start of a new Houdini session."""

        frame_start = self._getDefaultFrameRange()[0]
        frame_end = self._getDefaultFrameRange()[1]

        self._setFrameRange(frame_start, frame_end)

    # private methods

    def _setFrameRange(self, frameRangeStart, frameRangeEnd):
        """Set the Maya frame range and playback range to the input data."""
        

    def _getDefaultFrameRange(self):
        """Get the configured frame range integers."""

        # get an instance of the app itself
        app = self.parent

        # create an empty array to fill with frame range defaults
        frame_range = []

        # populate frame_range with settings
        try:
            frame_range.append(app.get_setting("framerange_default_start"))
            frame_range.append(app.get_setting("framerange_default_end"))
        except:
            self.logger.error("An error occured while getting the default configured frame range. Make sure the configuration for tk-houdini-startup is correct.")

        return frame_range