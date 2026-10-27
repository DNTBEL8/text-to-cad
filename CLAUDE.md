# 3D Print Farm Bot

This project has a print farm management tool at `print_farm_bot.py` and a full CAD pipeline in `skills/cad/`. When the user asks to generate, review, view, print, or sell 3D models, handle it directly — never ask the user to run commands themselves.

## Workflow (in order)

```
generate → build → review → [user confirms] → approve → queue → print → inventory → sell
```

**Review and approval are required before a model can be listed in inventory.** This ensures nothing gets sold with bad geometry.

## How generation works (no external API key needed)

You ARE the AI. When asked to generate a model:
1. `python print_farm_bot.py new <name> "<description>"` — reserve slot, get file paths
2. Write build123d Python yourself to the `py_file` path
3. `python print_farm_bot.py build <model_id>` — compile STEP + STL + GLB
4. `python print_farm_bot.py review <model_id>` — validate geometry
5. Show user the review report and ask for confirmation
6. `python print_farm_bot.py approve <model_id>` — only after user says yes

## build123d code rules

- `from build123d import *`
- Named parameters at top, dimensions in millimeters
- Single `gen_step()` returning a Shape or Compound
- Closed, manifold, FDM-printable: walls ≥ 1.5 mm, no unsupported overhangs > 60°
- No file I/O, display calls, or `__main__` block

## Review report interpretation

- **Watertight: PASS** — mesh is closed and printable
- **Watertight: FAIL** — geometry has holes; will likely fail to print; fix and rebuild
- **Dimensions** — actual bounding box in mm; verify against user's intent
- **Material cost** — PLA at 20% infill, $0.025/g; 4× is a typical minimum sell price
- **Suggested minimum price** — printed by `approve` automatically

## All bot commands

```bash
python print_farm_bot.py new <name> "<description>"          # reserve slot
python print_farm_bot.py build <model_id>                   # compile STEP+STL
python print_farm_bot.py review <model_id>                  # geometry validation
python print_farm_bot.py approve <model_id> ["notes"]       # clear for sale
python print_farm_bot.py list                               # list all models
python print_farm_bot.py view <model_id>                    # open in 3D viewer
python print_farm_bot.py queue                              # show queue
python print_farm_bot.py queue add <model_id> [qty]        # add to queue
python print_farm_bot.py queue status <job_id> <printing|done|failed>
python print_farm_bot.py inventory                          # show inventory
python print_farm_bot.py inventory add <job_id> <price>    # list for sale (requires approval)
python print_farm_bot.py inventory sell <item_id> <qty>    # record sale
python print_farm_bot.py summary                            # dashboard
```

## Data files

- `print_farm/models_index.json` — models (includes review + approval fields)
- `print_farm/queue.json` — print jobs
- `print_farm/inventory.json` — sales listings
- `print_farm/MARKET.md` — market research: best-selling categories, pricing, platforms, top designs to generate

## Market guidance

When the user asks what to make, what sells, or how to price/sell — read `print_farm/MARKET.md`.
The top 10 designs at the bottom of MARKET.md are pre-researched high-ROI items ready to generate.

## Slash commands

- `/generate <description>` — full generate → build → review flow
- `/review <model_id>` — review geometry and offer to approve
- `/view <model_id>` — open in 3D viewer
- `/queue [add|status] ...` — manage print queue
- `/inventory [add|sell] ...` — manage sales
- `/farm-summary` — full dashboard
