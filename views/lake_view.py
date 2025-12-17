import streamlit as st
import pandas as pd

from services.lake_service import (
    find_lake_meta,
    build_lake_summary,
)
from services.comparison_service import build_layer_dod_compare
from utils.dates import get_prev_business_day
from utils.styles import status_style, diff_style


def render_lake_tab(trd_dt: str):
    st.subheader("📥 Lake Monitoring")

    # ---------------------------
    # Load Lake Meta
    # ---------------------------
    with st.spinner("Scanning Lake metadata..."):
        lake_rows_today = find_lake_meta(trd_dt)

    if not lake_rows_today:
        st.warning("해당 날짜의 Lake 메타데이터가 없습니다.")
        return

    df_lake_today = pd.DataFrame(lake_rows_today)
    df_lake_summary = build_lake_summary(df_lake_today)

    # ---------------------------
    # ① Summary
    # ---------------------------
    st.subheader("① Lake Summary (Logical Domain 기준)")
    st.dataframe(
        df_lake_summary.style.applymap(status_style, subset=["status"]),
        use_container_width=True,
    )

    # ---------------------------
    # ② Exchange Coverage
    # ---------------------------
    st.subheader("② Lake Exchange Coverage")
    st.dataframe(
        df_lake_today[
            ["logical", "domain", "exchange_code", "status", "record_count", "message"]
        ].style.applymap(status_style, subset=["status"]),
        use_container_width=True,
    )

    # ---------------------------
    # ③ Detail
    # ---------------------------
    with st.expander("③ Lake Detail (Meta Path 포함)"):
        st.dataframe(
            df_lake_today.style.applymap(status_style, subset=["status"]),
            use_container_width=True,
        )

    # ---------------------------
    # ④ DoD Compare
    # ---------------------------
    prev_trd_dt = get_prev_business_day(trd_dt)

    lake_rows_prev = find_lake_meta(prev_trd_dt)
    df_lake_prev = pd.DataFrame(lake_rows_prev) if lake_rows_prev else pd.DataFrame(
        columns=df_lake_today.columns
    )

    df_lake_dod = build_layer_dod_compare(
        df_today=df_lake_today,
        df_prev=df_lake_prev,
        layer="lake",
    )

    st.subheader("④ Lake 전일 대비 데이터 증감 (DoD)")
    st.caption(f"비교 기준일: {prev_trd_dt}")

    st.dataframe(
        df_lake_dod[
            ["logical", "domain", "prev_records", "today_records", "diff", "diff_pct"]
        ]
        .style
        .applymap(diff_style, subset=["diff"])
        .format({"diff_pct": "{:.2f}%"}),
        use_container_width=True,
    )
