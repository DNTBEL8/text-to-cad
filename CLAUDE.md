# 3D Print Farm Bot

This project has a print farm management tool at `print_farm_bot.py` and a full CAD pipeline in `skills/cad/`. When the user asks to generate, view, print, or sell 3D models, handle it directly — never ask the user to run commands themselves.

## How generation works (no external API key needed)

You ARE the AI. When asked to generate a model:
1. Run `python print_farm_bot.py new <name> "<description>"` to reserve a slot and get file paths
2. Write the build123d Python code yourself to the `py_file` path it prints
3. Run `python print_farm_bot.py build <model_id>` to generate STEP + STL via the CAD pipeline
4. Offer to view it or queue it for printing

## build123d code rules

- Import only from build123d: `from build123d import *`
- Named parameters at top, dimensions in millimeters
- Single `gen_step()` function returning a Shape or Compound
- Closed, manifold, FDM-printable solid; walls ≥ 1.5 mm
- No file I/O, no display calls, no `__main__` block

## Bot commands

```bash
python print_farm_bot.py new <name> "<description>"    # reserve slot, get file paths
python print_farm_bot.py build <model_id>              # run CAD pipeline
python print_farm_bot.py list                          # list all models
python print_farm_bot.py view <model_id>               # open in 3D viewer
python print_farm_bot.py queue                         # show print queue
python print_farm_bot.py queue add <model_id> [qty]   # add to queue
python print_farm_bot.py queue status <job_id> <printing|done|failed>
python print_farm_bot.py inventory                     # show inventory
python print_farm_bot.py inventory add <job_id> <price>
python print_farm_bot.py inventory sell <item_id> <qty>
python print_farm_bot.py summary                       # dashboard
```

## CAD pipeline detail

The `build` command runs from `skills/cad/` and calls:
```
python scripts/step <py_file> --stl <stl_name> --skip-explorer --verbose
```
STEP and STL are written next to the Python source file in `print_farm/models/<model_id>/`.

## Viewer

The render skill viewer is started with:
```bash
npm --prefix scripts/viewer run dev:ensure -- --file <path>
```
Run from `skills/render/`.

## Data files

- `print_farm/models_index.json` — all generated models
- `print_farm/queue.json` — print queue jobs
- `print_farm/inventory.json` — sales inventory

## Slash commands

- `/generate <description>` — generate a model end-to-end
- `/view <model_id>` — open in 3D viewer
- `/queue [add|status] ...` — manage print queue
- `/inventory [add|sell] ...` — manage sales
- `/farm-summary` — full dashboard
