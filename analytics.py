# =============================================================================
# ANALYTICS MODULE — Instrument Usage Analytics
# File: analytics.py
# Adani Thermal Power Plant | C&I Main Store
# =============================================================================

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import io, os, datetime

# ── Bloomberg-style dark theme for all charts ─────────────────────────────────
ORANGE   = "#f97316"
ORANGE2  = "#fb923c"
BG       = "#0c0c0f"
SURFACE  = "#18181d"
GRID     = "#1e1e26"
TEXT1    = "#f0f0f2"
TEXT2    = "#9ca3af"
TEXT3    = "#4b5563"
GREEN    = "#22c55e"
RED      = "#ef4444"
AMBER    = "#f59e0b"
PALETTE  = [ORANGE, "#3b82f6", "#22c55e", "#a855f7", "#ec4899",
            "#14b8a6", "#f59e0b", "#ef4444", "#6366f1", "#84cc16"]

def _style_axis(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=TEXT2, labelsize=8)
    ax.xaxis.label.set_color(TEXT2)
    ax.yaxis.label.set_color(TEXT2)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.set_title(title, color=TEXT1, fontsize=10, fontweight="bold",
                 pad=10, loc="left")
    if xlabel: ax.set_xlabel(xlabel, fontsize=8)
    if ylabel: ax.set_ylabel(ylabel, fontsize=8)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.grid(axis="y", color=GRID, linewidth=0.8, linestyle="--")
    ax.set_axisbelow(True)

def _fig(w=9, h=4):
    fig = plt.figure(figsize=(w, h), facecolor=BG)
    return fig

# =============================================================================
# DATA LOADER
# =============================================================================

from inventory_chatbot_copy import get_supabase

def load_log():
    """Load transaction logs from Supabase and return cleaned DataFrame."""
    try:
        supabase = get_supabase()
        response = supabase.table("transaction_logs").select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame()
        df.columns = df.columns.str.strip()

        # Parse date
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df["Month"]     = df["Date"].dt.to_period("M")
            df["MonthName"] = df["Date"].dt.strftime("%b %Y")

        # Ensure numeric
        if "QuantityTaken" in df.columns:
            df["QuantityTaken"] = pd.to_numeric(df["QuantityTaken"], errors="coerce").fillna(0)

        # Add Department if missing (backward compat)
        if "Department" not in df.columns:
            df["Department"] = "Not Specified"

        return df
    except Exception as e:
        print(f"[analytics] log load error: {e}")
        return pd.DataFrame()


# =============================================================================
# ANALYTICS 1 — Most Frequently Issued Instruments
# =============================================================================

