# Northwind HW3

Analysis of the Northwind sample database, published as a webpage under `docs/`.

## Data

- Source: `data/Northwind_Database.xlsx` (the only data source; treat it as read-only).
- Sheets: `Categories`, `Customers`, `Employees`, `Orders Details`, `Orders`, `Shippers`, `Product`, `Suppliers`.
- Load with `pandas.read_excel(path, sheet_name=...)` (needs `openpyxl`).

## Rules

1. **Python only.** All analysis and chart code is Python. No R, no Excel formulas, no JavaScript charting, no numbers worked out by hand.
2. **Every number on the webpage comes from a script in this repo.** Each figure, table value, and statistic quoted in `docs/` must come from a Python script checked into this repo that reads `data/Northwind_Database.xlsx`.
3. **Never hard-code results.** Don't paste computed values (totals, counts, percentages, top-N lists) into the page or into scripts. Scripts compute them from the data and write them out (e.g. to generated HTML/Markdown, or a JSON/CSV the page reads). If the data changes, rerunning the scripts must update every number.
4. **Charts go in `docs/figures/`.** Every chart is saved there by a script (e.g. `plt.savefig("docs/figures/<name>.png", dpi=150, bbox_inches="tight")`). Create the folder from code if it's missing; don't save charts anywhere else.
5. **Keep `requirements.txt` up to date.** Whenever a script imports a third-party package, add it to `requirements.txt` in the same change. Remove packages that are no longer used.

## Workflow

- Set up: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Rerun every analysis script after changing code or data, then check that the page in `docs/` matches the fresh output.
- Use paths relative to the repo root so scripts run from a clean checkout.
