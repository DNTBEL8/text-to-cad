#!/usr/bin/env python3
"""3D Print Farm Bot - manage and track 3D prints for a print farm business."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent / "skills" / "cad"
RENDER_DIR = Path(__file__).parent / "skills" / "render"
DATA_DIR = Path(__file__).parent / "print_farm"
MODELS_DIR = DATA_DIR / "models"
QUEUE_FILE = DATA_DIR / "queue.json"
INVENTORY_FILE = DATA_DIR / "inventory.json"
INDEX_FILE = DATA_DIR / "models_index.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _idx() -> dict:
    return _load_json(INDEX_FILE)


def _queue() -> dict:
    return _load_json(QUEUE_FILE)


def _inv() -> dict:
    return _load_json(INVENTORY_FILE)


def cmd_new(name: str, description: str) -> None:
    """Reserve a new model slot and print the paths Claude should write to."""
    model_id = str(uuid.uuid4())[:8]
    safe = name.replace(" ", "_").replace("/", "_")
    model_dir = MODELS_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    py_file = model_dir / f"{safe}.py"
    step_file = model_dir / f"{safe}.step"
    stl_file = model_dir / f"{safe}.stl"

    index = _idx()
    index[model_id] = {
        "id": model_id,
        "name": safe,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "py_file": str(py_file),
        "step_file": str(step_file),
        "stl_file": str(stl_file),
        "built": False,
    }
    _save_json(INDEX_FILE, index)

    print(f"model_id={model_id}")
    print(f"py_file={py_file}")
    print(f"step_file={step_file}")
    print(f"stl_file={stl_file}")
    print(f"stl_name={stl_file.name}")
    print(f"skill_dir={SKILL_DIR}")


def cmd_build(model_id: str) -> None:
    """Run the CAD pipeline for an already-written Python file."""
    index = _idx()
    entry = index.get(model_id)
    if not entry:
        print(f"Model '{model_id}' not found. Use 'list' to see available models.")
        sys.exit(1)

    py_file = Path(entry["py_file"])
    stl_name = Path(entry["stl_file"]).name

    if not py_file.exists():
        print(f"Python file not found: {py_file}")
        sys.exit(1)

    print(f"Building {py_file.name}...")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/step",
            str(py_file.resolve()),
            "--stl",
            stl_name,
            "--skip-explorer",
            "--verbose",
        ],
        cwd=str(SKILL_DIR),
    )

    step_file = Path(entry["step_file"])
    stl_file = Path(entry["stl_file"])
    ok = result.returncode == 0 and step_file.exists()

    entry["built"] = ok
    entry["step_file"] = str(step_file) if step_file.exists() else None
    entry["stl_file"] = str(stl_file) if stl_file.exists() else None
    _save_json(INDEX_FILE, index)

    if ok:
        print(f"\nSTEP: {step_file}")
        print(f"STL:  {stl_file}")
        print(f"\nModel ID: {model_id}")
    else:
        print(f"\nBuild failed (exit {result.returncode}).")
        sys.exit(result.returncode)


def cmd_list() -> None:
    """List all registered models."""
    index = _idx()
    if not index:
        print("No models yet. Ask me to generate one!")
        return
    print(f"{'ID':<10} {'Name':<35} {'Built':<6} {'Created'}")
    print("-" * 70)
    for e in sorted(index.values(), key=lambda x: x["created_at"]):
        built = "yes" if e.get("built") else "no"
        ts = e["created_at"][:16].replace("T", " ")
        print(f"{e['id']:<10} {e['name']:<35} {built:<6} {ts}")


def cmd_view(model_id: str) -> None:
    """Open a model in the 3D viewer."""
    index = _idx()
    entry = index.get(model_id)
    if not entry:
        print(f"Model '{model_id}' not found.")
        return

    step = entry.get("step_file")
    stl = entry.get("stl_file")
    target = step if step and Path(step).exists() else stl

    if not target or not Path(target).exists():
        print(f"No built file for '{model_id}'. Build it first.")
        return

    print(f"Opening viewer for {Path(target).name}...")
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


def cmd_queue(sub: str, rest: list[str]) -> None:
    """Manage the print queue."""
    q = _queue()

    if sub == "list":
        if not q:
            print("Print queue is empty.")
            return
        print(f"{'Job':<10} {'Model':<28} {'Qty':>4} {'Status':<10} {'Added'}")
        print("-" * 68)
        for job in sorted(q.values(), key=lambda j: j["added_at"]):
            ts = job["added_at"][:16].replace("T", " ")
            print(
                f"{job['id']:<10} {job['model_name']:<28} "
                f"{job['quantity']:>4} {job['status']:<10} {ts}"
            )
        return

    if sub == "add":
        if not rest:
            print("Usage: queue add <model_id> [quantity]")
            return
        model_id = rest[0]
        qty = int(rest[1]) if len(rest) > 1 else 1
        index = _idx()
        entry = index.get(model_id)
        if not entry:
            print(f"Model '{model_id}' not found.")
            return
        job_id = str(uuid.uuid4())[:8]
        q[job_id] = {
            "id": job_id,
            "model_id": model_id,
            "model_name": entry["name"],
            "description": entry["description"],
            "stl_file": entry.get("stl_file"),
            "step_file": entry.get("step_file"),
            "status": "pending",
            "quantity": qty,
            "added_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        _save_json(QUEUE_FILE, q)
        print(f"Queued job {job_id}: {qty}x {entry['name']}")
        return

    if sub == "status":
        if len(rest) < 2:
            print("Usage: queue status <job_id> <pending|printing|done|failed>")
            return
        job_id, status = rest[0], rest[1]
        valid = {"pending", "printing", "done", "failed"}
        if status not in valid:
            print(f"Status must be one of: {', '.join(sorted(valid))}")
            return
        if job_id not in q:
            print(f"Job '{job_id}' not found.")
            return
        q[job_id]["status"] = status
        if status == "printing":
            q[job_id]["started_at"] = datetime.now().isoformat()
        elif status in {"done", "failed"}:
            q[job_id]["completed_at"] = datetime.now().isoformat()
        _save_json(QUEUE_FILE, q)
        print(f"Job {job_id} → {status}")
        if status == "done":
            print(f"Add to inventory: inventory add {job_id} <price>")
        return

    print(f"Unknown queue subcommand '{sub}'. Use: list, add, status")


def cmd_inventory(sub: str, rest: list[str]) -> None:
    """Manage sales inventory."""
    inv = _inv()

    if sub == "list":
        if not inv:
            print("Inventory is empty.")
            return
        total_value = sum(i["price"] * i["qty_available"] for i in inv.values())
        total_sold = sum(i["price"] * i["qty_sold"] for i in inv.values())
        print(f"{'Item':<10} {'Name':<28} {'Price':>8} {'Avail':>6} {'Sold':>6}")
        print("-" * 65)
        for item in sorted(inv.values(), key=lambda i: i["added_at"]):
            print(
                f"{item['id']:<10} {item['name']:<28} "
                f"${item['price']:>7.2f} {item['qty_available']:>6} "
                f"{item['qty_sold']:>6}"
            )
        print(f"\nInventory value: ${total_value:.2f}  |  Revenue: ${total_sold:.2f}")
        return

    if sub == "add":
        if len(rest) < 2:
            print("Usage: inventory add <job_id> <price>")
            return
        job_id, price_str = rest[0], rest[1]
        try:
            price = float(price_str)
        except ValueError:
            print(f"Invalid price: {price_str}")
            return
        q = _queue()
        job = q.get(job_id)
        if not job:
            print(f"Job '{job_id}' not found in queue.")
            return
        item_id = str(uuid.uuid4())[:8]
        inv[item_id] = {
            "id": item_id,
            "job_id": job_id,
            "model_id": job["model_id"],
            "name": job["model_name"],
            "description": job["description"],
            "price": price,
            "qty_available": job["quantity"],
            "qty_sold": 0,
            "added_at": datetime.now().isoformat(),
        }
        _save_json(INVENTORY_FILE, inv)
        print(f"Listed {job['quantity']}x {job['model_name']} @ ${price:.2f} (item {item_id})")
        return

    if sub == "sell":
        if len(rest) < 2:
            print("Usage: inventory sell <item_id> <quantity>")
            return
        item_id, qty_str = rest[0], rest[1]
        try:
            qty = int(qty_str)
        except ValueError:
            print(f"Invalid quantity: {qty_str}")
            return
        if item_id not in inv:
            print(f"Item '{item_id}' not found.")
            return
        item = inv[item_id]
        if qty > item["qty_available"]:
            print(f"Only {item['qty_available']} available.")
            return
        item["qty_available"] -= qty
        item["qty_sold"] += qty
        _save_json(INVENTORY_FILE, inv)
        print(f"Sold {qty}x {item['name']} = ${qty * item['price']:.2f}")
        return

    print(f"Unknown inventory subcommand '{sub}'. Use: list, add, sell")


def cmd_summary() -> None:
    """Print farm dashboard."""
    index = _idx()
    q = _queue()
    inv = _inv()

    by_status: dict[str, int] = {}
    for job in q.values():
        s = job["status"]
        by_status[s] = by_status.get(s, 0) + 1

    revenue = sum(i["price"] * i["qty_sold"] for i in inv.values())
    inv_value = sum(i["price"] * i["qty_available"] for i in inv.values())
    built = sum(1 for e in index.values() if e.get("built"))

    print("=== Print Farm Summary ===")
    print(f"Models       : {built} built / {len(index)} total")
    print(f"Queue pending: {by_status.get('pending', 0)}")
    print(f"Printing now : {by_status.get('printing', 0)}")
    print(f"Completed    : {by_status.get('done', 0)}")
    print(f"Inventory    : {len(inv)} listings  (value ${inv_value:.2f})")
    print(f"Revenue      : ${revenue:.2f}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="print_farm_bot",
        description="3D Print Farm Bot — manage and sell 3D prints.",
    )
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    # new — used by Claude Code's /generate to reserve a model slot
    n = sub.add_parser("new", help="Reserve a model slot and print its file paths")
    n.add_argument("name", help="Short model name (no spaces)")
    n.add_argument("description", help="What this model is")

    # build — run CAD pipeline on a registered model
    b = sub.add_parser("build", help="Run the CAD pipeline for a registered model")
    b.add_argument("model_id", help="Model ID from 'list'")

    # list
    sub.add_parser("list", help="List all models")

    # view
    v = sub.add_parser("view", help="Open a model in the 3D viewer")
    v.add_argument("model_id")

    # queue
    qp = sub.add_parser("queue", help="Manage the print queue")
    qp.add_argument("subcommand", nargs="?", default="list",
                    choices=["list", "add", "status"])
    qp.add_argument("rest", nargs="*")

    # inventory
    ip = sub.add_parser("inventory", help="Manage sales inventory")
    ip.add_argument("subcommand", nargs="?", default="list",
                    choices=["list", "add", "sell"])
    ip.add_argument("rest", nargs="*")

    # summary
    sub.add_parser("summary", help="Print farm dashboard")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "new":
        cmd_new(args.name, args.description)
    elif args.command == "build":
        cmd_build(args.model_id)
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
