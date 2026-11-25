"""Generate docs/index.html and its charts from the Northwind workbook.

Run with ``python scripts/build_site.py``.
"""

import html

import pandas as pd

import analysis
import charts

OUT_PATH = analysis.REPO_ROOT / "docs" / "index.html"


def figure(name, alt, caption):
    """Build HTML embedding a chart, with a dark-mode version.

    Args:
        name (str): Chart file name in docs/figures/, without extension.
        alt (str): Alternative text for the image.
        caption (str): Caption shown under the chart.

    Returns:
        str: HTML ``<figure>`` element.
    """
    return (f'<figure><picture>'
            f'<source srcset="figures/{name}_dark.png" media="(prefers-color-scheme: dark)">'
            f'<img src="figures/{name}.png" alt="{html.escape(alt)}" loading="lazy"></picture>'
            f'<figcaption>{html.escape(caption)}</figcaption></figure>')


# ---------------------------------------------------------------- formatting

def money(x):
    """Format an amount as whole dollars.

    Args:
        x (float): Amount in dollars.

    Returns:
        str: Text such as ``"$1,234"``.
    """
    return f"${x:,.0f}"


def pct(x, signed=False):
    """Format a fraction as a percentage with one decimal place.

    Args:
        x (float): Fraction, e.g. 0.25 for 25%; NaN gives an em dash.
        signed (bool): Whether to prefix positive values with ``+``.

    Returns:
        str: Text such as ``"25.0%"`` or ``"+25.0%"``.
    """
    if pd.isna(x):
        return "—"
    return f"{x:+.1%}" if signed else f"{x:.1%}"


def integer(x):
    """Format a whole number with thousands separators.

    Args:
        x (int | float): Number; any fraction is truncated.

    Returns:
        str: Text such as ``"1,234"``.
    """
    return f"{int(x):,}"


def day(ts):
    """Format a timestamp as an ISO date.

    Args:
        ts (pandas.Timestamp): Date to format.

    Returns:
        str: Text such as ``"1998-05-06"``.
    """
    return ts.strftime("%Y-%m-%d")


def table(df, formats, numeric=(), caption=None):
    """Render a DataFrame as an HTML table with per-column formatting.

    Args:
        df (pandas.DataFrame): Rows to render, in column order.
        formats (dict[str, Callable[[Any], str]]): Formatter for each
            column; unlisted columns use ``str``.
        numeric (Collection[str]): Columns to right-align.
        caption (str | None): Caption above the table; None for none.

    Returns:
        str: HTML table wrapped in a scrollable ``<div>``.
    """
    head = "".join(
        f'<th class="{"num" if c in numeric else ""}">{html.escape(str(c))}</th>' for c in df.columns
    )
    body = []
    for _, row in df.iterrows():
        cells = []
        for c in df.columns:
            text = formats.get(c, str)(row[c])
            cls = "num" if c in numeric else ""
            cells.append(f'<td class="{cls}">{html.escape(text)}</td>')
        body.append(f"<tr>{''.join(cells)}</tr>")
    cap = f"<caption>{html.escape(caption)}</caption>" if caption else ""
    return (f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead>'
            f"<tbody>{''.join(body)}</tbody></table></div>")


# ---------------------------------------------------------------- sections

def section_growth(monthly, yoy):
    """Build the HTML section for question 1 (growth).

    Args:
        monthly (pandas.DataFrame): Output of
            ``analysis.monthly_trend``.
        yoy (pandas.DataFrame): Output of ``analysis.year_over_year``.

    Returns:
        str: HTML ``<section>`` with summary, chart and two tables.
    """
    full = monthly[~monthly["Partial"]]
    best = full["Revenue"].idxmax()
    partial_months = [m.strftime("%b %Y") for m in monthly.index[monthly["Partial"]]]

    yoy_sentences = []
    for _, r in yoy.iterrows():
        verb = "grew" if r["Growth"] >= 0 else "fell"
        yoy_sentences.append(
            f"For {html.escape(r['Months'])}, revenue {verb} {pct(abs(r['Growth']))} "
            f"({money(r['PriorRevenue'])} → {money(r['CurrentRevenue'])})."
        )

    yoy_view = yoy.rename(columns={
        "Months": "Comparison", "PriorOrders": "Orders (prior)", "CurrentOrders": "Orders (current)",
        "PriorRevenue": "Revenue (prior)", "CurrentRevenue": "Revenue (current)", "Growth": "Revenue growth",
    })[["Comparison", "Orders (prior)", "Orders (current)", "Revenue (prior)", "Revenue (current)", "Revenue growth"]]

    month_view = monthly.reset_index()
    month_view["Month"] = [
        m.strftime("%b %Y") + (" (partial)" if p else "") for m, p in zip(month_view["Month"], month_view["Partial"])
    ]
    month_view = month_view.rename(columns={"AvgOrderValue": "Avg order value", "MoMChange": "Change vs prior month"})
    month_view = month_view[["Month", "Orders", "Revenue", "Avg order value", "Change vs prior month"]]

    return f"""
<section id="growth">
  <h2>1. Is the business growing?</h2>
  <p class="answer">{' '.join(yoy_sentences)} The best complete month was
  {best.strftime('%B %Y')} at {money(full.loc[best, 'Revenue'])}.</p>
  <p class="note">Comparisons use only months that are complete in both years.
  {' and '.join(partial_months)} are only partly covered by the data, so they are marked
  “partial” and left out of growth figures.</p>
  {figure("monthly_revenue",
          f"Line chart of net revenue by month from {monthly.index[0].strftime('%b %Y')} to "
          f"{monthly.index[-1].strftime('%b %Y')}; partial months are drawn as hollow points.",
          "Hollow points with dashed links are partial months. Exact values are in the month-by-month table below.")}
  <h3>Same months, year over year</h3>
  {table(yoy_view, {
      "Orders (prior)": integer, "Orders (current)": integer,
      "Revenue (prior)": money, "Revenue (current)": money,
      "Revenue growth": lambda x: pct(x, signed=True)},
      numeric=yoy_view.columns[1:])}
  <h3>Month by month</h3>
  {table(month_view, {
      "Orders": integer, "Revenue": money, "Avg order value": money,
      "Change vs prior month": lambda x: pct(x, signed=True)},
      numeric=month_view.columns[1:])}
</section>"""


