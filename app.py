# app.py

import streamlit as st
import pandas as pd

from views.lake_view import render_lake_tab
from views.warehouse_view import render_warehouse_tab
from views.event_view import render_event_view
from services.lake_service import find_lake_meta, build_lake_summary


st.set_page_config(layout="wide")
st.title("📊 Equity Data Monitoring")

trd_dt = st.date_input("📅 기준 거래일").strftime("%Y-%m-%d")

if st.button("▶ Run Monitoring"):

    # Lake 메타 먼저 로드 (warehouse에서 참조용)
    lake_rows = find_lake_meta(trd_dt)
    df_lake = pd.DataFrame(lake_rows)
    df_lake_summary = build_lake_summary(df_lake)

    lake_status_map = df_lake_summary.set_index("logical")["status"].to_dict()

    tab_lake, tab_wh, tab_event = st.tabs(
        ["📥 Lake Monitoring", "📦 Warehouse Coverage", "🧩 Event Integrity"]
    )

    with tab_lake:
        render_lake_tab(trd_dt=trd_dt)

    with tab_wh:
        render_warehouse_tab(trd_dt=trd_dt, lake_status_map=lake_status_map)

    with tab_event:
        render_event_view(trd_dt=trd_dt)
