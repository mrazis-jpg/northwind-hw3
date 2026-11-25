"""Draw the page's matplotlib charts and save them to docs/figures/.

Each chart is saved in a light and a dark version.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.dates import DateFormatter  # noqa: E402
from matplotlib.ticker import FuncFormatter, PercentFormatter  # noqa: E402

from analysis import REPO_ROOT  # noqa: E402

FIG_DIR = REPO_ROOT / "docs" / "figures"

# Colors from the dataviz reference palette; dark values are stepped for a dark surface.
THEMES = {
    "light": {"surface": "#fbfbf9", "text": "#1d1d1b", "muted": "#66655f",
              "grid": "#e2e0d8", "series": "#2a78d6", "accent": "#eb6834"},
    "dark": {"surface": "#17181a", "text": "#e8e6e1", "muted": "#a09d95",
             "grid": "#33343a", "series": "#3987e5", "accent": "#d95926"},
}


def _style_axes(ax, theme):
    """Apply the recessive grid and axis styling to one Axes.

    Args:
        ax (matplotlib.axes.Axes): Axes to style in place.
        theme (dict[str, str]): Colour set from ``THEMES``.

    Returns:
        None.
    """
    ax.set_facecolor(theme["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["grid"])
    ax.tick_params(colors=theme["muted"], labelsize=9, length=0)
    ax.grid(axis="y", color=theme["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def _money_k(x, _pos):
    """Format an axis tick as thousands of dollars.

    Args:
        x (float): Tick value in dollars.
        _pos (int): Tick position; unused, required by FuncFormatter.

    Returns:
        str: Label such as ``"$40k"``.
    """
    return f"${x / 1000:,.0f}k"


def _save(fig, name, mode):
    """Save a figure to docs/figures/ and close it.

    Creates docs/figures/ if it is missing.

    Args:
        fig (matplotlib.figure.Figure): Figure to save.
        name (str): File name without extension.
        mode (str): ``"light"`` or ``"dark"``; dark adds ``_dark``.

    Returns:
        pathlib.Path: Path of the saved PNG.
    """
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / (f"{name}.png" if mode == "light" else f"{name}_dark.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def monthly_revenue_chart(monthly, mode="light"):
    """Draw a line chart of revenue per month.

    Partial months are drawn as hollow points joined by dashed lines and
    labelled; the best complete month is labelled with its value.

    Args:
        monthly (pandas.DataFrame): Output of
            ``analysis.monthly_trend``.
        mode (str): ``"light"`` or ``"dark"`` colour theme.

    Returns:
        pathlib.Path: Path of the saved PNG.
    """
    t = THEMES[mode]
    x = monthly.index.to_timestamp()
    y = monthly["Revenue"].to_numpy()
    partial = monthly["Partial"].to_numpy()

    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor(t["surface"])
    _style_axes(ax, t)

    # Solid line through complete months; dashed links into partial months.
    full_idx = [i for i in range(len(y)) if not partial[i]]
    ax.plot(x[full_idx], y[full_idx], color=t["series"], linewidth=2, zorder=2)
    for i in range(len(y)):
        if partial[i]:
            nb = i - 1 if i > 0 else i + 1
            ax.plot([x[nb], x[i]], [y[nb], y[i]], color=t["series"], linewidth=2,
                    linestyle=(0, (2, 2)), zorder=2)
    ax.scatter(x[full_idx], y[full_idx], s=22, color=t["series"], edgecolor=t["surface"],
               linewidth=1.5, zorder=3)
    part_idx = [i for i in range(len(y)) if partial[i]]
    ax.scatter(x[part_idx], y[part_idx], s=48, facecolor=t["surface"], edgecolor=t["series"],
               linewidth=2, zorder=4)

    for i in part_idx:
        label = x[i].strftime("%b %Y") + "\npartial month"
        align = "right" if i == len(y) - 1 else "left"
        offset = -8 if align == "right" else 8
        ax.annotate(label, (x[i], y[i]), xytext=(offset, 22), textcoords="offset points",
                    ha=align, va="bottom", fontsize=8.5, color=t["muted"])

    best = max(full_idx, key=lambda i: y[i])
    ax.annotate(f"{x[best].strftime('%b %Y')}: ${y[best]:,.0f}", (x[best], y[best]),
                xytext=(-8, 8), textcoords="offset points", ha="right", fontsize=8.5, color=t["text"])

    ax.yaxis.set_major_formatter(FuncFormatter(_money_k))
    ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))
    ax.set_ylim(0, y.max() * 1.15)
    ax.set_title("Net revenue by month", loc="left", fontsize=11, color=t["text"], pad=10)
    return _save(fig, "monthly_revenue", mode)


def customer_pareto_chart(cust, target=0.8, mode="light"):
    """Draw a Pareto chart of customers ranked by revenue.

    Uses two panels sharing the rank axis (revenue bars above, a
    cumulative-share line below) instead of a dual-axis plot. Customers
    up to the ``target`` crossing are highlighted and the top three are
    named.

    Args:
        cust (pandas.DataFrame): Output of
            ``analysis.customer_revenue``, sorted by revenue.
        target (float): Cumulative revenue fraction to mark.
        mode (str): ``"light"`` or ``"dark"`` colour theme.

    Returns:
        pathlib.Path: Path of the saved PNG.
    """
    t = THEMES[mode]
    rank = cust["Rank"].to_numpy()
    revenue = cust["Revenue"].to_numpy()
    cum = cust["CumulativeShare"].to_numpy()
    n_needed = int((cum < target).sum() + 1)

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True,
                                      gridspec_kw={"height_ratios": [1.2, 1], "hspace": 0.12})
    fig.patch.set_facecolor(t["surface"])
    for ax in (top, bottom):
        _style_axes(ax, t)

    colors = [t["series"] if r <= n_needed else t["grid"] for r in rank]
    top.bar(rank, revenue, width=0.8, color=colors, linewidth=0)
    top.yaxis.set_major_formatter(FuncFormatter(_money_k))
    top.set_ylabel("Revenue", color=t["muted"], fontsize=9)
    top.set_ylim(0, revenue.max() * 1.12)
    # Name the three largest customers in clear space to the right, with leader lines.
    for i in range(3):
        label_y = revenue.max() * (1.02 - 0.13 * i)
        top.annotate(f"{i + 1}. {cust['Customer'].iloc[i]}", xy=(rank[i] + 0.4, revenue[i]),
                     xytext=(rank[0] + 7, label_y), fontsize=8.5, color=t["text"], va="center",
                     arrowprops={"arrowstyle": "-", "color": t["muted"], "linewidth": 0.8,
                                 "shrinkA": 2, "shrinkB": 1})
    top.set_title(f"Customers ranked by revenue — the first {n_needed} (blue) make up "
                  f"{target:.0%} of revenue", loc="left", fontsize=11, color=t["text"], pad=10)

    bottom.plot(rank, cum, color=t["series"], linewidth=2)
    bottom.axhline(target, color=t["muted"], linewidth=1, linestyle=(0, (3, 3)))
    bottom.axvline(n_needed, color=t["muted"], linewidth=1, linestyle=(0, (3, 3)))
    bottom.scatter([n_needed], [cum[n_needed - 1]], s=48, color=t["accent"],
                   edgecolor=t["surface"], linewidth=2, zorder=3)
    bottom.annotate(f"{n_needed} customers → {cum[n_needed - 1]:.0%}", (n_needed, cum[n_needed - 1]),
                    xytext=(10, -14), textcoords="offset points", fontsize=8.5, color=t["text"])
    bottom.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    bottom.set_ylim(0, 1.02)
    bottom.set_ylabel("Cumulative share", color=t["muted"], fontsize=9)
    bottom.set_xlabel("Customer rank", color=t["muted"], fontsize=9)
    bottom.set_xlim(0, len(rank) + 1)
    return _save(fig, "customer_pareto", mode)


def draw_all(monthly, cust):
    """Render every chart in both colour modes.

    Args:
        monthly (pandas.DataFrame): Output of
            ``analysis.monthly_trend``.
        cust (pandas.DataFrame): Output of
            ``analysis.customer_revenue``.

    Returns:
        list[pathlib.Path]: Paths of the saved PNGs.
    """
    paths = []
    for mode in THEMES:
        paths.append(monthly_revenue_chart(monthly, mode=mode))
        paths.append(customer_pareto_chart(cust, mode=mode))
    return paths
