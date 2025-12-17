import streamlit as st

from services.adjustment_factor_service import (
    load_adjustment_factor_master_parquet,
    validate_adjustment_factor_integrity,
)
from utils.styles import integrity_style


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
            "event_dt",
            "factor_type",
            "factor",
            "reference_price",
            "reference_date",
            "dividend_amount",
            "status",
            "reason",
        ]
        if c in df_checked.columns
    ]

    st.dataframe(
        df_checked[show_cols]
        .style.applymap(integrity_style, subset=["status"]),
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
