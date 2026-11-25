"""Generate docs/index.html and its charts from the Northwind workbook.

Run with ``python scripts/build_site.py``.
"""

import html

import pandas as pd

import analysis
import charts

OUT_PATH = analysis.REPO_ROOT / "docs" / "index.html"
REPO_URL = "https://github.com/mrazis-jpg/northwind-hw3"


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

def join_and(items):
    """Join words as an English list, e.g. "A, B and C".

    Args:
        items (Iterable[str]): Words to join, in order.

    Returns:
        str: The joined list; a single item is returned unchanged.
    """
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def part(label, body):
    """Wrap one labelled part of a question section.

    Args:
        label (str): Part heading, e.g. ``"Why it matters"``.
        body (str): HTML content of the part.

    Returns:
        str: HTML ``<div>`` with the heading and content.
    """
    return f'<div class="part"><h3>{html.escape(label)}</h3>{body}</div>'


def bullets(items):
    """Render a list of HTML strings as a numbered list.

    Args:
        items (list[str]): List items, already HTML-escaped.

    Returns:
        str: HTML ``<ol>`` element.
    """
    return "<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"


def section_growth(monthly, yoy, cov):
    """Build the HTML section for question 1 (growth).

    Args:
        monthly (pandas.DataFrame): Output of
            ``analysis.monthly_trend``.
        yoy (pandas.DataFrame): Output of ``analysis.year_over_year``.
        cov (dict[str, Any]): Output of ``analysis.data_coverage``.

    Returns:
        str: HTML ``<section>`` with the five labelled parts.
    """
    full = monthly[~monthly["Partial"]]
    best = full["Revenue"].idxmax()
    partial_months = [m.strftime("%b %Y") for m in monthly.index[monthly["Partial"]]]
    mom = monthly["MoMChange"].dropna()

    yoy_sentences = []
    for _, r in yoy.iterrows():
        verb = "grew" if r["Growth"] >= 0 else "fell"
        yoy_sentences.append(
            f"For {html.escape(r['Months'])}, revenue {verb} {pct(abs(r['Growth']))} "
            f"({money(r['PriorRevenue'])} → {money(r['CurrentRevenue'])})."
        )

    # Split the latest year-over-year change into more orders vs bigger orders.
    latest = yoy.iloc[-1]
    order_growth = latest["CurrentOrders"] / latest["PriorOrders"] - 1
    aov_prior = latest["PriorRevenue"] / latest["PriorOrders"]
    aov_current = latest["CurrentRevenue"] / latest["CurrentOrders"]
    aov_growth = aov_current / aov_prior - 1
    run_rate = latest["CurrentRevenue"] / latest["MonthCount"]
    prior_rate = latest["PriorRevenue"] / latest["MonthCount"]
    driver = "the number of orders" if order_growth >= aov_growth else "the size of each order"

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

    why = ("<p>Growth sets how much stock to buy, how many people to staff and what to commit to "
           "suppliers. A manager needs to know whether recent sales are a lasting trend or a "
           "temporary spike before planning around them.</p>")

    approach = (
        f"<p>Net revenue for each order line is added up by the month the order was placed, "
        f"giving {len(monthly)} months. Growth compares the same complete months in consecutive "
        f"years, so seasonal patterns cancel out; {' and '.join(partial_months)} are only partly "
        f"covered by the data, so they are marked “partial” and left out. Order counts and average "
        f"order value show whether growth comes from more orders or bigger ones.</p>"
    )

    evidence = f"""
  {figure("monthly_revenue",
          f"Line chart of net revenue by month from {monthly.index[0].strftime('%b %Y')} to "
          f"{monthly.index[-1].strftime('%b %Y')}; partial months are drawn as hollow points.",
          "Hollow points with dashed links are partial months. Exact values are in the month-by-month table below.")}
  <h4>Same months, year over year</h4>
  {table(yoy_view, {
      "Orders (prior)": integer, "Orders (current)": integer,
      "Revenue (prior)": money, "Revenue (current)": money,
      "Revenue growth": lambda x: pct(x, signed=True)},
      numeric=yoy_view.columns[1:])}
  <h4>Month by month</h4>
  {table(month_view, {
      "Orders": integer, "Revenue": money, "Avg order value": money,
      "Change vs prior month": lambda x: pct(x, signed=True)},
      numeric=month_view.columns[1:])}"""

    finding = (
        f'<p class="answer">{" ".join(yoy_sentences)} Over {html.escape(latest["Months"])}, the number '
        f"of orders changed by {pct(order_growth, signed=True)} ({integer(latest['PriorOrders'])} → "
        f"{integer(latest['CurrentOrders'])}) and average order value by {pct(aov_growth, signed=True)} "
        f"({money(aov_prior)} → {money(aov_current)}), so most of the change comes from {driver}. "
        f"The best complete month was {best.strftime('%B %Y')} at "
        f"{money(full.loc[best, 'Revenue'])}.</p>"
    )

    actions = [
        f"<strong>Plan to the current run rate, not last year’s.</strong> In the latest comparison "
        f"({html.escape(latest['Months'])}), revenue averaged {money(run_rate)} a month against "
        f"{money(prior_rate)} a year earlier. Base purchasing, "
        f"supplier commitments and staffing on the current level.",
        f"<strong>Add capacity where the growth is.</strong> Because growth comes mainly from {driver}, "
        + ("add order-handling and shipping capacity rather than relying on bigger orders."
           if driver == "the number of orders" else
           "protect the large-order customers and products driving it.")
        + (f" {cov['n_unshipped']} orders placed since {day(cov['oldest_unshipped'])} have not shipped yet; "
           f"check that fulfilment is keeping up." if cov["n_unshipped"] else ""),
        f"<strong>Judge each month against the same month last year.</strong> Month-to-month changes "
        f"ranged from {pct(mom.min(), signed=True)} to {pct(mom.max(), signed=True)}, so a single "
        f"weak month is not a reason to react.",
    ]

    return f"""
<section id="growth">
  <h2>1. Is the business growing?</h2>
  {part("Why it matters", why)}
  {part("Approach", approach)}
  {part("Chart and tables", evidence)}
  {part("Main finding", finding)}
  {part("Business implication", bullets(actions))}
</section>"""


