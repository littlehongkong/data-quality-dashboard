import streamlit as st

from services.adjustment_factor_service import (
    load_adjustment_factor_master_parquet,
    validate_adjustment_factor_integrity,
    load_recent_adj_prices_from_athena,
    compute_adjusted_prices_backadjust,
    build_adj_price_sparkline
)
from utils.styles import integrity_style
from streamlit.column_config import LineChartColumn


TARGET_EVENT_COUNTRIES = ["USA", "KOR"]


def render_adjustment_factor_view(trd_dt: str):
    st.subheader("📊 Price Integrity Check (Adjustment Factor)")
    st.caption("stage=validated / adjustment_factor_master.parquet 기반")

    # --------------------------------------------------
    # 1️⃣ Filters
    # --------------------------------------------------
    country = st.selectbox(
        "country_code",
        TARGET_EVENT_COUNTRIES,
        index=0,
        key="adjustment_factor_view_country",
    )

    # --------------------------------------------------
    # 2️⃣ Load adjustment_factor_master
    # --------------------------------------------------
    with st.spinner("Loading adjustment_factor_master parquet..."):
        df_factor = load_adjustment_factor_master_parquet(
            trd_dt=trd_dt,
            country_code=country,
        )

    if df_factor.empty:
        st.warning("adjustment_factor_master.parquet 가 비어있습니다.")
        return

    df_factor = df_factor

    # 2) 대상 security_id
    security_ids = df_factor["security_id"].unique().tolist()

    # 3️⃣ raw close (Athena)
    df_close = load_recent_adj_prices_from_athena(
        security_ids,
        country,
        trd_dt,
        window=20,
    )

    # -----------------------------------------
    # ⭐ ticker 붙이기 (여기가 정답 위치)
    # -----------------------------------------
    df_ticker = (
        df_close[["security_id", "ticker"]]
        .dropna()
        .drop_duplicates(subset=["security_id"])
    )

    df_factor = df_factor.merge(
        df_ticker,
        on="security_id",
        how="left",
    )

    # 4) adjusted_price 계산
    df_adj = compute_adjusted_prices_backadjust(df_close, df_factor)

    # 5) sparkline dict
    sparkline_map = build_adj_price_sparkline(df_adj)

    # 6) factor DF에 컬럼 추가
    df_factor["adj_price_20d"] = df_factor["security_id"].map(sparkline_map)

    # --------------------------------------------------
    # 3️⃣ Integrity validation
    # --------------------------------------------------
    df_checked = validate_adjustment_factor_integrity(df_factor)

    # --------------------------------------------------
    # 4️⃣ Summary
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 5️⃣ Detail
    # --------------------------------------------------
    st.subheader("② Adjustment Factor Detail")

    show_cols = [
        c for c in [
            "security_id",
            "ticker",
            "effective_date",  # ✅ event_dt → effective_date
            "factor_type",
            "factor",
            "adjustment_factor",  # ✅ factor → adjustment_factor
            "adj_price_20d",  # ✅ sparkline 컬럼 추가
            "reference_price",
            "reference_date",
            "dividend_amount",
            "status",
            "reason",
        ]
        if c in df_checked.columns
    ]

    st.dataframe(
        df_checked[show_cols],
        column_config={
            "adj_price_20d": LineChartColumn(
                label="Adj Price (20D)",
                help="최근 20거래일 수정종가 (close × cumulative factor)",
                width="medium",
            )
        },
        use_container_width=True,
    )

    # --------------------------------------------------
    # 6️⃣ Unresolved / Check required
    # --------------------------------------------------
    st.text("❗ Status UNRESOLVED / Check Required")

    bad = df_checked[df_checked["status"] != "RESOLVED"]
    if bad.empty:
        st.success("모든 adjustment_factor 이벤트가 정상입니다.")
    else:
        st.dataframe(
            bad[show_cols]
            .style.applymap(integrity_style, subset=["status"]),
            use_container_width=True,
        )
