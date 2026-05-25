#!/usr/bin/env python3
"""3D Print Farm Bot - Generate, manage, and track 3D prints using Claude AI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import anthropic

SKILL_DIR = Path(__file__).parent / "skills" / "cad"
RENDER_DIR = Path(__file__).parent / "skills" / "render"
DATA_DIR = Path(__file__).parent / "print_farm"
MODELS_DIR = DATA_DIR / "models"
QUEUE_FILE = DATA_DIR / "queue.json"
INVENTORY_FILE = DATA_DIR / "inventory.json"

MODEL_ID = "claude-opus-4-7"

BUILD123D_SYSTEM_PROMPT = """You are a CAD expert that generates build123d Python code to create 3D printable parts.

Rules:
- Always define a `gen_step()` function that returns a build123d Shape or Compound
- Use millimeters for all dimensions
- Ensure closed, manifold solids suitable for 3D printing
- Include wall thickness >= 1.5mm for thin-walled objects
- Use parametric style with named variables at the top
- Only import from build123d (e.g. `from build123d import *`)
- Do NOT include any file I/O, display calls, or if __name__ == "__main__" blocks
- The gen_step() function is the ONLY required output

Example structure:
```python
from build123d import *

# Parameters
width = 40
height = 20
depth = 30
wall = 2

def gen_step():
    box = Box(width, height, depth)
    return box
```