def section_products(cats, prods):
    """Build the HTML section for question 2 (products and categories).

    Args:
        cats (pandas.DataFrame): Output of
            ``analysis.category_revenue``.
        prods (pandas.DataFrame): Output of ``analysis.top_products``.

    Returns:
        str: HTML ``<section>`` with the five labelled parts.
    """
    top_cat = cats.iloc[0]
    top_two_share = cats["Share"].head(2).sum()
    n_top = len(prods)
    top_share = prods["CumulativeShare"].iloc[-1]
    leader = prods.iloc[0]
    disc = prods[prods["Discontinued"]]
    gaps = prods["Revenue"].diff(-1).iloc[:-1]
    close_i = int(gaps.idxmin())

    prods_view = prods.assign(Discontinued=prods["Discontinued"].map({True: "Yes", False: ""}))
    prods_view = prods_view.rename(columns={"UnitsSold": "Units sold", "CumulativeShare": "Cumulative share"})
    cats_view = cats.rename(columns={"UnitsSold": "Units sold"})

    why = ("<p>Knowing which products and categories earn the revenue tells a manager where to focus "
           "stock, promotions and supplier negotiations, and which losses would hurt most.</p>")

    approach = (
        f"<p>Net revenue is added up for each of the {len(cats)} categories and for each product, "
        f"then ranked, with each one’s share of total revenue and the running (cumulative) share. "
        f"Products marked discontinued in the product list are flagged.</p>"
        f"<p>The rankings are shown as tables rather than a chart because the point is exact order "
        f"and share: a table puts rank, revenue, share, cumulative share and discontinued status side "
        f"by side, while bars of similar length are hard to tell apart. For example, "
        f"{html.escape(prods['Product'].iloc[close_i])} and "
        f"{html.escape(prods['Product'].iloc[close_i + 1])} (ranks {close_i + 1} and {close_i + 2}) "
        f"differ by only {money(gaps.iloc[close_i])}.</p>"
    )

    evidence = f"""
  <h4>Revenue by category</h4>
  {table(cats_view, {"Products": integer, "Units sold": integer, "Revenue": money, "Share": pct},
         numeric=["Products", "Units sold", "Revenue", "Share"])}
  <h4>Top {n_top} products</h4>
  {table(prods_view, {"Rank": integer, "Units sold": integer, "Revenue": money,
                      "Share": pct, "Cumulative share": pct},
         numeric=["Rank", "Units sold", "Revenue", "Share", "Cumulative share"])}"""

    disc_text = (
        f" {len(disc)} of the top {n_top} {'is' if len(disc) == 1 else 'are'} marked discontinued: "
        f"{html.escape(join_and(disc['Product']))}." if len(disc) else ""
    )
    finding = (
        f'<p class="answer">{html.escape(top_cat["Category"])} is the largest category with '
        f"{pct(top_cat['Share'])} of revenue; the top two categories together make up "
        f"{pct(top_two_share)}. The top {n_top} products alone account for {pct(top_share)} of all "
        f"revenue, and {html.escape(leader['Product'])} by itself brings in {pct(leader['Share'])}."
        f"{disc_text}</p>"
    )

    actions = [
        f"<strong>Protect the best seller.</strong> Make sure {html.escape(leader['Product'])} "
        f"({html.escape(leader['Category'])}, {money(leader['Revenue'])}) never runs out of stock, "
        f"and secure its supply terms. It earns {leader['Revenue'] / prods['Revenue'].iloc[1]:.1f} times "
        f"the revenue of the next product, {html.escape(prods['Product'].iloc[1])}.",
    ]
    if len(disc):
        disc_cats = join_and(sorted(set(disc["Category"])))
        actions.append(
            f"<strong>Replace the discontinued top sellers now.</strong> {html.escape(join_and(disc['Product']))} "
            f"brought in {money(disc['Revenue'].sum())} ({pct(disc['Share'].sum())} of revenue). Find "
            f"replacement products in {html.escape(disc_cats)} and move their customers over before "
            f"remaining stock sells out."
        )

    return f"""
<section id="products">
  <h2>2. Which products and categories bring in the money?</h2>
  {part("Why it matters", why)}
  {part("Approach", approach)}
  {part("Tables", evidence)}
  {part("Main finding", finding)}
  {part("Business implication", bullets(actions))}
</section>"""


