Review a model's geometry to confirm it's ready to sell.

If $ARGUMENTS is empty, run `python print_farm_bot.py list` and ask which model to review.

Otherwise run:
```bash
python print_farm_bot.py review $ARGUMENTS
```

Read the output and tell the user clearly:
- PASS or FAIL on watertightness (non-watertight = can't print reliably)
- Exact dimensions in mm
- Estimated material cost and suggested minimum price (4× material cost is a common baseline)
- Whether it's already approved or needs approval

If it passes, ask: "Should I approve this for sale?"
If approved, run: `python print_farm_bot.py approve $ARGUMENTS`
