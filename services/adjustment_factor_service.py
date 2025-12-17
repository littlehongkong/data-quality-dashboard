# services/adjustment_factor_service.py

import pandas as pd

DATA_WAREHOUSE_BUCKET = "sapiens-finance-data-warehouse"


def load_adjustment_factor_master_parquet(
    trd_dt: str,
    country_code: str,
) -> pd.DataFrame:
    """
    s3://.../adjustment_factor_master.parquet 직접 로드
    """
    s3_path = (
        f"s3://{DATA_WAREHOUSE_BUCKET}/"
        f"env=prod/stage=validated/"
        f"domain_group=equity/"
        f"domain=adjustment_factor_master/"
        f"country_code={country_code}/"
        f"trd_dt={trd_dt}/"
        f"adjustment_factor_master.parquet"
    )

    try:
        return pd.read_parquet(s3_path)
    except Exception as e:
        # Streamlit 쪽에서 empty 체크하도록
        return pd.DataFrame()


def validate_adjustment_factor_integrity(df: pd.DataFrame) -> pd.DataFrame:
    """
    adjustment_factor_master 정합성 검증

    status:
      - RESOLVED
      - UNRESOLVED
    """

    df = df.copy()

    # 컬럼 방어
    if "status" not in df.columns:
        df["status"] = None
    if "reason" not in df.columns:
        df["reason"] = None

    # 기본값
    df["status"] = "RESOLVED"

    # 1️⃣ adjustment_factor <= 0
    mask_invalid = df["factor"] <= 0
    df.loc[mask_invalid, "status"] = "UNRESOLVED"
    df.loc[mask_invalid, "reason"] = "INVALID_ADJUSTMENT_FACTOR"

    # 2️⃣ effective null
    mask_effective_null = df["event_dt"].isna()
    df.loc[mask_effective_null, "status"] = "UNRESOLVED"
    df.loc[mask_effective_null, "reason"] = "EFFECTIVE_DATE_MISSING"

    # 3️⃣ duplicate (security_id + effective)
    dup = (
        df.groupby(["security_id", "event_dt"])
        .size()
        .reset_index(name="cnt")
        .query("cnt > 1")
    )

    if not dup.empty:
        dup_idx = df.merge(
            dup[["security_id", "event_dt"]],
            on=["security_id", "event_dt"],
            how="inner",
        ).index

        df.loc[dup_idx, "status"] = "UNRESOLVED"
        df.loc[dup_idx, "reason"] = "DUPLICATE_EFFECTIVE_DATE"

    return df
