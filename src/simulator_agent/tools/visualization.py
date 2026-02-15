"""BCG/McKinsey-style visualization charts for simulation reports.

Generates professional consulting-grade charts using matplotlib + seaborn.
All charts use a muted corporate color palette and clean styling.
"""

import base64
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─── Corporate Color Palette ────────────────────────────────────────────────
NAVY = "#1B2A4A"
TEAL = "#2D6A6A"
GOLD = "#C4A35A"
SLATE = "#5C6B7A"
CORAL = "#C4574B"
SAGE = "#6B8E6B"
LIGHT_GRAY = "#F5F5F5"
MID_GRAY = "#E0E0E0"
DARK_TEXT = "#2C2C2C"

PALETTE = [NAVY, TEAL, GOLD, CORAL, SAGE, SLATE, "#7B68AE", "#3C8DAD"]


def _setup_style():
    """Apply consulting-grade chart styling."""
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": MID_GRAY,
        "axes.labelcolor": DARK_TEXT,
        "axes.grid": True,
        "grid.color": MID_GRAY,
        "grid.alpha": 0.4,
        "grid.linewidth": 0.5,
        "xtick.color": SLATE,
        "ytick.color": SLATE,
        "text.color": DARK_TEXT,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "figure.dpi": 150,
    })


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    import matplotlib.pyplot as plt
    plt.close(fig)
    return encoded


def conversion_funnel(
    stages: list[str],
    values: list[int],
    title: str = "Endcap Conversion Funnel",
) -> str:
    """Horizontal bar funnel chart showing shopper conversion stages.

    Args:
        stages: Funnel stage labels top to bottom (e.g. ["Entered Store", "Passed Endcap", "Browsed", "Picked Up"])
        values: Count at each stage
        title: Chart title

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    _setup_style()

    fig, ax = plt.subplots(figsize=(8, 4.5))
    max_val = max(values) if values else 1

    colors = [NAVY, TEAL, GOLD, CORAL, SAGE, SLATE]
    for i, (stage, val) in enumerate(zip(stages, values)):
        width = val / max_val
        bar_color = colors[i % len(colors)]
        ax.barh(len(stages) - 1 - i, width, height=0.6, color=bar_color, alpha=0.85)
        pct = f"{val / values[0] * 100:.0f}%" if values[0] > 0 else "0%"
        ax.text(width + 0.02, len(stages) - 1 - i, f"{val}  ({pct})",
                va="center", fontsize=11, fontweight="bold", color=DARK_TEXT)

    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels(list(reversed(stages)), fontsize=11)
    ax.set_xlim(0, 1.3)
    ax.set_xlabel("")
    ax.set_title(title, pad=15, fontsize=14, fontweight="bold", color=NAVY)
    ax.xaxis.set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.grid(False)

    return _fig_to_base64(fig)


def revenue_waterfall(
    categories: list[str],
    values: list[float],
    title: str = "Revenue Waterfall — Baseline + Endcap Lift",
) -> str:
    """Waterfall chart showing baseline revenue plus incremental endcap contributions.

    Args:
        categories: Labels (first is baseline total, rest are incremental, last is total)
        values: Dollar amounts (positive = lift, negative = cost)
        title: Chart title

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    import numpy as np
    _setup_style()

    fig, ax = plt.subplots(figsize=(9, 5))
    n = len(categories)
    running = 0.0
    bottoms = []
    bar_colors = []

    for i, v in enumerate(values):
        if i == 0 or i == n - 1:
            bottoms.append(0)
            bar_colors.append(NAVY if i == 0 else TEAL)
        else:
            bottoms.append(running)
            bar_colors.append(SAGE if v >= 0 else CORAL)
        if i < n - 1:
            running += v

    x = np.arange(n)
    bars = ax.bar(x, values, bottom=bottoms, color=bar_colors, width=0.55, alpha=0.9)

    for i, (bar, val) in enumerate(zip(bars, values)):
        top = bottoms[i] + val
        label = f"${val:,.0f}" if val >= 0 else f"-${abs(val):,.0f}"
        ax.text(bar.get_x() + bar.get_width() / 2, top + max(values) * 0.02,
                label, ha="center", va="bottom", fontsize=10, fontweight="bold", color=DARK_TEXT)

    # Connector lines
    for i in range(n - 2):
        top = bottoms[i] + values[i]
        ax.plot([x[i] + 0.275, x[i + 1] - 0.275], [top, top],
                color=MID_GRAY, linewidth=1, linestyle="--")

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10, rotation=20, ha="right")
    ax.set_ylabel("Revenue ($)", fontsize=11)
    ax.set_title(title, pad=15, fontsize=14, fontweight="bold", color=NAVY)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_base64(fig)


