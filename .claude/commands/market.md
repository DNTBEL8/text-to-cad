Show the 3D print farm market intelligence report and recommend what to make next.

Read the market guide:
```bash
cat print_farm/MARKET.md
```

Also show current model list:
```bash
python print_farm_bot.py list
```

Then give the user a personalized recommendation:
1. Which category from MARKET.md has the best ROI for a print farm right now
2. Suggest 3 specific designs to generate next (use the "Top 10 designs" list + gap analysis vs what they already have)
3. Ask if they want you to generate any of them right now

If they say yes to generating, run the full generate → build → review flow for each one.
