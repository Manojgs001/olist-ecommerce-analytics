# ============================================================
# Olist E-Commerce - Python Exploratory Data Analysis (EDA)
# Author: Data Analyst Project
# Dataset: Brazilian E-Commerce (Olist) - 100K+ orders
# ============================================================

import sys
import matplotlib
matplotlib.use("Agg")          # <-- Non-interactive: saves charts without opening windows
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
import os

# Fix Unicode/emoji output on Windows terminals
sys.stdout.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore")
plt.rcParams["figure.figsize"] = (12, 5)
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
sns.set_palette("Set2")

# ── Paths ────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data", "raw")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ============================================================
# 1. LOAD DATA
# ============================================================
print("📦 Loading datasets...")

orders   = pd.read_csv(f"{DATA_DIR}/olist_orders_dataset.csv",         parse_dates=["order_purchase_timestamp","order_approved_at","order_delivered_customer_date","order_estimated_delivery_date"])
items    = pd.read_csv(f"{DATA_DIR}/olist_order_items_dataset.csv",     parse_dates=["shipping_limit_date"])
customers= pd.read_csv(f"{DATA_DIR}/olist_customers_dataset.csv")
products = pd.read_csv(f"{DATA_DIR}/olist_products_dataset.csv")
sellers  = pd.read_csv(f"{DATA_DIR}/olist_sellers_dataset.csv")
payments = pd.read_csv(f"{DATA_DIR}/olist_order_payments_dataset.csv")
reviews  = pd.read_csv(f"{DATA_DIR}/olist_order_reviews_dataset.csv",   parse_dates=["review_creation_date"])
category = pd.read_csv(f"{DATA_DIR}/product_category_name_translation.csv")

print("✅ All datasets loaded!\n")
for name, df in [("Orders",orders),("Items",items),("Customers",customers),("Products",products),
                  ("Sellers",sellers),("Payments",payments),("Reviews",reviews)]:
    print(f"  {name:12s}: {len(df):>7,} rows × {df.shape[1]} cols")

# ============================================================
# 2. BUILD MASTER DATASET (joins like bi_fact_sales)
# ============================================================
print("\n🔗 Building master dataset...")

# Merge products with English category names
products = products.merge(category, on="product_category_name", how="left")
products["category"] = products["product_category_name_english"].fillna(products["product_category_name"])

# Merge orders with customers
orders_customers = orders.merge(customers, on="customer_id", how="left")

# Merge items with orders+customers, products, sellers
df = (items
      .merge(orders_customers, on="order_id",   how="left")
      .merge(products[["product_id","category"]], on="product_id", how="left")
      .merge(sellers,  on="seller_id",  how="left")
      .merge(reviews[["order_id","review_score"]].drop_duplicates("order_id"), on="order_id", how="left")
      .merge(payments, on="order_id",  how="left")
)

# Derived columns
df["delivery_days"] = (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.days
df["is_late"] = (
    (df["order_status"] == "delivered") &
    (df["order_delivered_customer_date"] > df["order_estimated_delivery_date"])
).astype(int)
df["purchase_month"] = df["order_purchase_timestamp"].dt.to_period("M")
df["total_revenue"]  = df["price"] + df["freight_value"]

print(f"✅ Master dataset: {len(df):,} rows × {df.shape[1]} columns\n")

# ============================================================
# 3. KEY BUSINESS KPIs
# ============================================================
print("=" * 55)
print("📊  KEY BUSINESS KPIs")
print("=" * 55)

delivered = df[df["order_status"] == "delivered"]

total_revenue   = df["price"].sum()
total_orders    = df["order_id"].nunique()
total_customers = df["customer_unique_id"].nunique()
aov             = total_revenue / total_orders
on_time_pct     = (1 - delivered["is_late"].mean()) * 100
avg_rating      = df["review_score"].mean()
avg_delivery    = delivered["delivery_days"].mean()

print(f"  💰 Total Revenue      : R$ {total_revenue:>12,.2f}")
print(f"  🛒 Total Orders       : {total_orders:>12,}")
print(f"  👥 Unique Customers   : {total_customers:>12,}")
print(f"  📦 Avg Order Value    : R$ {aov:>12,.2f}")
print(f"  ✅ On-Time Delivery   : {on_time_pct:>11.1f}%")
print(f"  ⭐ Avg Review Score   : {avg_rating:>12.2f} / 5")
print(f"  🚚 Avg Delivery Days  : {avg_delivery:>12.1f} days")
print("=" * 55)

# ============================================================
# 4. SALES TREND (Monthly Revenue)
# ============================================================
monthly = (df.groupby("purchase_month")["price"]
             .sum()
             .reset_index()
             .sort_values("purchase_month"))
monthly["purchase_month_str"] = monthly["purchase_month"].astype(str)

fig, ax = plt.subplots()
ax.plot(monthly["purchase_month_str"], monthly["price"], marker="o", linewidth=2.5, color="#2196F3")
ax.fill_between(range(len(monthly)), monthly["price"], alpha=0.15, color="#2196F3")
ax.set_xticklabels(monthly["purchase_month_str"], rotation=45, ha="right", fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))
ax.set_title("Monthly Revenue Trend", fontsize=14, fontweight="bold")
ax.set_xlabel("Month"); ax.set_ylabel("Revenue")
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/01_monthly_revenue_trend.png", dpi=150)
print("📈 Chart saved: 01_monthly_revenue_trend.png")