def section_products(cats, prods):
    """Build the HTML section for question 2 (products and categories).

    Args:
        cats (pandas.DataFrame): Output of
            ``analysis.category_revenue``.
        prods (pandas.DataFrame): Output of ``analysis.top_products``.

    Returns:
        str: HTML ``<section>`` with summary and two tables.
    """
    top_cat = cats.iloc[0]
    top_two_share = cats["Share"].head(2).sum()
    n_top = len(prods)
    top_share = prods["CumulativeShare"].iloc[-1]
    n_disc = int(prods["Discontinued"].sum())
    disc_names = ", ".join(prods.loc[prods["Discontinued"], "Product"])
    disc_text = (
        f" {n_disc} of the top {n_top} {'is' if n_disc == 1 else 'are'} marked discontinued "
        f"({html.escape(disc_names)}), so that revenue will need replacing."
        if n_disc else ""
    )
    prods_view = prods.assign(Discontinued=prods["Discontinued"].map({True: "Yes", False: ""}))
    prods_view = prods_view.rename(columns={"UnitsSold": "Units sold", "CumulativeShare": "Cumulative share"})
    cats_view = cats.rename(columns={"UnitsSold": "Units sold"})

    return f"""
<section id="products">
  <h2>2. Which products and categories bring in the money?</h2>
  <p class="answer">{html.escape(top_cat['Category'])} is the largest category with
  {pct(top_cat['Share'])} of revenue; the top two categories together make up {pct(top_two_share)}.
  The top {n_top} products alone account for {pct(top_share)} of all revenue.{disc_text}</p>
  <h3>Revenue by category</h3>
  {table(cats_view, {"Products": integer, "Units sold": integer, "Revenue": money, "Share": pct},
         numeric=["Products", "Units sold", "Revenue", "Share"])}
  <h3>Top {n_top} products</h3>
  {table(prods_view, {"Rank": integer, "Units sold": integer, "Revenue": money,
                      "Share": pct, "Cumulative share": pct},
         numeric=["Rank", "Units sold", "Revenue", "Share", "Cumulative share"])}
</section>"""


def section_customers(conc, stats, top_cust, suspect):
    """Build the HTML section for question 3 (customer concentration).

    Args:
        conc (pandas.DataFrame): Display table from
            ``analysis.customer_concentration``.
        stats (dict[str, Any]): Number dict from
            ``analysis.customer_concentration``.
        top_cust (pandas.DataFrame): Top rows of
            ``analysis.customer_revenue``.
        suspect (dict[str, Any]): Output of
            ``analysis.suspect_customer_orders``.

    Returns:
        str: HTML ``<section>`` with summary, chart, two tables and an
        optional data caveat.
    """
    leader = top_cust.iloc[0]
    conc_view = conc.copy()
    conc_view["Value"] = [pct(v) if k == "pct" else integer(v) for v, k in zip(conc["Value"], conc["Kind"])]
    conc_view = conc_view[["Measure", "Value"]]

    cust_view = top_cust.rename(columns={"CumulativeShare": "Cumulative share", "LastOrder": "Last order"})

    suspect_note = ""
    if suspect["order_ids"]:
        ids = ", ".join(str(i) for i in suspect["order_ids"])
        impact = ", too little to change the picture" if suspect["share"] < 0.01 else ""
        suspect_note = (
            f'<p class="note">Data caveat: {len(suspect["order_ids"])} orders ({ids}) ship to a different '
            f"company and country than the customer recorded on them, so their customer ID may be wrong. "
            f"They are counted under the recorded customer; together they are {money(suspect['revenue'])} "
            f"({pct(suspect['share'])} of revenue){impact}.</p>"
        )

    return f"""
<section id="customers">
  <h2>3. How dependent are we on a few customers?</h2>
  <p class="answer">The top 10 customers bring in {pct(stats['top_10_share'])} of revenue, and just
  {stats['needed_for_80']} of {stats['n_customers_ordering']} ordering customers make up 80%.
  The largest, {html.escape(leader['Customer'])} ({html.escape(leader['Country'])}), alone accounts for
  {pct(leader['Share'])}.</p>
  {figure("customer_pareto",
          f"Pareto chart: bars show revenue for each of {stats['n_customers_ordering']} customers ranked "
          f"from largest to smallest; a line below shows cumulative share, reaching 80% at customer "
          f"{stats['needed_for_80']}.",
          "Top panel: revenue per customer, largest first. Bottom panel: running share of total revenue.")}
  <h3>Concentration summary</h3>
  {table(conc_view, {}, numeric=["Value"])}
  <h3>Top {len(top_cust)} customers</h3>
  {table(cust_view, {"Rank": integer, "Orders": integer, "Revenue": money, "Share": pct,
                     "Cumulative share": pct, "Last order": day},
         numeric=["Rank", "Orders", "Revenue", "Share", "Cumulative share"])}
  {suspect_note}
</section>"""


