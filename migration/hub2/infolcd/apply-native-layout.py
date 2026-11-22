"""Make all twelve slots of the pinned native Living Glass grid available."""
from pathlib import Path
import sys

from importlib import import_module

replace = import_module("apply-visual").replace

lcd = Path(sys.argv[1])
changes = {
    "infopanel.py": [('capacity = 9 if layout_for', 'capacity = 12 if layout_for', 1)],
    "infopanel_henk_task.py": [
        ("capacity = 9 if wide else 4", "capacity = 12 if wide else 4", 3),
        ("capacity=9", "capacity=12", 1),
        ("    from infopanel_ui import Hit, MUTED", "    from infopanel_ui import BORDER, Hit, MUTED", 1),
        ("    for role, rect, reference, opacity in placements(model, wide):",
         "    if wide:\n"
         "        for x, y, right, bottom in grid(12):\n"
         "            c.draw.rounded_rectangle((x, y, right-1, bottom-1), radius=12, outline=BORDER)\n"
         "    for role, rect, reference, opacity in placements(model, wide):", 1),
    ],
    "infopanel_landscape.py": [
        ("Až devět stejně velkých dlaždic, bez prázdných náhradních karet.",
         "Dvanáct stejně velkých dlaždic.", 1),
        ("if not 0<=count<=9:", "if not 0<=count<=12:", 1),
        ("vejde nejvýše devět", "vejde nejvýše dvanáct", 1),
    ],
    "infopanel_studio.py": [
        ("(len(roles)+8)//9", "(len(roles)+11)//12", 1),
        ("page*9:(page+1)*9", "page*12:(page+1)*12", 2),
        ("(x+3,y+36,x+105,y+138)", "(x+3,y+42,x+92,y+131)", 1),
        ("(x+111,y+63),state,17,WHITE,width=r-x-122", "(x+96,y+63),state,15,WHITE,width=r-x-105", 1),
        ("(x+111,y+92,r-13,y+121)", "(x+96,y+92,r-13,y+121)", 1),
    ],
}
for name, replacements in changes.items():
    path = lcd / name
    source = path.read_text()
    for before, after, count in replacements:
        source = replace(source, before, after, count)
    compile(source, str(path), "exec")
    path.write_text(source)