def most_frequent_instruments(df, top_n=10):
    """Returns DataFrame: ItemCode, ItemName, TimesIssued, TotalQtyIssued"""
    if df.empty or "ItemCode" not in df.columns:
        return pd.DataFrame()

    result = (
        df.groupby(["ItemCode", "ItemName"])
        .agg(
            TimesIssued    = ("ItemCode",      "count"),
            TotalQtyIssued = ("QuantityTaken", "sum")
        )
        .reset_index()
        .sort_values("TimesIssued", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    result.index = result.index + 1
    return result


# =============================================================================
# ANALYTICS 2 — Least Frequently Used Instruments
# =============================================================================

def least_used_instruments(df, bottom_n=10):
    """Returns DataFrame: ItemCode, ItemName, UsageCount"""
    if df.empty or "ItemCode" not in df.columns:
        return pd.DataFrame()

    result = (
        df.groupby(["ItemCode", "ItemName"])
        .agg(UsageCount = ("ItemCode", "count"))
        .reset_index()
        .sort_values("UsageCount", ascending=True)
        .head(bottom_n)
        .reset_index(drop=True)
    )
    result.index = result.index + 1
    return result


# =============================================================================
# ANALYTICS 3 — Top 10 Most Used (ranked)
# =============================================================================

def top10_instruments(df):
    """Returns ranked DataFrame with Rank column."""
    if df.empty:
        return pd.DataFrame()

    result = (
        df.groupby(["ItemCode", "ItemName"])
        .agg(
            TotalIssues = ("ItemCode",      "count"),
            TotalQty    = ("QuantityTaken", "sum")
        )
        .reset_index()
        .sort_values("TotalIssues", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    result.insert(0, "Rank", ["#1","#2","#3","#4","#5","#6","#7","#8","#9","#10"][:len(result)])
    return result


# =============================================================================
# ANALYTICS 4 — Department-wise Usage
# =============================================================================

def department_usage(df):
    """Returns: Department, TotalIssued, TotalQty, TopInstrument"""
    if df.empty or "Department" not in df.columns:
        return pd.DataFrame()

    base = (
        df.groupby("Department")
        .agg(
            TotalIssues = ("ItemCode",      "count"),
            TotalQty    = ("QuantityTaken", "sum")
        )
        .reset_index()
        .sort_values("TotalIssues", ascending=False)
        .reset_index(drop=True)
    )

    # Find top instrument per department
    top_item = (
        df.groupby(["Department", "ItemName"])
        .size()
        .reset_index(name="cnt")
        .sort_values("cnt", ascending=False)
        .drop_duplicates("Department")
        .set_index("Department")["ItemName"]
    )

    base["TopInstrument"] = base["Department"].map(top_item).fillna("—")
    return base


# =============================================================================
# ANALYTICS 5 — Monthly Usage Trends
# =============================================================================

def monthly_trends(df):
    """Returns: MonthName, TotalIssues, TotalQty sorted chronologically."""
    if df.empty or "Month" not in df.columns:
        return pd.DataFrame()

    result = (
        df.groupby(["Month", "MonthName"])
        .agg(
            TotalIssues = ("ItemCode",      "count"),
            TotalQty    = ("QuantityTaken", "sum")
        )
        .reset_index()
        .sort_values("Month")
        .reset_index(drop=True)
    )
    result = result.drop(columns=["Month"])
    return result


# =============================================================================
# ANALYTICS 6 — Critical Consumption Detection
# =============================================================================

def critical_consumption(df, threshold_pct=50):
    """
    Compares last 30 days vs previous 30 days.
    Returns items where usage jumped by threshold_pct% or more.
    """
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame(), []

    today    = pd.Timestamp.now().normalize()
    recent   = df[df["Date"] >= today - pd.Timedelta(days=30)]
    previous = df[(df["Date"] >= today - pd.Timedelta(days=60)) &
                  (df["Date"] <  today - pd.Timedelta(days=30))]

    r_count = recent.groupby("ItemCode")["QuantityTaken"].sum().rename("Recent30")
    p_count = previous.groupby("ItemCode")["QuantityTaken"].sum().rename("Prev30")

    merged = pd.concat([r_count, p_count], axis=1).fillna(0)
    merged["Change%"] = merged.apply(
        lambda row: (
            ((row["Recent30"] - row["Prev30"]) / row["Prev30"] * 100)
            if row["Prev30"] > 0
            else (100 if row["Recent30"] > 0 else 0)
        ), axis=1
    )

    # Add ItemName
    name_map = df.drop_duplicates("ItemCode").set_index("ItemCode")["ItemName"]
    merged["ItemName"] = merged.index.map(name_map)

    critical = (
        merged[merged["Change%"] >= threshold_pct]
        .sort_values("Change%", ascending=False)
        .reset_index()
        .rename(columns={"ItemCode": "ItemCode"})
    )
    critical["Change%"] = critical["Change%"].round(1).astype(str) + "%"

    alerts = []
    for _, row in critical.iterrows():
        alerts.append(
            f"{row['ItemName']} ({row['ItemCode']}) — "
            f"usage up {row['Change%']} in last 30 days. "
            f"Consider procurement."
        )
    return critical[["ItemCode", "ItemName", "Recent30", "Prev30", "Change%"]], alerts


# =============================================================================
# CHART 1 — Bar Chart: Top 10 Instruments
# =============================================================================

def chart_top10(df):
    data = top10_instruments(df)
    if data.empty:
        return None

    fig = _fig(9, 4)
    ax  = fig.add_subplot(111)
    ax.set_facecolor(SURFACE)
    fig.patch.set_facecolor(BG)

    bars = ax.barh(
        data["ItemName"].str[:30],
        data["TotalIssues"],
        color=PALETTE[:len(data)],
        height=0.6,
        edgecolor="none"
    )

    # Value labels
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.1, bar.get_y() + bar.get_height()/2,
                f"{int(w)}", va="center", ha="left",
                color=TEXT1, fontsize=8, fontweight="600")

    _style_axis(ax, title="TOP 10 MOST ISSUED INSTRUMENTS",
                xlabel="Times Issued")
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=7.5)
    plt.tight_layout(pad=1.5)
    return fig


# =============================================================================
# CHART 2 — Pie Chart: Department Usage
# =============================================================================

def chart_department_pie(df):
    data = department_usage(df)
    if data.empty or data["Department"].nunique() < 2:
        return None

    fig = _fig(7, 4)
    ax  = fig.add_subplot(111)
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    wedges, texts, autotexts = ax.pie(
        data["TotalIssues"],
        labels=data["Department"],
        autopct="%1.1f%%",
        colors=PALETTE[:len(data)],
        startangle=140,
        pctdistance=0.82,
        wedgeprops={"edgecolor": BG, "linewidth": 2}
    )
    for t in texts:     t.set_color(TEXT2); t.set_fontsize(8)
    for a in autotexts: a.set_color(TEXT1); a.set_fontsize(7.5); a.set_fontweight("bold")

    ax.set_title("DEPARTMENT-WISE INSTRUMENT USAGE",
                 color=TEXT1, fontsize=10, fontweight="bold", pad=10, loc="left")
    plt.tight_layout(pad=1.5)
    return fig


# =============================================================================
# CHART 3 — Monthly Trend Line Chart
# =============================================================================

def chart_monthly_trend(df):
    data = monthly_trends(df)
    if data.empty or len(data) < 1:
        return None

    fig = _fig(9, 4)
    ax  = fig.add_subplot(111)
    ax.set_facecolor(SURFACE)
    fig.patch.set_facecolor(BG)

    x = range(len(data))

    ax.fill_between(x, data["TotalIssues"], alpha=0.15, color=ORANGE)
    ax.plot(x, data["TotalIssues"], color=ORANGE, linewidth=2.2,
            marker="o", markersize=5, markerfacecolor=ORANGE,
            markeredgecolor=BG, markeredgewidth=2, label="Issues")

    ax.fill_between(x, data["TotalQty"], alpha=0.08, color="#3b82f6")
    ax.plot(x, data["TotalQty"], color="#3b82f6", linewidth=1.8,
            marker="s", markersize=4, markerfacecolor="#3b82f6",
            markeredgecolor=BG, markeredgewidth=1.5, label="Qty Issued", linestyle="--")

    # Value labels
    for i, (iss, qty) in enumerate(zip(data["TotalIssues"], data["TotalQty"])):
        ax.annotate(str(int(iss)), (i, iss), textcoords="offset points",
                    xytext=(0, 7), ha="center", color=ORANGE, fontsize=7.5, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(data["MonthName"], rotation=30, ha="right", fontsize=7.5)
    _style_axis(ax, title="MONTHLY USAGE TRENDS", ylabel="Count")
    ax.legend(fontsize=8, facecolor=SURFACE, edgecolor=GRID,
              labelcolor=TEXT2, framealpha=0.8)
    plt.tight_layout(pad=1.5)
    return fig


# =============================================================================
# CHART 4 — Category Usage Comparison Bar
# =============================================================================

def chart_category_usage(df):
    if df.empty or "ItemName" not in df.columns:
        return None

    inv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plant_inventory.xlsx")
    try:
        inv = pd.read_excel(inv_path, sheet_name="Inventory")
        inv.columns = inv.columns.str.strip()
        cat_map = inv.set_index("ItemCode")["Category"].to_dict()
        df = df.copy()
        df["Category"] = df["ItemCode"].map(cat_map).fillna("Other")
    except:
        if "Category" not in df.columns:
            return None

    cat_data = (
        df.groupby("Category")["QuantityTaken"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    if cat_data.empty:
        return None

    fig = _fig(9, 4)
    ax  = fig.add_subplot(111)
    ax.set_facecolor(SURFACE)
    fig.patch.set_facecolor(BG)

    bars = ax.bar(
        cat_data["Category"],
        cat_data["QuantityTaken"],
        color=PALETTE[:len(cat_data)],
        edgecolor="none",
        width=0.55
    )

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                str(int(h)), ha="center", va="bottom",
                color=TEXT1, fontsize=8, fontweight="600")

    _style_axis(ax, title="CATEGORY-WISE QUANTITY ISSUED",
                xlabel="Category", ylabel="Total Qty Issued")
    ax.set_xticklabels(cat_data["Category"], rotation=25, ha="right", fontsize=8)
    plt.tight_layout(pad=1.5)
    return fig


# =============================================================================
# SUMMARY REPORT — Text based
# =============================================================================

def generate_summary(df):
    """Returns a dict of key summary statistics."""
    if df.empty:
        return {}

    now = datetime.datetime.now()
    summary = {
        "report_date"    : now.strftime("%d %B %Y, %H:%M"),
        "total_records"  : len(df),
        "total_qty"      : int(df["QuantityTaken"].sum()),
        "unique_items"   : df["ItemCode"].nunique(),
        "unique_engineers": df["EngineerName"].nunique(),
        "date_from"      : df["Date"].min().strftime("%d %b %Y") if "Date" in df.columns else "—",
        "date_to"        : df["Date"].max().strftime("%d %b %Y") if "Date" in df.columns else "—",
        "top_item"       : None,
        "top_engineer"   : None,
        "top_dept"       : None,
    }

    if not df.empty:
        top = df.groupby("ItemName")["QuantityTaken"].sum().idxmax()
        summary["top_item"] = top

        top_eng = df["EngineerName"].value_counts().idxmax()
        summary["top_engineer"] = top_eng

        if "Department" in df.columns:
            top_dept = df["Department"].value_counts().idxmax()
            summary["top_dept"] = top_dept

    return summary
