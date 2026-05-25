Generate a 3D printable model from this description: $ARGUMENTS

Follow these steps exactly:

**Step 1 — Reserve a slot**
Run:
```bash
python print_farm_bot.py new "<safe_name_no_spaces>" "$ARGUMENTS"
```
Capture the output lines: model_id, py_file, step_file, stl_file, stl_name, skill_dir.

**Step 2 — Write build123d code**
Write a Python file to the path printed as `py_file`. The file must:
- Import only from build123d: `from build123d import *`
- Define named parameters at the top (dimensions in mm)
- Define a single `gen_step()` function that returns a Shape or Compound
- Produce a closed, manifold solid suitable for FDM 3D printing
- Include wall thickness ≥ 1.5 mm for any thin walls
- No file I/O, no display calls, no `if __name__ == "__main__"` block

Example structure:
```python
from build123d import *

width = 40
height = 20
depth = 30

def gen_step():
    return Box(width, height, depth)
```

**Step 3 — Build STEP and STL**
Run:
```bash
python print_farm_bot.py build <model_id>
```

**Step 4 — Report**
Tell the user:
- The model ID
- That they can say "view <model_id>" to see it in 3D
- That they can say "queue add <model_id>" to add it to the print queue
