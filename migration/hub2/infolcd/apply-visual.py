"""Transplant the pinned InfoLCD visual components into a staged HDMI tree."""
import ast
from pathlib import Path
import sys


def function(source, name):
    return next(node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def replace(source, old, new, count=1):
    if source.count(old) != count:
        raise ValueError(f"Unexpected InfoLCD baseline for {old!r}")
    return source.replace(old, new)


def transplant(source, reference, name):
    old = ast.get_source_segment(source, function(source, name))
    new = ast.get_source_segment(reference, function(reference, name))
    return replace(source, old, new)


def warm_values(source):
    return [ast.get_source_segment(source, statement.value.body)
            for statement in function(source, "surface").body
            if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.IfExp)
            and isinstance(statement.value.test, ast.Name) and statement.value.test.id == "warm"]


def main(lcd, references):
    grid = (references / "grid.py").read_text()
    henk = (references / "henk.py").read_text()
    presence = (references / "presence.py").read_text()

    task_path = lcd / "infopanel_henk_task.py"
    task = transplant(task_path.read_text(), grid, "grid")
    task = replace(task, "capacity = 9 if wide else 4", "capacity = 12 if wide else 4", 3)
    task = replace(task, "capacity=9", "capacity=12")

    main_path = lcd / "infopanel.py"
    entry = replace(main_path.read_text(), 'capacity = 9 if layout_for', 'capacity = 12 if layout_for')

    landscape_path = lcd / "infopanel_landscape.py"
    landscape = transplant(landscape_path.read_text(), presence, "presence_button")
    landscape = replace(
        landscape, "radius=height//2,fill=color)",
        "radius=height//2,fill=color if active else CARD,outline=None if active else BORDER)",
    )
    old_rects = ast.get_source_segment(landscape, function(landscape, "tile_rects"))
    landscape = replace(landscape, old_rects, """def tile_rects(count):
    from infopanel_henk_task import grid

    if not 0 <= count <= 12:
        raise ValueError("Na jednu stránku se vejde nejvýše 12 dlaždic.")
    return grid(count)""")

    studio_path = lcd / "infopanel_studio.py"
    studio = studio_path.read_text()
    for old, new in zip(warm_values(studio), warm_values(henk), strict=True):
        studio = replace(studio, old, new)
    # Keep the companion's status legible in the narrower upstream grid cell.
    studio = replace(studio, "(x+3,y+36,x+105,y+138)", "(x+3,y+42,x+92,y+131)")
    studio = replace(studio, "(x+111,y+63),state,17,WHITE,width=r-x-122",
                     "(x+96,y+63),state,15,WHITE,width=r-x-105")
    studio = replace(studio, "(x+111,y+92,r-13,y+121)", "(x+96,y+92,r-13,y+121)")
    start = "    roles=model.get('home_tiles',['meteo','heater','plug'])"
    studio = replace(studio, start, start + "\n    capacity = 12")
    studio = replace(studio, "(len(roles)+8)//9", "(len(roles)+capacity-1)//capacity")
    studio = replace(studio, "page*9:(page+1)*9", "page*capacity:(page+1)*capacity", 2)

    updates = {task_path: task, main_path: entry, landscape_path: landscape, studio_path: studio}
    for path, source in updates.items():
        compile(source, str(path), "exec")
    for path, source in updates.items():
        path.write_text(source)


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:]))
