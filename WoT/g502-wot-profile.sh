#!/bin/bash

# Automatically detects current nickname and strips trailing spaces
G502_NAME=$(ratbagctl list | grep "G502" | cut -f1 -d: | xargs)

# Ensure Profile 1 is targeted and active
ratbagctl "$G502_NAME" profile active set 1

# ==========================================
# DEFAULT MOUSE CLICKS
# ==========================================
ratbagctl "$G502_NAME" profile 1 button 0 action set button 1
ratbagctl "$G502_NAME" profile 1 button 1 action set button 2

# ==========================================
# ACTIVE CUSTOM WORLD OF TANKS MAPPINGS
# ==========================================

# G3 (Scroll Click) -> Hull Lock / Brake
ratbagctl "$G502_NAME" profile 1 button 2 action set macro KEY_X

# G4 (Rear Side Button) -> Cruise Control Forward
ratbagctl "$G502_NAME" profile 1 button 3 action set macro KEY_F

# G5 (Forward Side Button) -> Cruise Control Reverse
ratbagctl "$G502_NAME" profile 1 button 4 action set macro KEY_R

# G6 (Sniper Thumb Button) -> Handbrake (Formerly G-Shift)
ratbagctl "$G502_NAME" profile 1 button 5 action set macro KEY_P

# G7 Button (DPI Down Position) -> "Help! / Requesting Assistance"
ratbagctl "$G502_NAME" profile 1 button 6 action set macro KEY_F7 

# G8 Button (DPI Up Position) -> "Attacking Target!"
ratbagctl "$G502_NAME" profile 1 button 7 action set macro KEY_T

# ==========================================
# RESET UNASSIGNED BUTTONS TO PROFILE 0 DEFAULTS
# ==========================================

# G10 (Top Button behind wheel) -> Profile Cycle
ratbagctl "$G502_NAME" profile 1 button 8 action set special profile-cycle-up

# Tilt Wheel Right -> Standard Right Scroll
ratbagctl "$G502_NAME" profile 1 button 9 action set button 9

# Tilt Wheel Left -> Standard Left Scroll
ratbagctl "$G502_NAME" profile 1 button 10 action set button 10

# Display final layout to verify
ratbagctl "$G502_NAME" info