# ============================================================
# 5. TOP 10 CATEGORIES BY REVENUE
# ============================================================
top_cat = (df.groupby("category")["price"]
             .sum()
             .sort_values(ascending=False)
             .head(10))

fig, ax = plt.subplots()
bars = ax.barh(top_cat.index[::-1], top_cat.values[::-1], color="#4CAF50")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))
for bar, val in zip(bars, top_cat.values[::-1]):
    ax.text(val * 1.01, bar.get_y() + bar.get_height()/2,
            f"R${val/1e6:.2f}M", va="center", fontsize=8)
ax.set_title("Top 10 Product Categories by Revenue", fontsize=14, fontweight="bold")
ax.set_xlabel("Revenue")
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/02_top10_categories_revenue.png", dpi=150)
print("📊 Chart saved: 02_top10_categories_revenue.png")

# ============================================================
# 6. ORDER STATUS DISTRIBUTION
# ============================================================
status_counts = df.drop_duplicates("order_id")["order_status"].value_counts()
total_orders_cnt = status_counts.sum()

fig, ax = plt.subplots(figsize=(8, 5))
wedges, texts = ax.pie(
    status_counts,
    labels=None,
    startangle=140,
    colors=sns.color_palette("Set2", len(status_counts)),
    wedgeprops=dict(width=0.4, edgecolor='white', linewidth=1.5)
)

legend_labels = [f"{s.replace('_', ' ').capitalize()}: {c:,} ({c/total_orders_cnt*100:.1f}%)" 
                 for s, c in status_counts.items()]
ax.legend(wedges, legend_labels, title="Order Status", loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9, frameon=True)
ax.text(0, 0, f"Total Orders\n{total_orders_cnt:,}", ha='center', va='center', fontsize=11, fontweight='bold')
ax.set_title("Order Status Distribution", fontsize=14, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/03_order_status_distribution.png", dpi=150, bbox_inches='tight')
print("🍩 Chart saved: 03_order_status_distribution.png")

# ============================================================
# 7. LATE DELIVERY ANALYSIS
# ============================================================
late_by_state = (delivered.drop_duplicates("order_id")
                           .groupby("customer_state")["is_late"]
                           .mean()
                           .sort_values(ascending=False)
                           .head(10) * 100)

fig, ax = plt.subplots()
bars = ax.bar(late_by_state.index, late_by_state.values, color="#F44336")
for bar, val in zip(bars, late_by_state.values):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.5,
            f"{val:.1f}%", ha="center", fontsize=8)
ax.set_title("Top 10 States by Late Delivery Rate", fontsize=14, fontweight="bold")
ax.set_xlabel("State"); ax.set_ylabel("Late Delivery %")
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/04_late_delivery_by_state.png", dpi=150)
print("🚚 Chart saved: 04_late_delivery_by_state.png")

# ============================================================
# 8. REVIEW SCORE DISTRIBUTION
# ============================================================
review_dist = df.drop_duplicates("order_id")["review_score"].value_counts().sort_index()
colors = ["#F44336","#FF9800","#FFC107","#8BC34A","#4CAF50"]

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(review_dist.index.astype(str), review_dist.values, color=colors)
for bar, val in zip(bars, review_dist.values):
    ax.text(bar.get_x() + bar.get_width()/2, val + 100,
            f"{val:,}", ha="center", fontsize=9)
