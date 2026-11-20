"""
Bihar Electric Consumer Complaints - Daily Monitoring & Analytics Dashboard
Compatible with: SBPDCL, NBPDCL, and BSPHCL Statewide Data
"""

import os
import glob
import json
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Import pipeline runner
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
import data_pipeline

# Configure Streamlit Page
st.set_page_config(
    page_title="Bihar CHS 1912 | Consumer Complaints Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Clean Utility Dashboard
st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"]:hover {
        border-color: #0284c7;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.85rem !important;
        font-weight: 600;
        color: #475569;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700;
        color: #0f172a;
    }
    /* Header branding */
    .discom-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        margin-right: 8px;
    }
    .badge-sbpdcl { background-color: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
    .badge-nbpdcl { background-color: #dcfce7; color: #166534; border: 1px solid #86efac; }
    .status-pill {
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .pill-green { background-color: #dcfce7; color: #15803d; }
    .pill-red { background-color: #fee2e2; color: #b91c1c; }
    .pill-yellow { background-color: #fef9c3; color: #a16207; }

    /* Hide Flonnect & 3rd-party screen recorder extension overlays */
    [id*="flonnect"], [class*="flonnect"],
    flonnect-recorder, #flonnect-root, .flonnect-container,
    #flonnect-screen-recorder, flonnect-extension-root,
    div[data-flonnect], [id*="screen-recorder-extension"],
    iframe[src*="flonnect"], #flonnect-widget {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
        position: absolute !important;
        left: -99999px !important;
        z-index: -99999 !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_data():
    """Loads master complaints dataset from processed parquet or runs pipeline if missing."""
    if not os.path.exists(data_pipeline.MASTER_PARQUET):
        data_pipeline.run_pipeline()
        
    if os.path.exists(data_pipeline.MASTER_PARQUET):
        try:
            df = pd.read_parquet(data_pipeline.MASTER_PARQUET)
            return df
        except Exception:
            if os.path.exists(data_pipeline.MASTER_CSV):
                return pd.read_csv(data_pipeline.MASTER_CSV, low_memory=False)
    return pd.DataFrame()

def load_pipeline_logs():
    """Loads sync log history."""
    if os.path.exists(data_pipeline.LOG_FILE):
        try:
            with open(data_pipeline.LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

# Load data
df_raw = load_data()

# --- TOP HEADER & BRANDING ---
col_logo, col_title, col_actions = st.columns([1, 6, 3])

with col_logo:
    st.markdown("<h1 style='font-size: 3.2rem; margin: 0;'>⚡</h1>", unsafe_allow_html=True)

with col_title:
    st.markdown("""
        <div style='margin-top: 5px;'>
            <h2 style='margin: 0; padding: 0; color: #0f172a; font-weight: 800;'>
                Bihar CHS 1912 - Consumer Complaints Dashboard
            </h2>
            <div style='margin-top: 6px;'>
                <span class='discom-badge badge-sbpdcl'>SBPDCL (South Bihar)</span>
                <span class='discom-badge badge-nbpdcl'>NBPDCL (North Bihar)</span>
                <span style='font-size: 0.85rem; color: #64748b;'>Centralized 1912 Helpline & Grievance Redressal Monitoring Portal</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_actions:
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🔄 Sync Drop Folder", use_container_width=True, help="Scan data/input/ folder for new daily .xlsx files"):
            with st.spinner("Processing files from drop folder..."):
                res = data_pipeline.run_pipeline()
                st.cache_data.clear()
                st.rerun()
    with c_btn2:
        with st.popover("📤 Upload File"):
            st.write("**Drop daily report directly:**")
            uploaded_file = st.file_uploader("Upload .xlsx or .csv", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
            if uploaded_file is not None:
                save_path = os.path.join(data_pipeline.INPUT_DIR, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                with st.spinner("Ingesting uploaded report..."):
                    data_pipeline.run_pipeline()
                    st.cache_data.clear()
                    st.success("File uploaded & processed!")
                    st.rerun()

st.divider()

if df_raw.empty:
    st.warning("⚠️ No complaints data found yet. Drop an `.xlsx` report file into `data/input/` or click 'Upload File' above.")
    st.stop()

# Ensure datetime types
if 'CREATED_DATETIME' in df_raw.columns and not pd.api.types.is_datetime64_any_dtype(df_raw['CREATED_DATETIME']):
    df_raw['CREATED_DATETIME'] = pd.to_datetime(df_raw['CREATED_DATETIME'], errors='coerce')
if 'CLOSING_DATETIME' in df_raw.columns and not pd.api.types.is_datetime64_any_dtype(df_raw['CLOSING_DATETIME']):
    df_raw['CLOSING_DATETIME'] = pd.to_datetime(df_raw['CLOSING_DATETIME'], errors='coerce')

# --- SIDEBAR FILTERS ---
st.sidebar.markdown("### 🎛️ Dashboard Filters")

# 1. DISCOM Filter
all_discoms = ["All"] + sorted([x for x in df_raw['DISCOM'].dropna().unique().tolist() if x])
selected_discom = st.sidebar.selectbox("DISCOM", all_discoms, index=0)

df_filtered = df_raw.copy()
if selected_discom != "All":
    df_filtered = df_filtered[df_filtered['DISCOM'] == selected_discom]

# 2. Date Range Filter
min_date = df_filtered['CREATED_DATETIME'].min().date() if df_filtered['CREATED_DATETIME'].notna().any() else datetime.now().date()
max_date = df_filtered['CREATED_DATETIME'].max().date() if df_filtered['CREATED_DATETIME'].notna().any() else datetime.now().date()

if min_date == max_date:
    st.sidebar.info(f"📅 Report Date: **{min_date.strftime('%d-%b-%Y')}**")
    date_range = (min_date, max_date)
else:
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
    df_filtered = df_filtered[(df_filtered['CREATED_DATETIME'].dt.date >= start_d) & 
                              (df_filtered['CREATED_DATETIME'].dt.date <= end_d)]

# 3. Status Filter
status_options = ["All", "Closed Within SLA", "Closed Beyond SLA", "Pending Within SLA", "Pending Beyond SLA (Overdue)"]
selected_status = st.sidebar.selectbox("SLA Status", status_options, index=0)
if selected_status != "All":
    if selected_status == "Closed Within SLA":
        df_filtered = df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Closed') & (~df_filtered['SLA_BREACHED'])]
    elif selected_status == "Closed Beyond SLA":
        df_filtered = df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Closed') & (df_filtered['SLA_BREACHED'])]
    elif selected_status == "Pending Within SLA":
        df_filtered = df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Pending') & (~df_filtered['SLA_BREACHED'])]
    elif selected_status == "Pending Beyond SLA (Overdue)":
        df_filtered = df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Pending') & (df_filtered['SLA_BREACHED'])]

# 4. Complaint Category Filter
cat_options = ["All"] + sorted([x for x in df_filtered['COMPLAINT_TYPE'].dropna().unique().tolist() if x])
selected_cat = st.sidebar.selectbox("Complaint Category", cat_options, index=0)
if selected_cat != "All":
    df_filtered = df_filtered[df_filtered['COMPLAINT_TYPE'] == selected_cat]

# 5. Area Type Filter
area_options = ["All"] + sorted([x for x in df_filtered['AREA_TYPE'].dropna().unique().tolist() if x])
selected_area = st.sidebar.selectbox("Area Type (Urban/Rural)", area_options, index=0)
if selected_area != "All":
    df_filtered = df_filtered[df_filtered['AREA_TYPE'] == selected_area]

# 6. Cascading Geographic Filters: Circle -> Division
st.sidebar.markdown("---")
st.sidebar.markdown("**📍 Administrative Drill-down**")

available_circles = sorted([x for x in df_filtered['CIRCLE'].dropna().unique().tolist() if x])
selected_circles = st.sidebar.multiselect("Circle", available_circles, default=[])
if selected_circles:
    df_filtered = df_filtered[df_filtered['CIRCLE'].isin(selected_circles)]

available_divisions = sorted([x for x in df_filtered['DIVISION'].dropna().unique().tolist() if x])
selected_divisions = st.sidebar.multiselect("Division", available_divisions, default=[])
if selected_divisions:
    df_filtered = df_filtered[df_filtered['DIVISION'].isin(selected_divisions)]

# Smart meter vendor filter
if 'SM_VENDOR_CLEAN' in df_filtered.columns:
    vendors = sorted([x for x in df_filtered['SM_VENDOR_CLEAN'].dropna().unique().tolist() if x])
    if vendors:
        selected_vendor = st.sidebar.selectbox("Smart Meter Vendor", ["All"] + vendors, index=0)
        if selected_vendor != "All":
            df_filtered = df_filtered[df_filtered['SM_VENDOR_CLEAN'] == selected_vendor]

st.sidebar.markdown("---")
st.sidebar.caption("💡 **Tip**: Drop new daily reports into `data/input/` and click 'Sync Drop Folder'.")


# --- TOP LEVEL KPI METRICS ---
total_complaints = len(df_filtered)
total_closed = len(df_filtered[df_filtered['STATUS_SIMPLIFIED'] == 'Closed'])
total_pending = len(df_filtered[df_filtered['STATUS_SIMPLIFIED'] == 'Pending'])
closed_within_sla = len(df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Closed') & (~df_filtered['SLA_BREACHED'])])
closed_beyond_sla = len(df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Closed') & (df_filtered['SLA_BREACHED'])])
pending_beyond_sla = len(df_filtered[(df_filtered['STATUS_SIMPLIFIED'] == 'Pending') & (df_filtered['SLA_BREACHED'])])

sla_rate = (closed_within_sla / total_closed * 100) if total_closed > 0 else 0.0
avg_time_taken = df_filtered[df_filtered['STATUS_SIMPLIFIED'] == 'Closed']['ACTUAL_HOURS_TAKEN'].mean()
avg_time_str = f"{avg_time_taken:.1f} hrs" if not pd.isna(avg_time_taken) else "N/A"

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Total Inflow", f"{total_complaints:,}", help="Total complaints registered in selected period")
kpi2.metric("Closed / Resolved", f"{total_closed:,}", delta=f"{(total_closed/total_complaints*100):.1f}%" if total_complaints else None)
kpi3.metric("Pending Backlog", f"{total_pending:,}", delta=f"-{total_pending}" if total_pending > 0 else "0", delta_color="inverse")
kpi4.metric("SLA Adherence", f"{sla_rate:.1f}%", help="% of closed complaints resolved within official SLA")
kpi5.metric("Overdue Pending ⚠️", f"{pending_beyond_sla:,}", delta=f"{pending_beyond_sla} Breached" if pending_beyond_sla > 0 else "Clean", delta_color="inverse")
kpi6.metric("Avg. Resolution Time", avg_time_str, help="Average duration from registration to closure")

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)


# --- DASHBOARD TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Executive Summary",
    "⚡ Smart Meter Hub",
    "🔌 Supply & Outages",
    "🗺️ Circle & Division Leaderboard",
    "🚨 Overdue & Pending Tracker",
    "🔍 Search & Data Export"
])

# ==========================================
# TAB 1: EXECUTIVE SUMMARY
# ==========================================
with tab1:
    col_t1_l, col_t1_r = st.columns([7, 5])

    with col_t1_l:
        st.subheader("Complaints by Category & SLA Breakdown")
        cat_sla = df_filtered.groupby(['COMPLAINT_TYPE', 'SLA_CATEGORY']).size().reset_index(name='Count')
        
        # Color mapping for SLA categories
        color_map = {
            'Closed Within SLA': '#10b981',             # Green
            'Closed Beyond SLA': '#f59e0b',             # Amber / Orange
            'Pending Within SLA': '#3b82f6',            # Blue
            'Pending Beyond SLA (Overdue)': '#ef4444'   # Red
        }
        
        fig_cat = px.bar(
            cat_sla,
            x='COMPLAINT_TYPE',
            y='Count',
            color='SLA_CATEGORY',
            color_discrete_map=color_map,
            barmode='stack',
            labels={'COMPLAINT_TYPE': 'Category', 'Count': 'Complaints Count', 'SLA_CATEGORY': 'Resolution Status'},
            title="Distribution Across Complaint Categories"
        )
        fig_cat.update_layout(xaxis_tickangle=-15, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_t1_r:
        st.subheader("SLA Performance Breakdown")
        status_counts = df_filtered['SLA_CATEGORY'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        fig_donut = px.pie(
            status_counts,
            names='Status',
            values='Count',
            hole=0.55,
            color='Status',
            color_discrete_map=color_map,
            title="Overall Resolution & SLA Compliance"
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)

    col_t1_b1, col_t1_b2 = st.columns([6, 6])
    with col_t1_b1:
        st.subheader("Complaint Source Channels")
        if 'SOURCE_OF_COMPLAINT' in df_filtered.columns:
            src_df = df_filtered['SOURCE_OF_COMPLAINT'].value_counts().reset_index()
            src_df.columns = ['Channel', 'Count']
            fig_src = px.bar(
                src_df,
                x='Count',
                y='Channel',
                orientation='h',
                color='Count',
                color_continuous_scale='Blues',
                title="Registration Sources (Toll Free, IVRS, Suvidha, Chatbot, etc.)"
            )
            fig_src.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_src, use_container_width=True)

    with col_t1_b2:
        st.subheader("Urban vs. Rural Distribution")
        if 'AREA_TYPE' in df_filtered.columns:
            area_df = df_filtered.groupby(['AREA_TYPE', 'STATUS_SIMPLIFIED']).size().reset_index(name='Count')
            fig_area = px.bar(
                area_df,
                x='AREA_TYPE',
                y='Count',
                color='STATUS_SIMPLIFIED',
                barmode='group',
                color_discrete_map={'Closed': '#10b981', 'Pending': '#ef4444'},
                title="Complaint Load & Resolution: Urban vs. Rural"
            )
            st.plotly_chart(fig_area, use_container_width=True)


# ==========================================
# TAB 2: SMART METER HUB
# ==========================================
with tab2:
    st.markdown("### ⚡ Smart Meter Diagnostic & Vendor Control Center")
    st.write("Tracking smart prepaid meter grievances, disconnections with positive balance, recharge sync, and vendor performance.")

    df_sm = df_filtered[df_filtered['IS_SMART_METER']].copy()
    if df_sm.empty:
        st.info("No Smart Meter complaints found matching the current filters.")
    else:
        sm_c1, sm_c2, sm_c3, sm_c4 = st.columns(4)
        sm_total = len(df_sm)
        sm_closed = len(df_sm[df_sm['STATUS_SIMPLIFIED'] == 'Closed'])
        sm_pos_disc = len(df_sm[df_sm['COMPLAINT_SUBTYPE'].str.contains('POSITIVE|DISCONNECTED', case=False, na=False)])
        sm_recharge = len(df_sm[df_sm['COMPLAINT_SUBTYPE'].str.contains('RECHARGE', case=False, na=False)])
        
        sm_c1.metric("Total Smart Meter Tickets", f"{sm_total:,}")
        sm_c2.metric("Smart Meter Resolution", f"{(sm_closed/sm_total*100):.1f}%" if sm_total else "0%")
        sm_c3.metric("Positive Balance But Cut ⚠️", f"{sm_pos_disc:,}", help="Major friction: Consumer has money in meter but power is disconnected")
        sm_c4.metric("Recharge Not Updated", f"{sm_recharge:,}", help="Consumer paid online but smart meter did not credit balance")

        col_sm_l, col_sm_r = st.columns([6, 6])
        with col_sm_l:
            st.subheader("Top Smart Meter Grievance Types")
            sm_issues = df_sm['COMPLAINT_SUBTYPE'].value_counts().head(8).reset_index()
            sm_issues.columns = ['Issue Subtype', 'Count']
            fig_sm_sub = px.bar(
                sm_issues,
                y='Issue Subtype',
                x='Count',
                orientation='h',
                color='Count',
                color_continuous_scale='Teal',
                title="Top Subtypes Reported by Smart Meter Consumers"
            )
            fig_sm_sub.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_sm_sub, use_container_width=True)

        with col_sm_r:
            st.subheader("Vendor Performance & SLA Breaches")
            if 'SM_VENDOR_CLEAN' in df_sm.columns:
                vendor_perf = df_sm.groupby('SM_VENDOR_CLEAN').agg(
                    Total=('COMPLAINT_NO', 'count'),
                    Resolved=('STATUS_SIMPLIFIED', lambda x: (x == 'Closed').sum()),
                    Breached=('SLA_BREACHED', 'sum'),
                    Avg_Hours=('ACTUAL_HOURS_TAKEN', 'mean')
                ).reset_index()
                vendor_perf['Breach_Rate_%'] = (vendor_perf['Breached'] / vendor_perf['Total'] * 100).round(1)
                vendor_perf['Avg_Hours'] = vendor_perf['Avg_Hours'].round(1)

                fig_vendor = px.bar(
                    vendor_perf,
                    x='SM_VENDOR_CLEAN',
                    y=['Resolved', 'Breached'],
                    barmode='group',
                    labels={'value': 'Complaints Count', 'SM_VENDOR_CLEAN': 'Smart Meter Agency / Vendor'},
                    color_discrete_map={'Resolved': '#10b981', 'Breached': '#ef4444'},
                    title="Resolved vs. SLA Breached by Meter Agency"
                )
                st.plotly_chart(fig_vendor, use_container_width=True)

        # Detailed Smart Meter Vendor Table
        st.write("**Vendor Scorecard:**")
        st.dataframe(vendor_perf.sort_values(by='Total', ascending=False), use_container_width=True)


# ==========================================
# TAB 3: SUPPLY & OUTAGES
# ==========================================
with tab3:
    st.markdown("### 🔌 Power Supply, Breakdown & Infrastructure Failures")
    
    df_supply = df_filtered[df_filtered['COMPLAINT_TYPE'] == 'Supply Related'].copy()
    if df_supply.empty:
        st.info("No Supply Related complaints found matching the current filters.")
    else:
        sup_c1, sup_c2, sup_c3, sup_c4 = st.columns(4)
        dt_failures = len(df_supply[df_supply['COMPLAINT_SUBTYPE'].str.contains('DT FAILURE|TRANSFORMER', case=False, na=False)])
        fuse_calls = len(df_supply[df_supply['COMPLAINT_SUBTYPE'].str.contains('FUSE', case=False, na=False)])
        breakdowns = len(df_supply[df_supply['COMPLAINT_SUBTYPE'].str.contains('BREAKDOWN|CONDUCTOR', case=False, na=False)])
        volt_fluc = len(df_supply[df_supply['COMPLAINT_SUBTYPE'].str.contains('VOLTAGE', case=False, na=False)])

        sup_c1.metric("Burnt / Failed DT (Transformers) 🔥", f"{dt_failures:,}", delta="Urgent Repair", delta_color="inverse")
        sup_c2.metric("Fuse Off (Area/Individual)", f"{fuse_calls:,}")
        sup_c3.metric("Line Breakdowns / Conductor Snap", f"{breakdowns:,}")
        sup_c4.metric("Voltage Fluctuation / High Volt", f"{volt_fluc:,}")

        col_sup_1, col_sup_2 = st.columns([7, 5])
        with col_sup_1:
            st.subheader("Breakdown of Power Outage Subtypes")
            top_outages = df_supply['COMPLAINT_SUBTYPE'].value_counts().head(10).reset_index()
            top_outages.columns = ['Outage Subtype', 'Count']
            fig_outage = px.bar(
                top_outages,
                x='Count',
                y='Outage Subtype',
                orientation='h',
                color='Count',
                color_continuous_scale='Oranges',
                title="Supply Fault Frequency"
            )
            fig_outage.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_outage, use_container_width=True)

        with col_sup_2:
            st.subheader("Critical Safety & Accidental Issues")
            accidental = df_filtered[df_filtered['COMPLAINT_SUBTYPE'].str.contains('ACCIDENTAL|ELECTROCUTION|SNAPPING', case=False, na=False)]
            st.metric("Reported Electrical Hazards", len(accidental))
            if not accidental.empty:
                st.dataframe(
                    accidental[['COMPLAINT_NO', 'COMPLAINT_SUBTYPE', 'CIRCLE', 'DIVISION', 'SECTION', 'COMPLAINT_STATUS_AS_ON_CURRENT_DATE']].head(10),
                    use_container_width=True
                )
            else:
                st.success("No active accidental hazard complaints in selected filter!")


# ==========================================
# TAB 4: CIRCLE & DIVISION LEADERBOARD
# ==========================================
with tab4:
    st.markdown("### 🗺️ Geographic Performance Leaderboard")
    st.write("Benchmarking Circle, Division, and Section resolution efficiency across Bihar.")

    col_geo_l, col_geo_r = st.columns([6, 6])
    
    with col_geo_l:
        circle_stats = df_filtered.groupby('CIRCLE').agg(
            Total=('COMPLAINT_NO', 'count'),
            Closed=('STATUS_SIMPLIFIED', lambda x: (x == 'Closed').sum()),
            Breached=('SLA_BREACHED', 'sum'),
            Avg_Resolution_Hours=('ACTUAL_HOURS_TAKEN', 'mean')
        ).reset_index()
        circle_stats['SLA_Adherence_%'] = (100 - (circle_stats['Breached'] / circle_stats['Total'] * 100)).round(1)
        circle_stats['Avg_Resolution_Hours'] = circle_stats['Avg_Resolution_Hours'].round(1)

        fig_circle = px.bar(
            circle_stats.sort_values(by='Total', ascending=False).head(12),
            x='CIRCLE',
            y='Total',
            color='SLA_Adherence_%',
            color_continuous_scale='RdYlGn',
            labels={'CIRCLE': 'Electricity Circle', 'Total': 'Total Complaints', 'SLA_Adherence_%': 'SLA %'},
            title="Circle Inflow Volume vs. SLA Compliance %"
        )
        st.plotly_chart(fig_circle, use_container_width=True)

    with col_geo_r:
        st.subheader("Top 5 Circles by Pending & SLA Breaches")
        worst_circles = circle_stats.sort_values(by='Breached', ascending=False).head(5)
        fig_worst = px.pie(
            worst_circles,
            names='CIRCLE',
            values='Breached',
            hole=0.4,
            title="SLA Breaches Share by Circle"
        )
        st.plotly_chart(fig_worst, use_container_width=True)

    st.subheader("Complete Division-Level Operational Matrix")
    div_stats = df_filtered.groupby(['CIRCLE', 'DIVISION']).agg(
        Total=('COMPLAINT_NO', 'count'),
        Closed=('STATUS_SIMPLIFIED', lambda x: (x == 'Closed').sum()),
        Pending=('STATUS_SIMPLIFIED', lambda x: (x == 'Pending').sum()),
        Breached=('SLA_BREACHED', 'sum'),
        Avg_Hours=('ACTUAL_HOURS_TAKEN', 'mean')
    ).reset_index()
    div_stats['SLA_Compliance_%'] = ((div_stats['Closed'] - div_stats['Breached']) / div_stats['Total'] * 100).clip(lower=0).round(1)
    div_stats['Avg_Hours'] = div_stats['Avg_Hours'].round(1)
    
    st.dataframe(
        div_stats.sort_values(by='Total', ascending=False),
        use_container_width=True
    )


# ==========================================
# TAB 5: OVERDUE & PENDING TRACKER
# ==========================================
with tab5:
    st.markdown("### 🚨 Overdue & Pending Complaints Action Center")
    st.write("Track aging of pending tickets, identify SLA violations, and export escalation lists for field officers.")

    df_pending = df_filtered[df_filtered['STATUS_SIMPLIFIED'] == 'Pending'].copy()
    
    if df_pending.empty:
        st.success("🎉 No pending complaints found for the selected filters!")
    else:
        p_c1, p_c2, p_c3, p_c4 = st.columns(4)
        p_c1.metric("Total Open Complaints", len(df_pending))
        p_c2.metric("Pending Beyond SLA ⚠️", len(df_pending[df_pending['SLA_BREACHED']]), delta="Overdue", delta_color="inverse")
        p_c3.metric("Critical Supply Outages", len(df_pending[df_pending['COMPLAINT_TYPE'] == 'Supply Related']))
        p_c4.metric("Pending Meter Issues", len(df_pending[df_pending['IS_SMART_METER']]))

        col_p_l, col_p_r = st.columns([5, 7])
        with col_p_l:
            st.subheader("Aging Analysis")
            aging_counts = df_pending['AGING_BUCKET'].value_counts().reset_index()
            aging_counts.columns = ['Aging Bucket', 'Count']
            fig_aging = px.pie(
                aging_counts,
                names='Aging Bucket',
                values='Count',
                hole=0.45,
                color='Aging Bucket',
                color_discrete_map={
                    '< 24 Hours': '#10b981',
                    '24 - 48 Hours': '#3b82f6',
                    '2 - 7 Days': '#f59e0b',
                    '> 7 Days': '#ef4444'
                },
                title="Pending Complaints Aging"
            )
            st.plotly_chart(fig_aging, use_container_width=True)

        with col_p_r:
            st.subheader("Pending by Category")
            p_cat = df_pending['COMPLAINT_TYPE'].value_counts().reset_index()
            p_cat.columns = ['Category', 'Count']
            fig_p_cat = px.bar(p_cat, x='Category', y='Count', color='Category', title="Categories with Open Backlog")
            st.plotly_chart(fig_p_cat, use_container_width=True)

        st.subheader("Actionable Overdue List (With Field JE Details)")
        overdue_display = df_pending[[
            'COMPLAINT_NO', 'COMPLAINT_TYPE', 'COMPLAINT_SUBTYPE', 'CONSUMER_NAME', 'MOBILE_NO',
            'CIRCLE', 'DIVISION', 'SECTION', 'SLA_HOURS', 'JENAME', 'JEMOBILE', 'COMPLAINT_DETAILS'
        ]].copy()
        
        st.dataframe(overdue_display, use_container_width=True)
        
        # Download button for pending list
        csv_overdue = overdue_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Overdue Complaints List (CSV)",
            data=csv_overdue,
            file_name=f"Bihar_CHS_1912_Overdue_Complaints_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


# ==========================================
# TAB 6: SEARCH & DATA EXPORT
# ==========================================
with tab6:
    st.markdown("### 🔍 Consumer Complaint Search & Data Export")
    
    search_query = st.text_input("🔎 Search by Complaint No, Consumer Name, CA Number, or Mobile Number:", placeholder="e.g. SSU05112600730 or 7488199020 or PATNA")
    
    if search_query:
        q = search_query.strip().lower()
        search_mask = (
            df_filtered['COMPLAINT_NO'].astype(str).str.lower().str.contains(q) |
            df_filtered['CONSUMER_NAME'].astype(str).str.lower().str.contains(q) |
            df_filtered['CUSTOMER_ACCOUNT_NO'].astype(str).str.lower().str.contains(q) |
            df_filtered['MOBILE_NO'].astype(str).str.lower().str.contains(q) |
            df_filtered['SECTION'].astype(str).str.lower().str.contains(q) |
            df_filtered['ADDRESS'].astype(str).str.lower().str.contains(q)
        )
        display_df = df_filtered[search_mask]
        st.write(f"Found **{len(display_df)}** matching complaints:")
    else:
        display_df = df_filtered

    # Select columns to display
    display_cols = [
        'COMPLAINT_NO', 'DISCOM', 'COMPLAINT_TYPE', 'COMPLAINT_SUBTYPE', 'COMPLAINT_STATUS_AS_ON_CURRENT_DATE',
        'CREATED_DATETIME', 'CLOSING_DATETIME', 'ACTUAL_HOURS_TAKEN', 'SLA_HOURS', 'SLA_BREACHED',
        'CONSUMER_NAME', 'MOBILE_NO', 'CUSTOMER_ACCOUNT_NO', 'CIRCLE', 'DIVISION', 'SECTION',
        'SM_VENDOR_CLEAN', 'CLOSING_DETAILS', 'JENAME', 'JEMOBILE'
    ]
    avail_cols = [c for c in display_cols if c in display_df.columns]
    
    st.dataframe(display_df[avail_cols].head(100), use_container_width=True)

    col_exp1, col_exp2 = st.columns([3, 7])
    with col_exp1:
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Data to CSV",
            data=csv_data,
            file_name=f"Bihar_CHS_1912_Complaints_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Ingestion history log
    st.markdown("---")
    st.subheader("📜 Pipeline Ingestion Log & History")
    logs = load_pipeline_logs()
    if logs:
        st.dataframe(pd.DataFrame(logs)[::-1], use_container_width=True)
    else:
        st.info("No pipeline sync logs yet.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #94a3b8; font-size: 0.85rem;'>"
    "Bihar CHS 1912 • Bihar State Power Holding Company Limited (BSPHCL)<br>"
    "SBPDCL & NBPDCL Centralized Grievance & SLA Monitoring System<br>"
    f"System Active • Master Records: {len(df_raw):,} • Generated on {datetime.now().strftime('%d %B %Y')}</div>",
    unsafe_allow_html=True
)
