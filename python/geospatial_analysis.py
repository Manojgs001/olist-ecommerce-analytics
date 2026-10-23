# ============================================================
# 🗺️ Olist E-Commerce — Brazil Geospatial Logistics Analysis
# Author: Manoj (Data Analyst)
# Dataset: Brazilian E-Commerce (Olist)
# ============================================================

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
plt.rcParams["figure.figsize"] = (14, 6)
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

print("📦 Loading datasets for Geospatial Analysis...")

orders = pd.read_csv(
    os.path.join(DATA_DIR, "olist_orders_dataset.csv"),
    parse_dates=["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
)
items = pd.read_csv(os.path.join(DATA_DIR, "olist_order_items_dataset.csv"))
customers = pd.read_csv(os.path.join(DATA_DIR, "olist_customers_dataset.csv"))
sellers = pd.read_csv(os.path.join(DATA_DIR, "olist_sellers_dataset.csv"))
geo = pd.read_csv(os.path.join(DATA_DIR, "olist_geolocation_dataset.csv"))

print("🔗 Aggregating state-level logistics and geographic data...")

# Calculate state centroids from geolocation dataset
state_coords = geo.groupby("geolocation_state")[["geolocation_lat", "geolocation_lng"]].mean().reset_index()
state_coords.columns = ["state", "lat", "lng"]

# Filter to delivered orders
delivered = orders[orders["order_status"] == "delivered"].copy()
delivered["delivery_days"] = (delivered["order_delivered_customer_date"] - delivered["order_purchase_timestamp"]).dt.days
delivered["is_late"] = (delivered["order_delivered_customer_date"] > delivered["order_estimated_delivery_date"]).astype(int)

# Merge orders with customers
orders_cust = delivered.merge(customers[["customer_id", "customer_state", "customer_city"]], on="customer_id", how="left")

# Merge items to get revenue and freight
order_totals = items.groupby("order_id").agg(
    total_price=("price", "sum"),
    total_freight=("freight_value", "sum"),
    item_count=("order_item_id", "count")
).reset_index()

merged = orders_cust.merge(order_totals, on="order_id", how="inner")

# Brazilian Macro-Regions Mapping
REGION_MAP = {
    "SP": "Southeast", "RJ": "Southeast", "MG": "Southeast", "ES": "Southeast",
    "PR": "South", "SC": "South", "RS": "South",
    "BA": "Northeast", "PE": "Northeast", "CE": "Northeast", "MA": "Northeast",
    "PB": "Northeast", "RN": "Northeast", "AL": "Northeast", "PI": "Northeast", "SE": "Northeast",
    "DF": "Central-West", "GO": "Central-West", "MT": "Central-West", "MS": "Central-West",
    "AM": "North", "PA": "North", "RO": "North", "TO": "North", "AC": "North", "AP": "North", "RR": "North"
}

STATE_NAMES = {
    "SP": "São Paulo", "RJ": "Rio de Janeiro", "MG": "Minas Gerais", "RS": "Rio Grande do Sul",
    "PR": "Paraná", "SC": "Santa Catarina", "BA": "Bahia", "DF": "Distrito Federal",
    "GO": "Goiás", "ES": "Espírito Santo", "PE": "Pernambuco", "CE": "Ceará",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MA": "Maranhão", "PB": "Paraíba",
    "RN": "Rio Grande do Norte", "PI": "Piauí", "AL": "Alagoas", "SE": "Sergipe",
    "TO": "Tocantins", "RO": "Rondônia", "AM": "Amazonas", "AC": "Acre",
    "PA": "Pará", "AP": "Amapá", "RR": "Roraima"
}

merged["region"] = merged["customer_state"].map(REGION_MAP)
merged["state_name"] = merged["customer_state"].map(STATE_NAMES)

# State-level metrics aggregation
state_metrics = merged.groupby("customer_state").agg(
    order_count=("order_id", "nunique"),
    total_revenue=("total_price", "sum"),
    avg_order_value=("total_price", "mean"),
    avg_freight=("total_freight", "mean"),
    avg_delivery_days=("delivery_days", "mean"),
    late_delivery_rate=("is_late", "mean")
).reset_index()

state_metrics["late_pct"] = state_metrics["late_delivery_rate"] * 100
state_metrics["region"] = state_metrics["customer_state"].map(REGION_MAP)
state_metrics["state_name"] = state_metrics["customer_state"].map(STATE_NAMES)

# Merge coordinates
state_metrics = state_metrics.merge(state_coords, left_on="customer_state", right_on="state", how="left")

# Save state metrics summary CSV
csv_out = os.path.join(REPORTS_DIR, "state_logistics_metrics.csv")
state_metrics.to_csv(csv_out, index=False)
print(f"💾 Saved state logistics summary to: {csv_out}")

# ============================================================
# VISUALIZATION: REGIONAL DISPARITY DASHBOARD
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Plot 1: Average Delivery Days by Brazilian Region
region_summary = merged.groupby("region").agg(
    avg_days=("delivery_days", "mean"),
    late_rate=("is_late", "mean"),
    avg_freight=("total_freight", "mean"),
    orders=("order_id", "nunique")
).reset_index().sort_values("avg_days", ascending=True)
region_summary["late_pct"] = region_summary["late_rate"] * 100

colors = ["#2563eb", "#3b82f6", "#f59e0b", "#f97316", "#ef4444"]
bars1 = ax1.bar(region_summary["region"], region_summary["avg_days"], color=colors, edgecolor="black", linewidth=0.7)
for bar, val in zip(bars1, region_summary["avg_days"]):
    ax1.text(bar.get_x() + bar.get_width()/2, val + 0.4, f"{val:.1f} days", ha="center", fontsize=9, fontweight="bold")

ax1.set_title("Average Delivery Duration by Region", fontsize=13, fontweight="bold")
ax1.set_ylabel("Delivery Days")
ax1.set_ylim(0, max(region_summary["avg_days"]) * 1.2)
ax1.grid(axis="y", linestyle="--", alpha=0.3)

# Plot 2: Freight Cost vs Delivery Days (Scatter with state bubbles)
scatter_colors = {"Southeast": "#2563eb", "South": "#10b981", "Central-West": "#f59e0b", "Northeast": "#f97316", "North": "#ef4444"}

for reg, group in state_metrics.groupby("region"):
    ax2.scatter(
        group["avg_delivery_days"], group["avg_freight"],
        s=group["order_count"] / 40 + 30, # size proportional to orders
        color=scatter_colors.get(reg, "gray"),
        alpha=0.75,
        edgecolors="black",
        label=reg
    )

for _, row in state_metrics.iterrows():
    if row["customer_state"] in ["SP", "RJ", "MG", "BA", "AM", "RR", "AP", "AL", "CE"]:
        ax2.annotate(
            row["customer_state"],
            (row["avg_delivery_days"], row["avg_freight"]),
            xytext=(5, 5), textcoords="offset points", fontsize=8, fontweight="bold"
        )

ax2.set_title("Freight Cost vs Delivery Duration by State\n(Bubble size = Order volume)", fontsize=13, fontweight="bold")
ax2.set_xlabel("Average Delivery Days")
ax2.set_ylabel("Average Freight Cost (R$)")
ax2.legend(title="Macro-Region", loc="upper left", frameon=True)
ax2.grid(True, linestyle="--", alpha=0.3)

plt.suptitle("Brazilian E-Commerce Regional Disparity Analysis", fontsize=15, fontweight="bold", y=1.02)
plt.tight_layout()

chart_out = os.path.join(REPORTS_DIR, "08_brazil_geospatial_density.png")
plt.savefig(chart_out, dpi=150, bbox_inches="tight")
print(f"📊 Chart saved: {chart_out}")

# Print Executive Regional Summary
print("\n📋 Regional Logistics Breakdown:")
print(region_summary[["region", "orders", "avg_days", "avg_freight", "late_pct"]].to_string(index=False))
print("\n✅ Geospatial Analysis completed successfully!")