# ---------------------------------------------------------------- page

CSS = """
:root { --bg:#fbfbf9; --fg:#1d1d1b; --muted:#66655f; --line:#e2e0d8; --accent:#2f5d8a; --stripe:#f3f2ed; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#17181a; --fg:#e8e6e1; --muted:#a09d95; --line:#33343a; --accent:#8db4dc; --stripe:#1f2023; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font:16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
main { max-width: 920px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 1.8rem; margin: 0 0 4px; }
h2 { font-size: 1.35rem; margin: 48px 0 8px; padding-top: 16px; border-top: 1px solid var(--line); }
h3 { font-size: 1rem; margin: 24px 0 8px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.sub, .note { color: var(--muted); }
.note { font-size: .9rem; }
.answer { font-size: 1.05rem; border-left: 3px solid var(--accent); padding-left: 12px; }
nav a { color: var(--accent); margin-right: 16px; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .92rem; font-variant-numeric: tabular-nums; }
th, td { padding: 6px 10px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
th { font-weight: 600; border-bottom: 2px solid var(--line); }
tbody tr:nth-child(even) { background: var(--stripe); }
.num { text-align: right; }
figure { margin: 16px 0 8px; }
figure img { display: block; width: 100%; height: auto; }
figcaption { font-size: .85rem; color: var(--muted); margin-top: 6px; }
footer { margin-top: 48px; font-size: .85rem; color: var(--muted); }
"""


def build_page():
    """Run every analysis, draw the charts and assemble the page.

    Also writes the chart PNGs to docs/figures/ as a side effect.

    Args:
        None.

    Returns:
        str: Complete HTML document.
    """
    tables = analysis.load_tables()
    lines = analysis.build_order_lines(tables)
    cov = analysis.data_coverage(tables)

    monthly = analysis.monthly_trend(lines)
    yoy = analysis.year_over_year(monthly)
    cats = analysis.category_revenue(lines, tables)
    prods = analysis.top_products(lines, n=10)
    cust = analysis.customer_revenue(lines)
    conc, stats = analysis.customer_concentration(cust, tables)
    suspect = analysis.suspect_customer_orders(tables, lines)
    charts.draw_all(monthly, cust)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Northwind Sales Review</title>
<style>{CSS}</style>
</head>
<body>
<main>
  <h1>Northwind Sales Review</h1>
  <p class="sub">{integer(cov['n_orders'])} orders ({integer(cov['n_lines'])} order lines) placed between
  {day(cov['first_order'])} and {day(cov['last_order'])}, totalling {money(lines['Revenue'].sum())}
  in net revenue.</p>
  <nav><a href="#growth">Growth</a><a href="#products">Products</a><a href="#customers">Customers</a></nav>
  {section_growth(monthly, yoy)}
  {section_products(cats, prods)}
  {section_customers(conc, stats, cust.head(10), suspect)}
  <footer>
    <p>Revenue = unit price on the order line × quantity × (1 − discount), using the price actually
    charged rather than today's list price. Orders are dated by order date; {cov['n_unshipped']}
    orders had not shipped yet and are included.</p>
    <p>Generated by <code>scripts/build_site.py</code> from <code>data/Northwind_Database.xlsx</code>.
    Data through {day(cov['last_order'])}.</p>
  </footer>
</main>
</body>
</html>
"""


def main():
    """Build the page and write it to docs/index.html.

    Args:
        None.

    Returns:
        None. Writes docs/index.html and prints its path.
    """
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_page(), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(analysis.REPO_ROOT)}")


if __name__ == "__main__":
    main()
