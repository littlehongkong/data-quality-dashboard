# views/warehouse_view.py

import streamlit as st
import pandas as pd

from services.warehouse_service import (
    find_warehouse_meta,
    build_warehouse_status_pivot,
    build_multi_country_check,
)
from services.comparison_service import build_layer_dod_compare
from utils.dates import get_prev_business_day
from utils.styles import status_style, diff_style, mc_status_style

from services.coverage_service import find_asset_without_price
from services.coverage_service import find_price_without_asset


def render_warehouse_tab(trd_dt: str, lake_status_map: dict):
    st.subheader("📦 Warehouse Coverage")
    st.caption("Lake SUCCESS 도메인 기준으로 해석하세요")

    with st.spinner("Scanning Warehouse metadata..."):
        wh_rows_today = find_warehouse_meta(trd_dt)

    if not wh_rows_today:
        st.warning("해당 날짜의 Warehouse 메타데이터가 없습니다.")
        return

    df_wh_today = pd.DataFrame(wh_rows_today)

    # ---------- Coverage Pivot ----------
    wh_pivot = build_warehouse_status_pivot(df_wh_today)

    def warehouse_cell_style(val, logical):
        lake_status = lake_status_map.get(logical)
        if lake_status in ("failed", "partial"):
            return "background-color:#374151;color:#9ca3af;"
        return status_style(val)

    st.dataframe(
        wh_pivot.style.apply(
            lambda row: [warehouse_cell_style(v, row["logical"]) for v in row],
            axis=1,
        ),
        use_container_width=True,
    )

    # ---------- Detail ----------
    with st.expander("Warehouse Meta Detail"):
        st.dataframe(
            df_wh_today.style.applymap(status_style, subset=["status"]),
            use_container_width=True,
        )

    # ---------- Multi-Country ----------
    st.subheader("Multi-Country Warehouse Domain Check")
    df_mc = build_multi_country_check(df_wh_today)

    st.dataframe(
        df_mc.style.applymap(mc_status_style, subset=["build_status"]),
        use_container_width=True,
    )

    # ---------- DoD ----------
    prev_trd_dt = get_prev_business_day(trd_dt)
    wh_rows_prev = find_warehouse_meta(prev_trd_dt)
    df_wh_prev = pd.DataFrame(wh_rows_prev) if wh_rows_prev else pd.DataFrame(
        columns=df_wh_today.columns
    )

    df_wh_dod = build_layer_dod_compare(
        df_today=df_wh_today,
        df_prev=df_wh_prev,
        layer="warehouse",
    )

    st.subheader("Warehouse 전일 대비 데이터 증감 (DoD)")
    st.caption(f"비교 기준일: {prev_trd_dt}")

    st.dataframe(
        df_wh_dod[
            ["logical", "domain", "prev_records", "today_records", "diff", "diff_pct"]
        ]
        .style
        .applymap(diff_style, subset=["diff"])
        .format({"diff_pct": "{:.2f}%"}),
        use_container_width=True,
    )

    # =========================================================
    # 🔎 Asset vs Price Diff – Drill-down List
    # =========================================================
    with st.expander("🔎 Asset vs Price Diff Detail"):
        st.caption("Asset / Price 간 전일 대비 건수 차이가 발생한 상세 목록")

        # ---------------------------------------------
        # Asset은 있으나 Price가 없는 경우
        # ---------------------------------------------

        try:
            df_asset_only = find_asset_without_price(trd_dt=trd_dt)

            st.markdown(f"### ❗ Asset은 있으나 Price가 없는 종목 : {df_asset_only.shape[0]}건")

            if df_asset_only.empty:
                st.success("차이 없음")
            else:
                st.dataframe(
                    df_asset_only,
                    use_container_width=True,
                )

        except Exception as e:
            st.error(f"Asset > Price 조회 중 오류 발생: {e}")

        st.divider()

        # ---------------------------------------------
        # Price는 있으나 Asset이 없는 경우
        # ---------------------------------------------

        try:

            df_price_only = find_price_without_asset(trd_dt=trd_dt)

            st.markdown(f"### ❗ Price는 있으나 Asset이 없는 종목 : {df_price_only.shape[0]}건")

            if df_price_only.empty:
                st.success("차이 없음")
            else:
                st.dataframe(
                    df_price_only,
                    use_container_width=True,
                )

        except Exception as e:
            st.error(f"Price > Asset 조회 중 오류 발생: {e}")