ax.set_title("Review Score Distribution (1–5 Stars)", fontsize=14, fontweight="bold")
ax.set_xlabel("Review Score"); ax.set_ylabel("Number of Orders")
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/05_review_score_distribution.png", dpi=150)
print("⭐ Chart saved: 05_review_score_distribution.png")

# ============================================================
# 9. PAYMENT TYPE ANALYSIS
# ============================================================
pay_type = (payments.groupby("payment_type")["payment_value"]
                     .sum()
                     .sort_values(ascending=False))
total_pay_val = pay_type.sum()

fig, ax = plt.subplots(figsize=(8, 5))
wedges, texts = ax.pie(
    pay_type,
    labels=None,
    startangle=140,
    colors=sns.color_palette("Set2", len(pay_type)),
    wedgeprops=dict(width=0.4, edgecolor='white', linewidth=1.5)
)

pay_legend_labels = [f"{ptype.replace('_', ' ').title()}: R${val/1e6:.2f}M ({val/total_pay_val*100:.1f}%)" 
                     for ptype, val in pay_type.items()]
ax.legend(wedges, pay_legend_labels, title="Payment Method", loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9, frameon=True)
ax.text(0, 0, f"Total Value\nR${total_pay_val/1e6:.2f}M", ha='center', va='center', fontsize=11, fontweight='bold')
ax.set_title("Payment Type Share by Value", fontsize=14, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/06_payment_type_share.png", dpi=150, bbox_inches='tight')
print("💳 Chart saved: 06_payment_type_share.png")

# ============================================================
# 10. RFM CUSTOMER SEGMENTATION
# ============================================================
print("\n🎯 Running RFM Customer Segmentation...")

snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)

rfm = (df.groupby("customer_unique_id")
         .agg(
             Recency   = ("order_purchase_timestamp", lambda x: (snapshot_date - x.max()).days),
             Frequency = ("order_id", "nunique"),
             Monetary  = ("price", "sum")
         )
         .reset_index())

# Score 1-5 (5 = best)
rfm["R_Score"] = pd.qcut(rfm["Recency"],   5, labels=[5,4,3,2,1]).astype(int)
rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm["M_Score"] = pd.qcut(rfm["Monetary"],  5, labels=[1,2,3,4,5]).astype(int)
rfm["RFM_Score"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]

# Segment
def segment(score):
    if score >= 13:  return "🏆 Champions"
    elif score >= 10: return "💛 Loyal Customers"
    elif score >= 7:  return "🔄 Potential Loyalists"
    elif score >= 5:  return "🆕 Recent Customers"
    else:             return "😴 At Risk"

rfm["Segment"] = rfm["RFM_Score"].apply(segment)

seg_summary = rfm.groupby("Segment").agg(
    Customers=("customer_unique_id","count"),
    Avg_Recency=("Recency","mean"),
    Avg_Frequency=("Frequency","mean"),
    Avg_Monetary=("Monetary","mean")
).round(1)

print("\n📋 RFM Segment Summary:")
print(seg_summary.to_string())

fig, ax = plt.subplots(figsize=(8, 5))
seg_counts = rfm["Segment"].value_counts()
bars = ax.barh(seg_counts.index, seg_counts.values, color=sns.color_palette("Set2", len(seg_counts)))
for bar, val in zip(bars, seg_counts.values):
    ax.text(val + 50, bar.get_y() + bar.get_height()/2,
            f"{val:,}", va="center", fontsize=9)
ax.set_title("Customer Segmentation (RFM Analysis)", fontsize=14, fontweight="bold")
ax.set_xlabel("Number of Customers")
plt.tight_layout()
plt.savefig(f"{REPORTS_DIR}/07_rfm_segmentation.png", dpi=150)
print("👥 Chart saved: 07_rfm_segmentation.png")

# Save RFM results
rfm.to_csv(f"{REPORTS_DIR}/rfm_customer_segments.csv", index=False)
print("💾 RFM data saved: rfm_customer_segments.csv")

# ============================================================
# ✅ DONE
# ============================================================
print("\n" + "="*55)
print("✅ EDA Complete! All charts saved to /reports folder.")
print(f"   Path: {REPORTS_DIR}")
print("="*55)