def persona_matrix_2x2(
    personas: list[dict[str, Any]],
    title: str = "Persona Positioning — Impulse Tendency vs. Budget",
) -> str:
    """BCG-style 2x2 matrix plotting personas by impulse tendency (x) and budget (y).

    Args:
        personas: List of dicts with keys: name, impulse_tendency (0-1), budget (float)
        title: Chart title

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    _setup_style()

    fig, ax = plt.subplots(figsize=(8, 7))

    colors = PALETTE[:len(personas)]
    for i, p in enumerate(personas):
        x = p["impulse_tendency"]
        y = p["budget"]
        ax.scatter(x, y, s=280, color=colors[i % len(colors)], zorder=5,
                   edgecolors="white", linewidth=1.5)
        ax.annotate(p["name"].split()[0], (x, y), textcoords="offset points",
                    xytext=(8, 8), fontsize=9, color=DARK_TEXT)

    # Quadrant lines
    ax.axhline(y=80, color=MID_GRAY, linewidth=1.2, linestyle="--", alpha=0.7)
    ax.axvline(x=0.5, color=MID_GRAY, linewidth=1.2, linestyle="--", alpha=0.7)

    # Quadrant labels
    ax.text(0.25, 0.97, "Low Impulse\nHigh Budget", transform=ax.transAxes,
            ha="center", va="top", fontsize=9, color=SLATE, fontstyle="italic")
    ax.text(0.75, 0.97, "High Impulse\nHigh Budget", transform=ax.transAxes,
            ha="center", va="top", fontsize=9, color=SLATE, fontstyle="italic")
    ax.text(0.25, 0.03, "Low Impulse\nLow Budget", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9, color=SLATE, fontstyle="italic")
    ax.text(0.75, 0.03, "High Impulse\nLow Budget", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9, color=SLATE, fontstyle="italic")

    ax.set_xlabel("Impulse Buy Tendency", fontsize=11)
    ax.set_ylabel("Budget ($)", fontsize=11)
    ax.set_title(title, pad=15, fontsize=14, fontweight="bold", color=NAVY)
    ax.set_xlim(-0.05, 1.05)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_base64(fig)


def aisle_heatmap(
    persona_names: list[str],
    aisle_names: list[str],
    visit_matrix: list[list[float]],
    title: str = "Aisle Visit Frequency by Persona",
) -> str:
    """Heatmap showing aisle visit probability per persona.

    Args:
        persona_names: Row labels
        aisle_names: Column labels
        visit_matrix: 2D matrix [persona][aisle] with values 0.0-1.0
        title: Chart title

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    import numpy as np
    _setup_style()

    fig, ax = plt.subplots(figsize=(10, 5))
    data = np.array(visit_matrix)

    import matplotlib.colors as mcolors
    cmap = mcolors.LinearSegmentedColormap.from_list("consulting", ["#FFFFFF", TEAL, NAVY])
    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(aisle_names)))
    ax.set_xticklabels(aisle_names, fontsize=9, rotation=35, ha="right")
    ax.set_yticks(range(len(persona_names)))
    ax.set_yticklabels(persona_names, fontsize=9)

    for i in range(len(persona_names)):
        for j in range(len(aisle_names)):
            val = data[i, j]
            color = "white" if val > 0.6 else DARK_TEXT
            ax.text(j, i, f"{val:.0%}", ha="center", va="center", fontsize=8, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Visit Probability", fontsize=10)
    ax.set_title(title, pad=15, fontsize=14, fontweight="bold", color=NAVY)

    return _fig_to_base64(fig)


def endcap_pickup_bars(
    persona_names: list[str],
    pickup_rates: dict[str, list[float]],
    title: str = "Endcap Pickup Rate by Persona & Scenario",
) -> str:
    """Grouped bar chart of endcap pickup rates by persona across scenarios.

    Args:
        persona_names: Persona labels
        pickup_rates: Dict mapping scenario_name -> list of rates (one per persona)
        title: Chart title

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    import numpy as np
    _setup_style()

    fig, ax = plt.subplots(figsize=(10, 5))
    scenarios = list(pickup_rates.keys())
    n_groups = len(persona_names)
    n_scenarios = len(scenarios)
    bar_width = 0.8 / n_scenarios
    x = np.arange(n_groups)

    for i, scenario in enumerate(scenarios):
        rates = pickup_rates[scenario]
        offset = (i - n_scenarios / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, rates, bar_width * 0.9, label=scenario,
                      color=PALETTE[i % len(PALETTE)], alpha=0.85)
        for bar, rate in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{rate:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(persona_names, fontsize=9, rotation=20, ha="right")
    ax.set_ylabel("Pickup Rate (%)", fontsize=11)
    ax.set_title(title, pad=15, fontsize=14, fontweight="bold", color=NAVY)
    ax.legend(fontsize=9, framealpha=0.9, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_base64(fig)


def persona_radar(
    persona_name: str,
    attributes: list[str],
    values: list[float],
    title: str | None = None,
) -> str:
    """Radar/spider chart comparing persona attributes.

    Args:
        persona_name: Label for the persona
        attributes: Attribute names around the radar
        values: Values 0.0-1.0 for each attribute
        title: Chart title (defaults to persona name)

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    import numpy as np
    _setup_style()

    n = len(attributes)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles += [angles[0]]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values_plot, "o-", linewidth=2, color=NAVY)
    ax.fill(angles, values_plot, alpha=0.15, color=TEAL)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(attributes, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=8, color=SLATE)
    ax.set_title(title or persona_name, pad=20, fontsize=14, fontweight="bold", color=NAVY)

    return _fig_to_base64(fig)


