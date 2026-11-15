Handoff: G502 annotated button diagram
Repo: /home/sylvain/repositories/GameSetup (branch: current, uncommitted changes in G502/)

Goal
An annotated button-map image for the Logitech G502 in G502/, referenced by G502/README.md. Each button labeled with: manual number · name (G-name) · ratbag index.

Current state of G502/
File	State
g502.png	Bad — my hand-drawn SVG overlay composite; labels overlap the mouse, looks worse than the AI-generated version. Should be replaced.
g502-photo.png	Good — clean product photo, heather grey background (#b8bcc0), 1024x555. Use as the base.
image.png	Deleted (was the original white-background source).
README.md	Good — has the manual↔ratbag mapping table and references g502.png. Update text if the new image filename changes.
g502-profiles.json, g502-apply-profile.py, g502-reset-profile.sh	Done, working, unrelated to the image task.
What went wrong
First attempt: AI image generation produced a good annotated image, but the G7/G8 dots didn't line up with the actual buttons.
Second attempt: I tried drawing annotations manually with ImageMagick + SVG overlay. Spent too many turns zooming into crops to find button coordinates, and the final composite had overlapping labels and worse visual quality than the AI version.
Button coordinates (1024x555 source, verified against the photo)
These are the dot positions on g502-photo.png (the grey-background one) — halve these if working from the original 1024x555 scale, since my last composite was 2x (2048x1110):

Button	x	y
Left click (ratbag 0)	300	200
Right click (ratbag 1)	430	180
Wheel click (ratbag 2)	340	250
Tilt left (ratbag 10)	328	232
Tilt right (ratbag 9)	350	260
DPI Down / G7 (ratbag 6)	470	143
DPI Up / G8 (ratbag 7)	525	113
Profile / G9 (ratbag 8)	505	125
Back / G4 (ratbag 3)	755	227
Forward / G5 (ratbag 4)	670	292
Sniper / G6 (ratbag 5)	622	377
Suggested approach for the next agent
Use the image generation tool (it did well except G7/G8) with g502-photo.png as input, and a prompt that explicitly states the pixel coordinates above for each callout dot — that may anchor the misplaced ones.
Or: generate the AI version again, then fix only the 7/8 dots by compositing small corrections rather than redrawing everything.
Keep the label format: 8 · DPI Up / G8 (ratbag 7).
Save result as G502/g502.png; keep g502-photo.png untouched as the clean base.
The mapping table in README.md is correct — no changes needed there.
Verification
View the final image and confirm each dot sits on its button, especially G7 (lower, circle icon) vs G8 (upper, "G8" icon) behind the scroll wheel.