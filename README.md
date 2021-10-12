![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/nfa-vfxim/tk-multi-startup?include_prereleases)
![GitHub](https://img.shields.io/github/license/nfa-vfxim/tk-multi-startup)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# tk-multi-startup
tk-multi-startup is a Shotgun Toolkit app that allows you to add some logic to the startup process of the engine. At default, the app sets the frame range to the frame range found in the configuration. If one can't be found it will default to 1001-1240. This and other things can be configured through your Shotgun configuration. 

# Configuration
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
- `execute_at_startup_hook`
    - type: `hook`
    - A hook that will be called at the start of a Houdini session.
    - default value: `{self}\hooks\startup.py`
- `execute_at_context_change_hook`
    - type: `hook`
    - A hook that will be called after a change of context.
    - default value: `{self}\hooks\context.py`