# ============================================================
# 🛒 Olist E-Commerce — AI-Powered Analytics Platform
# Author: Manoj (Data Analyst)
# Built with: Streamlit · Plotly · Scikit-Learn · Pandas
# ============================================================

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestClassifier

# ── Page Configuration ───────────────────────────────────────
st.set_page_config(
    page_title="Olist E-Commerce AI Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #2563eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        background-color: #f1f5f9;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ── File Paths ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# ── Cached Data Loader ───────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    orders = pd.read_csv(
        os.path.join(DATA_DIR, "olist_orders_dataset.csv"),
        parse_dates=["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    )
    items = pd.read_csv(os.path.join(DATA_DIR, "olist_order_items_dataset.csv"))
    customers = pd.read_csv(os.path.join(DATA_DIR, "olist_customers_dataset.csv"))
    products = pd.read_csv(os.path.join(DATA_DIR, "olist_products_dataset.csv"))
    sellers = pd.read_csv(os.path.join(DATA_DIR, "olist_sellers_dataset.csv"))
    payments = pd.read_csv(os.path.join(DATA_DIR, "olist_order_payments_dataset.csv"))
    reviews = pd.read_csv(os.path.join(DATA_DIR, "olist_order_reviews_dataset.csv"))
    category = pd.read_csv(os.path.join(DATA_DIR, "product_category_name_translation.csv"))

    # English Category translation
    products = products.merge(category, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(products["product_category_name"]).str.replace("_", " ").str.title()

    # Merge Orders + Customers
    orders_cust = orders.merge(customers[["customer_id", "customer_unique_id", "customer_state", "customer_city"]], on="customer_id", how="left")
    
    # Merge Items
    df = items.merge(orders_cust, on="order_id", how="left")
    df = df.merge(products[["product_id", "category", "product_weight_g"]], on="product_id", how="left")
    df = df.merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
    
    # Latest reviews (deduplicated)
    rev_unique = reviews.sort_values("review_creation_date", ascending=False).drop_duplicates("order_id")
    df = df.merge(rev_unique[["order_id", "review_score"]], on="order_id", how="left")

    # Calculated columns
    df["delivery_days"] = (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.days
    df["is_late"] = (
        (df["order_status"] == "delivered") &
        (df["order_delivered_customer_date"] > df["order_estimated_delivery_date"])
    ).astype(int)
    df["purchase_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    df["same_state"] = (df["customer_state"] == df["seller_state"]).astype(int)

    # Load RFM if precalculated
    rfm_path = os.path.join(REPORTS_DIR, "rfm_customer_segments.csv")
    if os.path.exists(rfm_path):
        rfm = pd.read_csv(rfm_path)
    else:
        rfm = pd.DataFrame()

    return df, payments, rfm

with st.spinner("⚡ Loading Olist E-Commerce dataset..."):
    df, payments, rfm = load_data()

# ── Sidebar Controls ─────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/shopping-cart.png", width=70)
st.sidebar.title("🛒 Olist Analytics")
st.sidebar.caption("Full-Stack BI & AI Platform")

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")

all_states = sorted(df["customer_state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect("Select Customer State(s)", options=all_states, default=[])

# Apply state filter if selected
filtered_df = df[df["customer_state"].isin(selected_states)] if selected_states else df

st.sidebar.markdown("---")
st.sidebar.info("""
**Project Stack**:
- 🗄️ PostgreSQL (DDL & BI Views)
- 📊 Power BI (DirectQuery & DAX)
- 🐍 Python & Streamlit
- 🤖 Scikit-Learn Predictive AI
""")

# ── Top Hero & KPIs ──────────────────────────────────────────
st.title("🛒 Brazilian E-Commerce Analytics Platform")
st.markdown("Interactive Business Intelligence & Machine Learning dashboard analyzing **100,000+ orders** from Olist Marketplace.")

# High-Level KPIs
delivered_df = filtered_df[filtered_df["order_status"] == "delivered"]
total_rev = filtered_df["price"].sum()
total_orders = filtered_df["order_id"].nunique()
unique_customers = filtered_df["customer_unique_id"].nunique()
aov = total_rev / total_orders if total_orders > 0 else 0
on_time_pct = (1 - delivered_df["is_late"].mean()) * 100 if len(delivered_df) > 0 else 0
avg_rating = filtered_df["review_score"].mean()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("💰 Total Revenue", f"R$ {total_rev/1e6:.2f}M")
col2.metric("🛒 Total Orders", f"{total_orders:,}")
col3.metric("👥 Customers", f"{unique_customers:,}")
col4.metric("📦 Avg Order Value", f"R$ {aov:.1f}")
col5.metric("✅ On-Time Delivery", f"{on_time_pct:.1f}%")
col6.metric("⭐ Avg Rating", f"{avg_rating:.2f} / 5")

st.markdown("---")

# ── Navigation Tabs ──────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive BI Overview",
    "🚚 Logistics & Operations",
    "👥 RFM Customer Segments",
    "🔮 AI Delivery Risk Predictor",
    "💡 Executive Insights Copilot"
])

# ============================================================
# TAB 1: EXECUTIVE BI OVERVIEW
# ============================================================
with tab1:
    st.subheader("📈 Revenue Trends & Product Performance")
    
    col_t1, col_t2 = st.columns([7, 5])
    
    with col_t1:
        # Monthly Revenue Trend
        monthly = filtered_df.groupby("purchase_month")["price"].sum().reset_index()
        monthly = monthly[monthly["purchase_month"] >= "2017-01"] # clean full period
        fig_trend = px.line(
            monthly, x="purchase_month", y="price",
            title="Monthly Revenue Trend (2017–2018)",
            markers=True,
            labels={"purchase_month": "Month", "price": "Revenue (R$)"}
        )
        fig_trend.update_traces(line_color="#2563eb", line_width=3, fill="tozeroy", fillcolor="rgba(37,99,235,0.1)")
        fig_trend.update_layout(height=380, hovermode="x unified")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_t2:
        # Order Status Donut Chart
        status_counts = filtered_df.drop_duplicates("order_id")["order_status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig_status = px.pie(
            status_counts, names="status", values="count",
            hole=0.55,
            title="Order Fulfillment Status",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_traces(textposition='inside', textinfo='percent')
        fig_status.update_layout(height=380, legend=dict(orientation="v", y=0.5))
        st.plotly_chart(fig_status, use_container_width=True)

    col_b1, col_b2 = st.columns([7, 5])

    with col_b1:
        # Top 10 Product Categories by Revenue
        top_cats = filtered_df.groupby("category")["price"].sum().nlargest(10).reset_index()
        fig_cat = px.bar(
            top_cats.sort_values("price", ascending=True),
            x="price", y="category", orientation="h",
            title="Top 10 Product Categories by Revenue",
            labels={"price": "Revenue (R$)", "category": ""},
            color="price",
            color_continuous_scale="Blues"
        )
        fig_cat.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_b2:
        # Payment Type Share
        pay_order = filtered_df[["order_id"]].drop_duplicates().merge(payments, on="order_id", how="inner")
        pay_summary = pay_order.groupby("payment_type")["payment_value"].sum().reset_index()
        pay_summary["payment_type"] = pay_summary["payment_type"].str.replace("_", " ").str.title()
        fig_pay = px.pie(
            pay_summary, names="payment_type", values="payment_value",
            hole=0.55,
            title="Payment Method Breakdown (by Value)",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pay.update_layout(height=380)
        st.plotly_chart(fig_pay, use_container_width=True)

# ============================================================
# TAB 2: LOGISTICS & OPERATIONS
# ============================================================
with tab2:
    st.subheader("🚚 Delivery Lead Times & Delay Analysis")

    c_log1, c_log2 = st.columns(2)

    with c_log1:
        # Late Delivery by State
        late_state = delivered_df.drop_duplicates("order_id").groupby("customer_state")["is_late"].agg(["mean", "count"]).reset_index()
        late_state = late_state[late_state["count"] >= 50].sort_values("mean", ascending=False).head(10)
        late_state["late_pct"] = late_state["mean"] * 100
        fig_late = px.bar(
            late_state, x="customer_state", y="late_pct",
            title="Top 10 States with Highest Late Delivery Rate (%)",
            labels={"customer_state": "State", "late_pct": "Late Deliveries (%)"},
            color="late_pct",
            color_continuous_scale="Reds"
        )
        fig_late.add_hline(y=7.8, line_dash="dash", line_color="black", annotation_text="National Avg (7.8%)")
        fig_late.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig_late, use_container_width=True)

    with c_log2:
        # Review score: On-time vs Late
        rev_delivery = delivered_df.drop_duplicates("order_id").groupby("is_late")["review_score"].mean().reset_index()
        rev_delivery["Delivery Status"] = rev_delivery["is_late"].map({0: "✅ On-Time Delivery", 1: "⚠️ Late Delivery"})
        fig_rev = px.bar(
            rev_delivery, x="Delivery Status", y="review_score",
            title="Impact of Delivery Timeliness on Customer Review Rating",
            labels={"review_score": "Average Rating (1-5)"},
            color="Delivery Status",
            color_discrete_map={"✅ On-Time Delivery": "#10b981", "⚠️ Late Delivery": "#ef4444"},
            text_auto=".2f"
        )
        fig_rev.update_layout(height=380, yaxis_range=[1, 5], showlegend=False)
        st.plotly_chart(fig_rev, use_container_width=True)

# ============================================================
# TAB 3: RFM CUSTOMER SEGMENTATION
# ============================================================
with tab3:
    st.subheader("👥 RFM Customer Loyalty & Value Segmentation")

    if not rfm.empty:
        col_rfm1, col_rfm2 = st.columns([5, 7])

        with col_rfm1:
            seg_counts = rfm["Segment"].value_counts().reset_index()
            seg_counts.columns = ["Segment", "Customers"]
            fig_rfm = px.bar(
                seg_counts, y="Segment", x="Customers", orientation="h",
                title="Customer Distribution by RFM Segment",
                color="Segment",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_rfm.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig_rfm, use_container_width=True)

        with col_rfm2:
            st.markdown("#### 📋 Segment Metrics & Strategic Actions")
            rfm_summary = rfm.groupby("Segment").agg(
                Customers=("customer_unique_id", "count"),
                Avg_Recency_Days=("Recency", "mean"),
                Avg_Spend_R=("Monetary", "mean")
            ).round(1).reset_index()
            
            st.dataframe(rfm_summary, use_container_width=True, hide_index=True)

            st.success("""
            **Key Strategic Takeaway**:
            - **🏆 Champions**: ~8K top buyers spending R$ 314 on average. Enroll in VIP loyalty & early-access promos.
            - **🔄 Potential Loyalists**: 39K+ buyers (~41% of user base). Prime candidates for automated reactivation coupons!
            """)
    else:
        st.warning("RFM data file not found. Run python/eda_analysis.py to generate.")

# ============================================================
# TAB 4: AI LATE DELIVERY RISK PREDICTOR (MACHINE LEARNING)
# ============================================================
with tab4:
    st.subheader("🔮 Machine Learning: Real-Time Late Delivery Risk Predictor")
    st.markdown("""
    This predictive model is trained using **Random Forest Classification** to estimate the likelihood 
    that an order will experience shipping delays based on order weight, freight cost, price, and route geography.
    """)

    # Train a lightweight fast model on cached data
    @st.cache_resource(show_spinner=False)
    def train_delay_model(data):
        valid = data[data["order_status"] == "delivered"].dropna(subset=["product_weight_g", "freight_value", "price", "is_late", "same_state"])
        sample = valid.sample(n=min(30000, len(valid)), random_state=42)
        X = sample[["product_weight_g", "freight_value", "price", "same_state"]]
        y = sample["is_late"]
        model = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42)
        model.fit(X, y)
        return model

    with st.spinner("Training predictive model..."):
        ml_model = train_delay_model(df)

    col_sim1, col_sim2 = st.columns([5, 7])

    with col_sim1:
        st.markdown("#### 🎛️ Order Parameters")
        weight = st.slider("Product Weight (grams)", min_value=50, max_value=15000, value=1200, step=50)
        freight = st.slider("Freight Value (R$)", min_value=5.0, max_value=150.0, value=22.5, step=1.0)
        price = st.number_input("Product Price (R$)", min_value=10.0, max_value=2000.0, value=129.0, step=10.0)
        same_state = st.radio("Delivery Route", options=["Different State (Interstate)", "Same State (Local)"], index=0)
        is_same_state_val = 1 if "Same State" in same_state else 0

    with col_sim2:
        st.markdown("#### 🤖 Model Prediction")
        input_data = pd.DataFrame([{
            "product_weight_g": weight,
            "freight_value": freight,
            "price": price,
            "same_state": is_same_state_val
        }])

        prob_late = ml_model.predict_proba(input_data)[0][1] * 100

        # Gauge / Meter
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob_late,
            number={'suffix': "%", 'valueformat': ".1f"},
            title={'text': "Predicted Delay Risk"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#ef4444" if prob_late > 25 else "#10b981"},
                'steps': [
                    {'range': [0, 15], 'color': "#dcfce7"},
                    {'range': [15, 30], 'color': "#fef9c3"},
                    {'range': [30, 100], 'color': "#fee2e2"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 3},
                    'thickness': 0.75,
                    'value': 30
                }
            }
        ))
        fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

        if prob_late > 30:
            st.error(f"⚠️ **High Delay Risk ({prob_late:.1f}%)**: Significant probability of late delivery. Recommend upgrading to an express carrier or establishing a regional fulfillment hub.")
        elif prob_late > 15:
            st.warning(f"🟡 **Moderate Risk ({prob_late:.1f}%)**: Monitor dispatch time closely to ensure compliance with estimated SLA.")
        else:
            st.success(f"✅ **Low Risk ({prob_late:.1f}%)**: Standard ground shipping is expected to arrive on or before the estimated date.")

# ============================================================
# TAB 5: EXECUTIVE INSIGHTS COPILOT
# ============================================================
with tab5:
    st.subheader("💡 Strategic Business Briefing")
    
    st.markdown("""
    ### 🎯 Executive Summary & Actionable Recommendations

    #### 1. 🚚 Logistics Optimization (Direct Impact on Review Ratings)
    - **Finding**: On-time orders average a **4.17 / 5.0** rating, whereas late deliveries plummet to **2.25 / 5.0**.
    - **Action**: Partner with local 3PL carriers in North & Northeast states (e.g., Alagoas, Amazonas) where late delivery rates reach 15–20%.

    #### 2. 💳 Payment & AOV Expansion
    - **Finding**: **73.9%** of GMV is transacted via Credit Cards, with customers utilizing multi-month installments.
    - **Action**: Partner with fintech gateways (Pix / Boleto Parcelado) to offer interest-free installments to cash-reliant buyers.

    #### 3. 👥 Customer Retention Opportunity (RFM)
    - **Finding**: **41% of total customers** fall into the **Potential Loyalists** segment with single purchases in mid-to-high spend tiers.
    - **Action**: Implement automated post-purchase email triggers (30-day replenishment discount) to capture repeat orders.

    ---
    *Built by **Manoj** | Data Analyst Portfolio Project*
    """)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption("Olist Brazilian E-Commerce Analytics Platform | Live Demo built with Streamlit, Plotly & Scikit-Learn.")
