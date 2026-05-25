# 3D Print Farm Bot

This project includes a 3D print farm bot at `print_farm_bot.py` that uses Claude AI to generate 3D-printable models from text, manage a print queue, and track sales inventory.

## How to help the user

When the user asks to generate, view, print, queue, or sell 3D models — run the bot for them using Bash. Never ask them to run it themselves.

Requires `ANTHROPIC_API_KEY` to be set in the environment.

## Bot commands

```bash
# Generate a 3D model from text (takes 30-60s — use streaming/patience)
python print_farm_bot.py generate "description of object"
python print_farm_bot.py generate "description" --name short_name

# List all generated models
python print_farm_bot.py list

# Open a model in the 3D viewer
python print_farm_bot.py view <model_id>

# Print queue management
python print_farm_bot.py queue                       # list queue
python print_farm_bot.py queue add <model_id>        # add to queue
python print_farm_bot.py queue add <model_id> 5      # queue 5 copies
python print_farm_bot.py queue status <job_id> printing
python print_farm_bot.py queue status <job_id> done

# Inventory and sales
python print_farm_bot.py inventory                        # list inventory
python print_farm_bot.py inventory add <job_id> <price>   # list for sale
python print_farm_bot.py inventory sell <item_id> <qty>   # record a sale

# Dashboard
python print_farm_bot.py summary
```

## Data locations

- Generated models: `print_farm/models/<id>/`
- Model index: `print_farm/models_index.json`
- Print queue: `print_farm/queue.json`
- Inventory: `print_farm/inventory.json`

## Workflow

Generate → view → queue → mark done → add to inventory → sell

## Slash commands available

- `/generate` — generate a 3D model from text
- `/view` — open a model in the 3D viewer
- `/queue` — manage print queue
- `/inventory` — manage sales inventory
- `/farm-summary` — show print farm dashboard