def section_customers(conc, stats, top_cust, suspect, data_end, lapse_days=90):
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
        data_end (pandas.Timestamp): Date of the last order in the data.
        lapse_days (int): Days without an order before a top customer
            is flagged as lapsing.

    Returns:
        str: HTML ``<section>`` with the five labelled parts.
    """
    top3 = top_cust.head(3)
    top3_names = [html.escape(n) for n in top3["Customer"]]
    top3_list = join_and(top3_names)
    top3_share = top3["Share"].sum()
    rest_of_top10 = top_cust.iloc[3:]
    lapsing = top_cust[(data_end - top_cust["LastOrder"]).dt.days > lapse_days]

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
            f"({pct(suspect['share'])} of revenue){impact}. The customer on these orders should be "
            f"corrected so account reviews use accurate figures.</p>"
        )

    why = ("<p>When a few customers supply most of the revenue, losing one of them can wipe out a "
           "year’s growth, and those customers gain leverage over prices and terms. A manager needs "
           "to know how exposed the business is and to whom.</p>")

    approach = (
        f"<p>Net revenue is added up for each of the {stats['n_customers_ordering']} customers who "
        f"ordered, then customers are ranked from largest to smallest. The running share shows how "
        f"many customers it takes to reach 50% and 80% of revenue (a Pareto analysis). Each top "
        f"customer’s last order date shows whether they are still active. Orders whose shipping "
        f"details point to a different customer are checked and reported.</p>"
    )

    evidence = f"""
  {figure("customer_pareto",
          f"Pareto chart: bars show revenue for each of {stats['n_customers_ordering']} customers ranked "
          f"from largest to smallest; a line below shows cumulative share, reaching 80% at customer "
          f"{stats['needed_for_80']}.",
          "Top panel: revenue per customer, largest first. Bottom panel: running share of total revenue.")}
  <h4>Concentration summary</h4>
  {table(conc_view, {}, numeric=["Value"])}
  <h4>Top {len(top_cust)} customers</h4>
  {table(cust_view, {"Rank": integer, "Orders": integer, "Revenue": money, "Share": pct,
                     "Cumulative share": pct, "Last order": day},
         numeric=["Rank", "Orders", "Revenue", "Share", "Cumulative share"])}
  {suspect_note}"""

    finding = (
        f'<p class="answer">The top three customers, {top3_list}, bring in {pct(top3_share)} of '
        f"revenue between them, more than the other {len(rest_of_top10)} customers in the top 10 "
        f"combined ({pct(rest_of_top10['Share'].sum())}). The top 10 bring in "
        f"{pct(stats['top_10_share'])}, and {stats['needed_for_80']} of "
        f"{stats['n_customers_ordering']} ordering customers make up 80%.</p>"
    ) if top3_share > rest_of_top10["Share"].sum() else (
        f'<p class="answer">The top three customers, {top3_list}, bring in {pct(top3_share)} of '
        f"revenue between them. The top 10 bring in {pct(stats['top_10_share'])}, and "
        f"{stats['needed_for_80']} of {stats['n_customers_ordering']} ordering customers make up 80%.</p>"
    )

    actions = [
        f"<strong>Treat {top3_list} as key accounts.</strong> Give each a named account manager, "
        f"review their orders monthly and agree supply and pricing terms that make them less likely "
        f"to leave. Losing any one of them would cost about {pct(top3['Share'].min())}–"
        f"{pct(top3['Share'].max())} of revenue.",
        f"<strong>Reduce the dependence by growing the next tier.</strong> Customers ranked 4 to "
        f"{stats['needed_for_80']} each bring in at most {money(top_cust['Revenue'].iloc[3])}. Target "
        f"them with promotions and sales visits, and track the top-three share (now {pct(top3_share)}) "
        f"each quarter as the measure of progress.",
    ]
    if len(lapsing):
        names = ", ".join(f"{html.escape(c)} (last order {day(d)})"
                          for c, d in zip(lapsing["Customer"], lapsing["LastOrder"]))
        actions.append(
            f"<strong>Call top customers who have gone quiet.</strong> {names} "
            f"{'has' if len(lapsing) == 1 else 'have'} not ordered in over {lapse_days} days before "
            f"the end of the data."
        )

    return f"""
<section id="customers">
  <h2>3. How dependent are we on a few customers?</h2>
  {part("Why it matters", why)}
  {part("Approach", approach)}
  {part("Chart and tables", evidence)}
  {part("Main finding", finding)}
  {part("Business implication", bullets(actions))}
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
.part { margin: 20px 0; }
.part h3 { font-size: .8rem; margin: 0 0 6px; color: var(--accent); text-transform: uppercase; letter-spacing: .08em; }
.part p { margin: 0 0 10px; }
.part ol { margin: 0; padding-left: 22px; }
.part li { margin-bottom: 8px; }
h4 { font-size: .95rem; margin: 20px 0 8px; color: var(--muted); }
.repo { font-size: .9rem; margin: 8px 0 12px; }
.repo a, nav a { color: var(--accent); }
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
  <p class="repo">Code and data: <a href="{REPO_URL}">{REPO_URL.removeprefix("https://")}</a></p>
  <nav><a href="#growth">Growth</a><a href="#products">Products</a><a href="#customers">Customers</a></nav>
  {section_growth(monthly, yoy, cov)}
  {section_products(cats, prods)}
  {section_customers(conc, stats, cust.head(10), suspect, cov['last_order'])}
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
