Manage the 3D print queue.

Parse $ARGUMENTS to determine what to do:

- No args → show queue: `python print_farm_bot.py queue`
- "add <model_id>" → `python print_farm_bot.py queue add <model_id>`
- "add <model_id> <qty>" → `python print_farm_bot.py queue add <model_id> <qty>`
- "printing <job_id>" → `python print_farm_bot.py queue status <job_id> printing`
- "done <job_id>" → `python print_farm_bot.py queue status <job_id> done`
- "failed <job_id>" → `python print_farm_bot.py queue status <job_id> failed`

Run the appropriate command and show the output. After marking a job done, remind the user they can add it to inventory with `/inventory add <job_id> <price>`.
