Generate a 3D printable model from this description: $ARGUMENTS

Follow these steps exactly:

**Step 1 — Reserve a slot**
```bash
python print_farm_bot.py new "<safe_name_no_spaces>" "$ARGUMENTS"
```
Capture: model_id, py_file, step_file, stl_file, stl_name, skill_dir.

**Step 2 — Write build123d code**
Write valid build123d Python to the `py_file` path. Requirements:
- `from build123d import *`
- Named dimension parameters at the top (mm)
- Single `gen_step()` returning a closed, manifold Shape/Compound
- FDM-printable: walls ≥ 1.5 mm, no unsupported overhangs > 60°
- No file I/O, display calls, or `__main__` block

**Step 3 — Build**
```bash
python print_farm_bot.py build <model_id>
```

**Step 4 — Review geometry**
```bash
python print_farm_bot.py review <model_id>
```
Read the output carefully. Report to the user:
- Is it watertight (printable)?
- Actual dimensions (X × Y × Z mm)
- Estimated material weight and cost
- Any geometry warnings

**Step 5 — Report to user**
Show the review results and ask: "Does this look right? Should I approve it for sale?"
Only run `approve <model_id>` if the user confirms.
