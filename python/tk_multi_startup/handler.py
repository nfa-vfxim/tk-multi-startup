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
import re

import sgtk


class Handler:
    def __init__(self, app):
        self.app = app
        self.current_engine = self.app.engine
        self.logger = self.app.logger
        self.sg = self.current_engine.shotgun
        self.current_context = self.current_engine.context
        self.entity = self.current_context.entity

        self.env = {}

        # Setting FPS
        fps = self.__get_default_fps
        self.app.execute_hook_method(
            key="helper_hook",
            method_name="set_fps",
            fps=fps,
        )

        if self.entity is not None:
            # Get data from ShotGrid
            entity_id = self.entity["id"]
            entity_type = self.entity["type"]

            filters = [["id", "is", entity_id]]

            columns = ["sg_cut_in", "sg_cut_out", "code"]

            self.entity_data = self.sg.find_one(entity_type, filters, columns)

            if entity_type == "Shot":
                # Setting Frame Range
                frame_range = self.__get_frame_range()
                frame_start = frame_range[0]
                frame_end = frame_range[1]

                self.app.execute_hook_method(
                    key="helper_hook",
                    method_name="set_frame_range",
                    frame_range_start=frame_start,
                    frame_range_end=frame_end,
                )

        # Set environments
        self.__set_environments()

        # Run engine specific functions
        self.app.execute_hook_method(
            key="helper_hook",
            method_name="other_settings",
            env=self.env,
        )

    # private methods
    def __set_environments(self):
        """Set ShotGrid environment variables"""
        env = {}

        project_name = self.current_context.project.get("name")

        project_data = self.sg.find_one(
            "Project", [["name", "is", project_name]], ["sg_projectcode", "sg_fps"]
        )

        env["SG_PROJECT_NAME"] = project_name
        env["SG_PROJECT_CODE"] = project_data.get("sg_projectcode")
        env["SG_PROJECT_ROOT"] = self.__fix_path(
            self.current_context._get_project_roots()[0]
        )
        env["SG_FPS"] = str(project_data.get("sg_fps"))
        env["SG_USER_NAME"] = self.current_context.user.get("name")
        env["SG_USER_ID"] = str(self.current_context.user.get("id"))

        if self.entity:
            entity_name = self.entity["name"]
            entity_type = self.entity["type"]
            entity_id = self.entity["id"]

            env["SG_CONTEXT_TYPE"] = entity_type
            env["SG_CONTEXT_ID"] = str(entity_id)

            source_pattern = re.compile(
                r"//nfa-vfxim-source.stud.ahk.nl/(\d+ejaar)_source/"
            )
            replacement = r"//nfa-vfxim-render.stud.ahk.nl/\1_render/"

            if entity_type == "Asset":
                template = self.app.get_template("asset_root")
                fields = self.current_context.as_template_fields(template)
                root = self.__fix_path(template.apply_fields(fields))
                env["SG_ASSET"] = entity_name
                env["SG_STEP"] = fields.get("Step")
                env["SG_ASSET_ROOT"] = root
                env["SG_ASSET_RENDER_ROOT"] = re.sub(source_pattern, replacement, root)

                env["SG_SEQUENCE"] = "-"
                env["SG_SHOT"] = "-"
                env["SG_SHOT_ROOT"] = "-"
                env["SG_SHOT_RENDER_ROOT"] = "-"

            if entity_type == "Shot":
                template = self.app.get_template("shot_root")
                fields = self.current_context.as_template_fields(template)
                root = self.__fix_path(template.apply_fields(fields))

                env["SG_SHOT"] = entity_name
                env["SG_SEQUENCE"] = fields.get("Sequence")
                env["SG_STEP"] = fields.get("Step")
                env["SG_SHOT_ROOT"] = root
                env["SG_SHOT_RENDER_ROOT"] = re.sub(source_pattern, replacement, root)

                env["SG_FSTART"] = str(self.entity_data.get("sg_cut_in"))
                env["SG_FEND"] = str(self.entity_data.get("sg_cut_out"))

                env["SG_ASSET"] = "-"
                env["SG_ASSET_ROOT"] = "-"
                env["SG_ASSET_RENDER_ROOT"] = "-"

            work_template = self.app.get_template("work_file")
            if work_template:
                file = self.app.execute_hook_method(
                    key="helper_hook",
                    method_name="get_file_path",
                )
                fields = work_template.get_fields(file)
                env["SG_NAME"] = fields.get("name")
                env["SG_VERSION"] = str(fields.get("version"))
                env["SG_VERSION_S"] = f"v{fields.get('version'):03}"

        self.env = env
        for key, value in env.items():
            sgtk.util.append_path_to_env_var(key, value)

        self.logger.debug(f"Set Houdini ShotGrid environment variables: {env}")

    def __fix_path(self, path: str) -> str:
        """Fix Windows paths"""
        return path.replace(os.sep, "/")

    def __get_frame_range(self):
        """Get the configured frame range integers."""

        # create an empty list to fill with frame range defaults
        frame_range = []

        frame_start = self.entity_data["sg_cut_in"]
        frame_end = self.entity_data["sg_cut_out"]

        if frame_start is None:
            try:
                frame_range.append(self.app.get_setting("frame_range_default_start"))
                frame_range.append(self.app.get_setting("frame_range_default_end"))
            except Exception as e:
                self.logger.error(
                    "An error occurred while getting the default configured frame range. Make sure the configuration for "
                    "tk-houdini-startup is correct. %s" % str(e)
                )

        else:
            frame_range.append(frame_start)
            frame_range.append(frame_end)

        return frame_range

    @property
    def __get_default_fps(self):
        """Get the configured fps integer."""

        # get fps setting
        try:
            project_name = self.current_context.project["name"]

            fps = self.sg.find_one(
                "Project", [["name", "is", project_name]], ["sg_fps"]
            ).get("sg_fps")

            if fps is None:
                fps = self.app.get_setting("fps_default")

            return fps

        except Exception as e:
            self.logger.error(
                "An error occurred while getting the default configured frame range. Make sure the configuration for "
                "tk-multi-startup is correct. %s" % str(e)
            )