def scenario_comparison_bars(
    scenario_names: list[str],
    metric_name: str,
    metric_values: list[float],
    title: str = "Scenario Comparison",
) -> str:
    """Simple horizontal bar chart comparing a single metric across scenarios.

    Args:
        scenario_names: Scenario labels
        metric_name: What is being measured (e.g. "Total Revenue")
        metric_values: One value per scenario
        title: Chart title

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib.pyplot as plt
    import numpy as np
    _setup_style()

    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(scenario_names))
    bars = ax.barh(y, metric_values, height=0.5, color=PALETTE[:len(scenario_names)], alpha=0.85)

    for bar, val in zip(bars, metric_values):
        fmt = f"${val:,.0f}" if "revenue" in metric_name.lower() or "spend" in metric_name.lower() else f"{val:,.1f}"
        ax.text(bar.get_width() + max(metric_values) * 0.02, bar.get_y() + bar.get_height() / 2,
                fmt, va="center", fontsize=11, fontweight="bold", color=DARK_TEXT)

    ax.set_yticks(y)
    ax.set_yticklabels(scenario_names, fontsize=10)
    ax.set_xlabel(metric_name, fontsize=11)
    ax.set_title(title, pad=15, fontsize=14, fontweight="bold", color=NAVY)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_base64(fig)
