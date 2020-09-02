![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/nfa-vfxim/tk-houdini-startup?include_prereleases)
![GitHub](https://img.shields.io/github/license/nfa-vfxim/tk-houdini-startup)

# tk-houdini-startup
tk-houdini-startup is a Shotgun Toolkit app that allows you to add some logic to the startup process of [tk-houdini](https://github.com/nfa-vfxim/tk-houdini). At default, the app sets the frame range to the frame range found on Shotgun in the task or entity. If one can't be found it will default to 1001-1240. This and other things can be configured through your Shotgun configuration. 

# Configuration
- `framerange_default_start`
    - type: `integer`
    - The app will use this as a default frame range start value if one can't be found in Shotgun.
    - default value: `1001`
- `framerange_default_end`
    - type: `integer`
    - The app will use this as a default frame range end value if one can't be found in Shotgun.
    - default value: `1240`
- `execute_at_startup_hook`
    - type: `hook`
    - A hook that will be called at the start of a Houdini session.
    - default value: `{self}\hooks\startup.py`
- `execute_at_context_change_hook`
    - type: `hook`
    - A hook that will be called after a change of context.
    - default value: `{self}\hooks\context.py`