Generate ONLY the Python code, no markdown fences, no explanations."""


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _load_queue() -> dict:
    return _load_json(QUEUE_FILE)


def _load_inventory() -> dict:
    return _load_json(INVENTORY_FILE)


def _load_models_index() -> dict:
    index_path = DATA_DIR / "models_index.json"
    return _load_json(index_path)


def _save_models_index(data: dict) -> None:
    index_path = DATA_DIR / "models_index.json"
    _save_json(index_path, data)


def cmd_generate(description: str, name: str | None = None) -> None:
    """Generate a 3D model from a text description using Claude."""
    client = anthropic.Anthropic()

    model_id = str(uuid.uuid4())[:8]
    safe_name = (name or description[:40]).replace(" ", "_").replace("/", "_")
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    py_file = model_dir / f"{safe_name}.py"
    step_file = model_dir / f"{safe_name}.step"
    stl_file = model_dir / f"{safe_name}.stl"

    print(f"Generating 3D model for: {description}")
    print("Asking Claude to generate build123d code...")

    code_parts: list[str] = []

    with client.messages.stream(
        model=MODEL_ID,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=BUILD123D_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Generate build123d Python code for a 3D printable object: {description}",
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            code_parts.append(text)

    print()
    code = "".join(code_parts).strip()

    # Strip any accidental markdown fences
    if code.startswith("```"):
        lines = code.splitlines()
        code = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    py_file.write_text(code)
    print(f"\nCode saved to: {py_file}")

    print("\nRunning CAD generation...")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/step",
            str(py_file.resolve()),
            "--stl",
            str(stl_file.resolve()),
            "--skip-explorer",
            "--verbose",
        ],
        cwd=str(SKILL_DIR),
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"\nCAD generation failed (exit {result.returncode}).")
        print("The generated Python file is saved — you can inspect or fix it manually.")
    else:
        print(f"\nSTEP file: {step_file}")
        print(f"STL file:  {stl_file}")

    index = _load_models_index()
    index[model_id] = {
        "id": model_id,
        "name": safe_name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "py_file": str(py_file),
        "step_file": str(step_file) if step_file.exists() else None,
        "stl_file": str(stl_file) if stl_file.exists() else None,
        "generation_ok": result.returncode == 0,
    }
    _save_models_index(index)

    print(f"\nModel ID: {model_id}")
    print("Use 'view {model_id}' to preview in 3D viewer.")
    print("Use 'queue add {model_id}' to add to print queue.")


def cmd_list() -> None:
    """List all generated models."""
    index = _load_models_index()
    if not index:
        print("No models generated yet. Use 'generate <description>' to create one.")
        return

    print(f"{'ID':<10} {'Name':<35} {'Status':<8} {'Created'}")
    print("-" * 75)
    for entry in sorted(index.values(), key=lambda e: e["created_at"]):
        status = "ok" if entry.get("generation_ok") else "fail"
        created = entry["created_at"][:16].replace("T", " ")
        print(f"{entry['id']:<10} {entry['name']:<35} {status:<8} {created}")


def cmd_view(model_id: str) -> None:
    """View a model in the 3D viewer."""
    index = _load_models_index()
    entry = index.get(model_id)
    if not entry:
        print(f"Model '{model_id}' not found. Use 'list' to see available models.")
        return

    step_file = entry.get("step_file")
    stl_file = entry.get("stl_file")
    target = step_file if step_file and Path(step_file).exists() else stl_file

    if not target or not Path(target).exists():
        print(f"No viewable file found for model '{model_id}'.")
        print(f"Source: {entry.get('py_file')}")
        return

    print(f"Opening {target} in 3D viewer...")
    subprocess.run(
        [
            "npm",
            "--prefix",
            "scripts/viewer",
            "run",
            "dev:ensure",
            "--",
            "--file",
            target,
        ],
        cwd=str(RENDER_DIR),
    )


def cmd_queue(subcommand: str | None = None, args: list[str] | None = None) -> None:
    """Manage the print queue."""
    queue = _load_queue()

    if subcommand is None or subcommand == "list":
        if not queue:
            print("Print queue is empty.")
            return
        print(f"{'Job ID':<10} {'Model':<25} {'Status':<12} {'Added'}")
        print("-" * 65)
        for job in sorted(queue.values(), key=lambda j: j["added_at"]):
            added = job["added_at"][:16].replace("T", " ")
            print(
                f"{job['id']:<10} {job['model_name']:<25} {job['status']:<12} {added}"
            )
        return

    if subcommand == "add":
        if not args:
            print("Usage: queue add <model_id>")
            return
        model_id = args[0]
        index = _load_models_index()
        entry = index.get(model_id)
        if not entry:
            print(f"Model '{model_id}' not found.")
            return
        job_id = str(uuid.uuid4())[:8]
        queue[job_id] = {
            "id": job_id,
            "model_id": model_id,
            "model_name": entry["name"],
            "description": entry["description"],
            "stl_file": entry.get("stl_file"),
            "step_file": entry.get("step_file"),
            "status": "pending",
            "added_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "quantity": int(args[1]) if len(args) > 1 else 1,
        }
        _save_json(QUEUE_FILE, queue)
        print(f"Added job {job_id} for '{entry['name']}' to print queue.")
        return

    if subcommand == "status":
        if not args or len(args) < 2:
            print("Usage: queue status <job_id> <pending|printing|done|failed>")
            return
        job_id, new_status = args[0], args[1]
        valid = {"pending", "printing", "done", "failed"}
        if new_status not in valid:
            print(f"Status must be one of: {', '.join(sorted(valid))}")
            return
        if job_id not in queue:
            print(f"Job '{job_id}' not found.")
            return
        queue[job_id]["status"] = new_status
        if new_status == "printing":
            queue[job_id]["started_at"] = datetime.now().isoformat()
        elif new_status == "done":
            queue[job_id]["completed_at"] = datetime.now().isoformat()
        _save_json(QUEUE_FILE, queue)
        print(f"Job {job_id} status updated to '{new_status}'.")

        if new_status == "done":
            print(f"Use 'inventory add {job_id} <price>' to list this print for sale.")
        return

    print(f"Unknown queue subcommand '{subcommand}'. Use: list, add, status")


def cmd_inventory(
    subcommand: str | None = None, args: list[str] | None = None
) -> None:
    """Manage the sales inventory."""
    inventory = _load_inventory()

    if subcommand is None or subcommand == "list":
        if not inventory:
            print("Inventory is empty. Complete prints and add them with 'inventory add'.")
            return
        total_value = sum(
            i["price"] * i["quantity_available"]
            for i in inventory.values()
        )
        print(f"{'Item ID':<10} {'Name':<30} {'Price':>8} {'Qty':>5} {'Sold':>6}")
        print("-" * 65)
        for item in sorted(inventory.values(), key=lambda i: i["added_at"]):
            print(
                f"{item['id']:<10} {item['name']:<30} "
                f"${item['price']:>7.2f} {item['quantity_available']:>5} "
                f"{item['quantity_sold']:>6}"
            )
        print(f"\nTotal available inventory value: ${total_value:.2f}")
        return

    if subcommand == "add":
        if not args or len(args) < 2:
            print("Usage: inventory add <job_id> <price>")
            return
        job_id, price_str = args[0], args[1]
        try:
            price = float(price_str)
        except ValueError:
            print(f"Invalid price: {price_str}")
            return

        queue = _load_queue()
        job = queue.get(job_id)
        if not job:
            print(f"Job '{job_id}' not found in print queue.")
            return

        item_id = str(uuid.uuid4())[:8]
        inventory[item_id] = {
            "id": item_id,
            "job_id": job_id,
            "model_id": job["model_id"],
            "name": job["model_name"],
            "description": job["description"],
            "price": price,
            "quantity_available": job.get("quantity", 1),
            "quantity_sold": 0,
            "added_at": datetime.now().isoformat(),
        }
        _save_json(INVENTORY_FILE, inventory)
        print(
            f"Added {job.get('quantity', 1)}x '{job['model_name']}' to inventory at ${price:.2f} each."
        )
        return

    if subcommand == "sell":
        if not args or len(args) < 2:
            print("Usage: inventory sell <item_id> <quantity>")
            return
        item_id, qty_str = args[0], args[1]
        try:
            qty = int(qty_str)
        except ValueError:
            print(f"Invalid quantity: {qty_str}")
            return

        if item_id not in inventory:
            print(f"Item '{item_id}' not found.")
            return
        item = inventory[item_id]
        if qty > item["quantity_available"]:
            print(
                f"Only {item['quantity_available']} available "
                f"(requested {qty})."
            )
            return
        item["quantity_available"] -= qty
        item["quantity_sold"] += qty
        _save_json(INVENTORY_FILE, inventory)
        revenue = qty * item["price"]
        print(
            f"Sold {qty}x '{item['name']}' for ${revenue:.2f}. "
            f"Remaining: {item['quantity_available']}."
        )
        return

    print(f"Unknown inventory subcommand '{subcommand}'. Use: list, add, sell")


def cmd_summary() -> None:
    """Show a summary of the print farm."""
    index = _load_models_index()
    queue = _load_queue()
    inventory = _load_inventory()

    total_models = len(index)
    ok_models = sum(1 for e in index.values() if e.get("generation_ok"))

    queue_by_status: dict[str, int] = {}
    for job in queue.values():
        s = job["status"]
        queue_by_status[s] = queue_by_status.get(s, 0) + 1

    total_revenue = sum(
        i["price"] * i["quantity_sold"] for i in inventory.values()
    )
    inventory_value = sum(
        i["price"] * i["quantity_available"] for i in inventory.values()
    )

    print("=== 3D Print Farm Summary ===")
    print(f"Models generated : {ok_models}/{total_models}")
    print(f"Queue - pending  : {queue_by_status.get('pending', 0)}")
    print(f"Queue - printing : {queue_by_status.get('printing', 0)}")
    print(f"Queue - done     : {queue_by_status.get('done', 0)}")
    print(f"Inventory items  : {len(inventory)}")
    print(f"Inventory value  : ${inventory_value:.2f}")
    print(f"Total revenue    : ${total_revenue:.2f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="print_farm_bot",
        description="3D Print Farm Bot — generate, view, queue, and sell 3D prints using Claude AI.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # generate
    gen_p = sub.add_parser("generate", help="Generate a 3D model from a text description")
    gen_p.add_argument("description", help="What to generate (e.g. 'small gear with 20 teeth')")
    gen_p.add_argument("--name", help="Optional short name for the model file")

    # list
    sub.add_parser("list", help="List all generated models")

    # view
    view_p = sub.add_parser("view", help="View a model in the 3D viewer")
    view_p.add_argument("model_id", help="Model ID from 'list'")

    # queue
    queue_p = sub.add_parser("queue", help="Manage the print queue")
    queue_p.add_argument(
        "subcommand",
        nargs="?",
        choices=["list", "add", "status"],
        default="list",
    )
    queue_p.add_argument("rest", nargs="*", help="Arguments for the subcommand")

    # inventory
    inv_p = sub.add_parser("inventory", help="Manage sales inventory")
    inv_p.add_argument(
        "subcommand",
        nargs="?",
        choices=["list", "add", "sell"],
        default="list",
    )
    inv_p.add_argument("rest", nargs="*", help="Arguments for the subcommand")

    # summary
    sub.add_parser("summary", help="Show print farm summary")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "generate":
        cmd_generate(args.description, name=args.name)
    elif args.command == "list":
        cmd_list()
    elif args.command == "view":
        cmd_view(args.model_id)
    elif args.command == "queue":
        cmd_queue(args.subcommand, args.rest)
    elif args.command == "inventory":
        cmd_inventory(args.subcommand, args.rest)
    elif args.command == "summary":
        cmd_summary()
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
