#!/bin/bash

# Automatically detects current nickname and strips trailing spaces
G502_NAME=$(ratbagctl list | grep "G502" | cut -f1 -d: | xargs)

# Ensure Profile 1 is targeted and active
ratbagctl "$G502_NAME" profile active set 1

# ==========================================
# RESET RESOLUTIONS TO PROFILE 0 DEFAULTS
# ==========================================

ratbagctl "$G502_NAME" profile 1 resolution 0 set 400
ratbagctl "$G502_NAME" profile 1 resolution 1 set 800
ratbagctl "$G502_NAME" profile 1 resolution 1 set default
ratbagctl "$G502_NAME" profile 1 resolution 1 set active
ratbagctl "$G502_NAME" profile 1 resolution 2 set 1000
ratbagctl "$G502_NAME" profile 1 resolution 3 set 100 disabled
ratbagctl "$G502_NAME" profile 1 resolution 4 set 100 disabled

# ==========================================
# RESET BUTTONS TO PROFILE 0 DEFAULTS
# ==========================================

# Left click
ratbagctl "$G502_NAME" profile 1 button 0 action set button 1

# Right click
ratbagctl "$G502_NAME" profile 1 button 1 action set button 2

# Middle click (G3 / Scroll Click)
ratbagctl "$G502_NAME" profile 1 button 2 action set button 3

# G4 (Rear Side Button)
ratbagctl "$G502_NAME" profile 1 button 3 action set button 4

# G5 (Forward Side Button)
ratbagctl "$G502_NAME" profile 1 button 4 action set button 5

# G6 (Sniper Thumb Button) -> Second Mode (temporary DPI shift)
ratbagctl "$G502_NAME" profile 1 button 5 action set special second-mode

# G7 Button (DPI Down Position)
ratbagctl "$G502_NAME" profile 1 button 6 action set special resolution-down

# G8 Button (DPI Up Position)
ratbagctl "$G502_NAME" profile 1 button 7 action set special resolution-up

# G10 (Top Button behind wheel) -> unassigned
ratbagctl "$G502_NAME" profile 1 button 8 action set none

# Tilt Wheel Right -> Standard Right Scroll
ratbagctl "$G502_NAME" profile 1 button 9 action set button 9

# Tilt Wheel Left -> Standard Left Scroll
ratbagctl "$G502_NAME" profile 1 button 10 action set button 10

# Display final layout to verify
ratbagctl "$G502_NAME" info
