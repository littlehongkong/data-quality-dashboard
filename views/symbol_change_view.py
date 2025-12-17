# views/event_view.py

import streamlit as st
import pandas as pd
from services.event_service import (
    load_event_log_parquet,
    filter_symbol_change_by_trd_dt,
    validate_symbol_change_integrity,
)
from services.asset_service import load_asset_master_snapshot  # 아래 참고
from utils.styles import integrity_style


TARGET_EVENT_COUNTRIES = ["USA", "KOR"]


def render_symbol_change_view(trd_dt: str):
    st.subheader("🧩 Event Integrity Check (symbol_change)")
    st.caption("stage=event_logs / event_log.parquet 기반")

    country = st.selectbox("country_code", TARGET_EVENT_COUNTRIES, index=0, key='symbol_change_view_country')

    # 1) event log 로드
    with st.spinner("Loading event_logs parquet..."):
        df_log = load_event_log_parquet("symbol_change_events", country)

    if df_log.empty:
        st.warning("event_log.parquet 가 비어있습니다.")
        return

    # 2) 날짜 필터
    df_evt = filter_symbol_change_by_trd_dt(df_log, trd_dt)

    if df_evt.empty:
        st.warning(f"{country} 기준 {trd_dt} 이벤트가 없습니다.")
        return

    # 3) asset_master 로드 (snapshot)
    with st.spinner("Loading asset_master snapshot..."):
        df_asset = load_asset_master_snapshot(trd_dt, country)

    if df_asset.empty or "security_id" not in df_asset.columns:
        st.error("asset_master snapshot 로딩 실패 또는 security_id 컬럼 없음")
        return

    # 4) integrity 계산
    df_checked = validate_symbol_change_integrity(df_evt, df_asset)

    # Summary
    st.subheader("① Integrity Summary")
    summary = (
        df_checked.groupby("status")
        .size()
        .reset_index(name="count")
        .sort_values("status")
    )
    st.dataframe(
        summary.style.applymap(integrity_style, subset=["status"]),
        use_container_width=True,
    )

    # Detail
    st.subheader("② Event Detail")
    show_cols = [c for c in [
        "event_dt", "trd_dt", 'effective',
        "old_symbol", "new_symbol",
        "old_security_id", "new_security_id",
        "exchange_code", 'status', 'reason'
    ] if c in df_checked.columns]

    st.dataframe(
        df_checked[show_cols]
        .style.applymap(integrity_style, subset=["status"]),
        use_container_width=True,
    )

    st.text("❗ Status None (Check Require)")
    bad = df_checked[pd.isna(df_checked["status"])]
    st.dataframe(
        bad[show_cols]
        .style.applymap(integrity_style, subset=["status"]),
        use_container_width=True,
    )
