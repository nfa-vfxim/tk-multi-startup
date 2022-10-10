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
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sgtk
import hou
import os

HookBaseClass = sgtk.get_hook_baseclass()


class Startup(HookBaseClass):
    def startup(self):
        """This method will be called at the start of a new Houdini session."""
        self.current_engine = self.parent.engine
        self.sg = self.current_engine.shotgun
        self.current_context = self.current_engine.context
        self.entity = self.current_context.entity

        # Get data from ShotGrid
        entity_id = self.entity["id"]
        entity_type = self.entity["type"]

        filters = [["id", "is", entity_id]]

        columns = ["sg_cut_in", "sg_cut_out", "code"]

        self.entity_data = self.sg.find_one(entity_type, filters, columns)

        # Setting FPS
        fps = self.__get_default_fps
        self.__set_fps(fps)

        # Setting Frame Range
        frame_range = self.__get_frame_range()
        frame_start = frame_range[0]
        frame_end = frame_range[1]

        self._set_frame_range(frame_start, frame_end)

        self.__set_environments()

    def __set_environments(self):
        """Set environments containing data
        during current session.
        """

        entity_data = self.entity_data

        try:
            # Get provided data into variables
            entity_type = entity_data.get("type")
            entity_id = entity_data.get("id")
            entity_code = entity_data.get("code")
            start_frame = entity_data.get("sg_cut_in")
            end_frame = entity_data.get("sg_cut_out")

            # Set environments
            os.environ["sg_type"] = entity_type
            os.environ["sg_id"] = str(entity_id)
            os.environ["sg_code"] = str(entity_code)
            os.environ["sg_fstart"] = str(start_frame)
            os.environ["sg_fend"] = str(end_frame)

        except Exception as error:
            self.logger.error("Something went wrong %s..." % str(error))

    # private methods
    def _set_frame_range(self, frame_range_start, frame_range_end):
        """Set the Houdini frame range and playback range to the input data."""

        # set the frame range to frameRangeStart - frameRangeEnd
        hou.playbar.setFrameRange(frame_range_start, frame_range_end)

        # set the playback range to frameRangeStart - frameRangeEnd
        hou.playbar.setPlaybackRange(frame_range_start, frame_range_end)

        # set the timeline to the first frame
        hou.setFrame(frame_range_start)

    def __get_frame_range(self):
        """Get the configured frame range integers."""

        # get an instance of the app itself
        app = self.parent

        # create an empty list to fill with frame range defaults
        frame_range = []

        frame_start = self.entity_data["sg_cut_in"]
        frame_end = self.entity_data["sg_cut_out"]

        if frame_start is None:
            try:
                frame_range.append(
                    app.get_setting("frame_range_default_start")
                )
                frame_range.append(app.get_setting("frame_range_default_end"))
            except Exception as e:
                self.logger.error(
                    "An error occurred while getting the default configured frame range. Make sure the configuration for "
                    "tk-houdini-startup is correct. %s" % str(e)
                )

        else:
            frame_range.append(frame_start)
            frame_range.append(frame_end)

        return frame_range

    @staticmethod
    def __set_fps(fps):
        hou.setFps(fps)

    @property
    def __get_default_fps(self):
        """Get the configured fps integer."""

        # get an instance of the app itself
        app = self.parent

        # get fps setting
        try:
            project_name = self.current_context.project["name"]

            fps = self.sg.find_one(
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
