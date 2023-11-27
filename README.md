![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/nfa-vfxim/tk-multi-startup?include_prereleases)
![GitHub](https://img.shields.io/github/license/nfa-vfxim/tk-multi-startup)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# tk-multi-startup
tk-multi-startup is a Shotgun Toolkit app that allows you to add some logic to the startup process of the engine. At default, the app sets the frame range to the frame range found in the configuration. If one can't be found it will default to 1001-1240. This and other things can be configured through your Shotgun configuration. 

## Configuration
- `framerange_default_start`
    - type: `integer`
    - The app will use this as a default frame range start value.
    - default value: `1001`
- `framerange_default_end`
    - type: `integer`
    - The app will use this as a default frame range end value.
    - default value: `1240`
- `fps_default`
    - type: `integer`
    - description: Default fps to use when opening engines.
    - default_value: `25`
- `helper_hook`
    - type: `hook`
    - A hook that implements helper functions.
    - default_value: `{self}/{engine_name}_helper.py`
- `work_file_template`
    - type: `template`
    - A template for the work file path
- `asset_root_template`
    - type: `template`
    - A template for the asset root directory
- `shot_root_template`
    - type: `template`
    - A template for the shot root directory

## Environment variables
- `SG_PROJECT_NAME`: Project name
- `SG_PROJECT_CODE`: Project code
- `SG_PROJECT_ROOT`: Project file root
- `SG_FPS`: Project fps
- `SG_USER_NAME`: Current username
- `SG_USER_ID`: Current user id
- `SG_CONTEXT_TYPE`: Current context type (Asset, Shot)
- `SG_CONTEXT_ID`: Current context id
- `SG_STEP`: Current step
- `SG_NAME`: File name (_main_)
- `SG_VERSION`: File version
- `SG_VERSION_S`: File version as string (`v{version}`)
- Asset context:
  - `SG_ASSET`: Asset name, if different context: `-`
  - `SG_ASSET_ROOT`: Asset file root, if different context: `-`
  - `SG_ASSET_RENDER_ROOT`: Asset file root on render server, if different context: `-`
- Shot context:
  - `SG_SEQUENCE`: Sequence name, if different context: `-`
  - `SG_SHOT`: Shot name, if different context: `-`
  - `SG_SHOT_ROOT`: Shot file root, if different context: `-`
  - `SG_SHOT_RENDER_ROOT`: Shot file root on render server, if different context: `-`