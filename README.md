# Northwind HW3

An analysis of the Northwind sample database, published as a single web page at
`docs/index.html`. It answers three business questions:

1. Is the business growing?
2. Which products and categories bring in the money?
3. How dependent are we on a few customers?

Every number, table and chart on the page is computed by the Python scripts in
`scripts/` from `data/Northwind_Database.xlsx`. Nothing is typed in by hand, so
rerunning the build after a data change updates the whole page.

## Reproduce from a fresh clone

You need **Python 3.9 or newer** (tested with 3.9.6). Run these from the repo root.

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

   ```bash
   source .venv/bin/activate
   ```

   On Windows, activate with `.venv\Scripts\activate` instead.

2. Install the dependencies (pandas, openpyxl, matplotlib):

   ```bash
   pip install -r requirements.txt
   ```

3. Build the page and charts:

   ```bash
   python scripts/build_site.py
   ```

   This writes `docs/index.html` and the four PNGs in `docs/figures/`, creating
   the folder if needed. The build is deterministic, so running it twice gives
   identical files.

4. View the page by opening `docs/index.html` in a web browser. Use a normal
   browser rather than an editor preview, so the chart images load from
   `docs/figures/`.

`requirements.txt` pins the tested versions (pandas 2.3.3, openpyxl 3.1.5,
matplotlib 3.9.4), so a fresh install reproduces the committed page and charts
byte for byte.

## Repository layout

| Path | Contents |
|---|---|
| `data/Northwind_Database.xlsx` | Source data (read-only) |
| `scripts/analysis.py` | Loads and cleans the data; computes every table |
| `scripts/charts.py` | Draws the charts with matplotlib |
| `scripts/build_site.py` | Entry point: runs the analysis and charts, writes the HTML |
| `docs/index.html` | Generated page |
| `docs/figures/` | Generated charts (a light and a dark version of each) |
| `requirements.txt` | Python dependencies |

## Where each table and chart comes from

All functions are in `scripts/`. Each page section is assembled by the
`section_*` function shown in its heading below, in `build_site.py`.

**Page header** (order count, date range, total revenue): `analysis.data_coverage`
and the `Revenue` column from `analysis.build_order_lines`.

### 1. Is the business growing? (`section_growth`)

| Item on the page | Produced by |
|---|---|
| Chart: net revenue by month (`figures/monthly_revenue.png`) | `charts.monthly_revenue_chart` |
| Table: same months, year over year | `analysis.year_over_year` |
| Table: month by month | `analysis.monthly_trend` |

### 2. Which products and categories bring in the money? (`section_products`)

| Item on the page | Produced by |
|---|---|
| Table: revenue by category | `analysis.category_revenue` |
| Table: top 10 products | `analysis.top_products` |

### 3. How dependent are we on a few customers? (`section_customers`)

| Item on the page | Produced by |
|---|---|
| Chart: customer Pareto (`figures/customer_pareto.png`) | `charts.customer_pareto_chart` |
| Table: concentration summary | `analysis.customer_concentration` |
| Table: top 10 customers | `analysis.customer_revenue` (first 10 rows) |
| Data caveat about suspect customer IDs | `analysis.suspect_customer_orders` |

The `*_dark.png` version of each chart comes from the same function, called with
`mode="dark"` by `charts.draw_all`.

## How the data is handled

- **Revenue** is `UnitPrice × Quantity × (1 − Discount)` from the order lines. It
  uses the price actually charged, not `Product.Price`, because older orders were
  sold below the current list price.
- **Discounts** are rounded to 2 decimals to remove floating-point noise in the
  source file.
- **Product columns that are classroom spreadsheet formulas** (`Cheap`,
  `NewPrice`, `IsCheap` and their duplicates) are ignored.
- **Partial months** at either end of the data are labelled on the page and left
  out of growth comparisons.
- **Orders with a suspect customer ID** stay under the recorded customer and are
  flagged in a note on the page.
