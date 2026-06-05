Manage the print farm sales inventory.

Parse $ARGUMENTS to determine what to do:

- No args → show inventory: `python print_farm_bot.py inventory`
- "add <job_id> <price>" → `python print_farm_bot.py inventory add <job_id> <price>`
- "sell <item_id> <qty>" → `python print_farm_bot.py inventory sell <item_id> <qty>`

Run the appropriate command and show the output. After a sale, show the updated summary with `python print_farm_bot.py summary`.
