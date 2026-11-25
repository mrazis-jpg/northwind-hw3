"""Load the Northwind workbook and compute the tables behind the page.

Covers growth, product/category revenue and customer concentration.
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "Northwind_Database.xlsx"


def load_tables(path=DATA_PATH):
    """Read every sheet of the Northwind workbook.

    Args:
        path (str | pathlib.Path): Workbook location; defaults to
            ``data/Northwind_Database.xlsx`` in the repo.

    Returns:
        dict[str, pandas.DataFrame]: Each sheet keyed by sheet name.
    """
    return pd.read_excel(path, sheet_name=None)


def build_order_lines(tables):
    """Join order lines to orders, products, categories and customers.

    Revenue uses the price charged on each line, not ``Product.Price``,
    since older orders were sold below list price. Discounts are rounded
    to 2 decimals to remove float noise; Product's Excel-formula columns
    are ignored.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        pandas.DataFrame: One row per order line, with net ``Revenue``
        plus order date, product, category and customer columns.
    """
    details = tables["Orders Details"].copy()
    details["Discount"] = details["Discount"].round(2)
    details["Revenue"] = details["UnitPrice"] * details["Quantity"] * (1 - details["Discount"])

    orders = tables["Orders"][["OrderID", "CustomerID", "OrderDate"]]
    products = tables["Product"][["ProductID", "ProductName", "CategoryID", "Discontinued"]]
    categories = tables["Categories"][["CategoryID", "CategoryName"]]
    customers = tables["Customers"][["CustomerID", "CompanyName", "Country"]]

    lines = (
        details.merge(orders, on="OrderID", how="left", validate="many_to_one")
        .merge(products, on="ProductID", how="left", validate="many_to_one")
        .merge(categories, on="CategoryID", how="left", validate="many_to_one")
        .merge(customers, on="CustomerID", how="left", validate="many_to_one")
    )
    return lines


def data_coverage(tables):
    """Summarise the date range and size of the order data.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        dict[str, Any]: ``first_order`` and ``last_order``
        (pandas.Timestamp), ``n_orders`` and ``n_lines`` (int), and
        ``n_unshipped`` (int, orders with no ``ShippedDate``).
    """
    orders = tables["Orders"]
    return {
        "first_order": orders["OrderDate"].min(),
        "last_order": orders["OrderDate"].max(),
        "n_orders": len(orders),
        "n_lines": len(tables["Orders Details"]),
        "n_unshipped": int(orders["ShippedDate"].isna().sum()),
    }


def monthly_trend(lines):
    """Compute revenue, orders and average order value per month.

    A month is flagged partial when the data does not span all of it,
    which marks both the first and the last month in the data.
    Month-over-month change into or out of a partial month is NaN.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.

    Returns:
        pandas.DataFrame: Indexed by monthly ``Period`` with ``Orders``,
        ``Revenue``, ``AvgOrderValue``, ``Partial`` (bool) and
        ``MoMChange`` (fraction) columns.
    """
    month = lines["OrderDate"].dt.to_period("M")
    monthly = lines.groupby(month).agg(Orders=("OrderID", "nunique"), Revenue=("Revenue", "sum"))
    monthly.index.name = "Month"
    monthly["AvgOrderValue"] = monthly["Revenue"] / monthly["Orders"]

    first_day, last_day = lines["OrderDate"].min(), lines["OrderDate"].max()
    starts = monthly.index.to_timestamp(how="start")
    ends = monthly.index.to_timestamp(how="end").normalize()
    monthly["Partial"] = (starts < first_day) | (ends > last_day)

    monthly["MoMChange"] = monthly["Revenue"].pct_change()
    # A change into or out of a partial month is not meaningful.
    partial_involved = monthly["Partial"] | monthly["Partial"].shift(1, fill_value=False)
    monthly.loc[partial_involved, "MoMChange"] = float("nan")
    return monthly


def year_over_year(monthly):
    """Compare revenue for the same complete months year over year.

    Only months complete in both years are compared.

    Args:
        monthly (pandas.DataFrame): Output of ``monthly_trend``.

    Returns:
        pandas.DataFrame: One row per year with a prior year to compare:
        ``Months`` (label), ``PriorRevenue``, ``CurrentRevenue``,
        ``PriorOrders``, ``CurrentOrders`` and ``Growth`` (fraction).
    """
    full = monthly[~monthly["Partial"]].copy()
    full["Year"] = full.index.year
    full["MonthNum"] = full.index.month

    rows = []
    for year in sorted(full["Year"].unique())[1:]:
        prior = full[full["Year"] == year - 1].set_index("MonthNum")
        current = full[full["Year"] == year].set_index("MonthNum")
        common = sorted(set(prior.index) & set(current.index))
        if not common:
            continue
        first = pd.Timestamp(year=year, month=common[0], day=1).strftime("%b")
        last = pd.Timestamp(year=year, month=common[-1], day=1).strftime("%b")
        prior_rev = prior.loc[common, "Revenue"].sum()
        current_rev = current.loc[common, "Revenue"].sum()
        rows.append({
            "Months": f"{first}–{last} {year} vs {year - 1}",
            "PriorRevenue": prior_rev,
            "CurrentRevenue": current_rev,
            "PriorOrders": prior.loc[common, "Orders"].sum(),
            "CurrentOrders": current.loc[common, "Orders"].sum(),
            "Growth": current_rev / prior_rev - 1,
        })
    return pd.DataFrame(rows)


def category_revenue(lines, tables):
    """Compute revenue, share and volume for each product category.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``; used to count catalogue products.

    Returns:
        pandas.DataFrame: Sorted by revenue, with ``Category``,
        ``Products``, ``UnitsSold``, ``Revenue`` and ``Share``
        (fraction) columns.
    """
    products_per_cat = (
        tables["Product"].merge(tables["Categories"], on="CategoryID")
        .groupby("CategoryName")["ProductID"].nunique()
    )
    by_cat = lines.groupby("CategoryName").agg(UnitsSold=("Quantity", "sum"), Revenue=("Revenue", "sum"))
    by_cat["Products"] = products_per_cat
    by_cat["Share"] = by_cat["Revenue"] / by_cat["Revenue"].sum()
    by_cat = by_cat.sort_values("Revenue", ascending=False).reset_index()
    by_cat = by_cat.rename(columns={"CategoryName": "Category"})
    return by_cat[["Category", "Products", "UnitsSold", "Revenue", "Share"]]


def top_products(lines, n=10):
    """Rank products by revenue and return the top ``n``.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.
        n (int): Number of products to return.

    Returns:
        pandas.DataFrame: ``Rank``, ``Product``, ``Category``,
        ``UnitsSold``, ``Revenue``, ``Share``, ``CumulativeShare`` and
        ``Discontinued`` columns; shares are fractions of all revenue.
    """
    by_prod = (
        lines.groupby(["ProductName", "CategoryName", "Discontinued"])
        .agg(UnitsSold=("Quantity", "sum"), Revenue=("Revenue", "sum"))
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    by_prod["Share"] = by_prod["Revenue"] / lines["Revenue"].sum()
    by_prod["CumulativeShare"] = by_prod["Share"].cumsum()
    by_prod.insert(0, "Rank", range(1, len(by_prod) + 1))
    by_prod = by_prod.rename(columns={"ProductName": "Product", "CategoryName": "Category"})
    cols = ["Rank", "Product", "Category", "UnitsSold", "Revenue", "Share", "CumulativeShare", "Discontinued"]
    return by_prod[cols].head(n).reset_index(drop=True)


def customer_revenue(lines):
    """Rank every ordering customer by revenue.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.

    Returns:
        pandas.DataFrame: Sorted by revenue, with ``Rank``,
        ``Customer``, ``Country``, ``Orders``, ``Revenue``, ``Share``,
        ``CumulativeShare`` and ``LastOrder`` columns.
    """
    by_cust = (
        lines.groupby(["CustomerID", "CompanyName", "Country"])
        .agg(Orders=("OrderID", "nunique"), Revenue=("Revenue", "sum"), LastOrder=("OrderDate", "max"))
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    by_cust["Share"] = by_cust["Revenue"] / by_cust["Revenue"].sum()
    by_cust["CumulativeShare"] = by_cust["Share"].cumsum()
    by_cust.insert(0, "Rank", range(1, len(by_cust) + 1))
    by_cust = by_cust.rename(columns={"CompanyName": "Customer"})
    cols = ["Rank", "Customer", "Country", "Orders", "Revenue", "Share", "CumulativeShare", "LastOrder"]
    return by_cust[cols].reset_index(drop=True)


def customer_concentration(cust, tables, top_ns=(1, 5, 10), share_targets=(0.5, 0.8)):
    """Summarise how concentrated revenue is across customers.

    Args:
        cust (pandas.DataFrame): Output of ``customer_revenue``.
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``; used to count all customers.
        top_ns (tuple[int, ...]): Sizes N for "top N customers' share"
            rows.
        share_targets (tuple[float, ...]): Revenue fractions for
            "customers needed to reach X" rows.

    Returns:
        tuple[pandas.DataFrame, dict[str, Any]]: Display table with
        ``Measure``, ``Value`` and ``Kind`` (``"pct"`` or ``"int"``)
        columns, and a dict of the same numbers keyed for prose (e.g.
        ``top_10_share``, ``needed_for_80``).
    """
    n_cust = len(cust)
    top_20pct_n = max(1, round(n_cust * 0.2))
    stats = {
        "n_customers_total": len(tables["Customers"]),
        "n_customers_ordering": n_cust,
        "n_customers_no_orders": len(tables["Customers"]) - n_cust,
        "top_20pct_n": top_20pct_n,
        "top_20pct_share": cust["Share"].head(top_20pct_n).sum(),
    }
    rows = []
    for n in top_ns:
        share = cust["Share"].head(n).sum()
        stats[f"top_{n}_share"] = share
        label = "Top customer" if n == 1 else f"Top {n} customers"
        rows.append({"Measure": f"{label}: share of revenue", "Value": share, "Kind": "pct"})
    rows.append({"Measure": f"Top 20% of customers ({top_20pct_n}): share of revenue",
                 "Value": stats["top_20pct_share"], "Kind": "pct"})
    for target in share_targets:
        needed = int((cust["CumulativeShare"] < target).sum() + 1)
        stats[f"needed_for_{int(target * 100)}"] = needed
        rows.append({"Measure": f"Customers needed to reach {target:.0%} of revenue",
                     "Value": needed, "Kind": "int"})
    rows.append({"Measure": "Customers with at least one order", "Value": n_cust, "Kind": "int"})
    rows.append({"Measure": "Customers with no orders", "Value": stats["n_customers_no_orders"], "Kind": "int"})
    return pd.DataFrame(rows), stats


def suspect_customer_orders(tables, lines):
    """Find orders whose ship-to details point to a different customer.

    An order is flagged when both ``ShipName`` differs from the
    customer's ``CompanyName`` and ``ShipCountry`` differs from the
    customer's ``Country``.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.
        lines (pandas.DataFrame): Order lines from
            ``build_order_lines``.

    Returns:
        dict[str, Any]: ``order_ids`` (sorted list[int]), ``revenue``
        (float, their net revenue) and ``share`` (fraction of total).
    """
    orders = tables["Orders"].merge(tables["Customers"][["CustomerID", "CompanyName", "Country"]],
                                    on="CustomerID")
    flagged = orders[(orders["ShipName"] != orders["CompanyName"]) & (orders["ShipCountry"] != orders["Country"])]
    ids = sorted(flagged["OrderID"].tolist())
    revenue = lines.loc[lines["OrderID"].isin(ids), "Revenue"].sum()
    return {"order_ids": ids, "revenue": revenue, "share": revenue / lines["Revenue"].sum()}
