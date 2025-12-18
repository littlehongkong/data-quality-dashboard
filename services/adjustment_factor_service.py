import pandas as pd
from services.athena_service import query_athena
from config.settings import WAREHOUSE_BUCKET
from datetime import datetime, timedelta


def load_adjustment_factor_master_parquet(
        trd_dt: str,
        country_code: str,
) -> pd.DataFrame:
    """
    s3://.../adjustment_factor_master.parquet 직접 로드
    """
    s3_path = (
        f"s3://{WAREHOUSE_BUCKET}/"
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


def compute_adjusted_prices_backadjust(
        df_price: pd.DataFrame,
        df_factor: pd.DataFrame,
        price_date_col: str = "trd_dt",
        factor_date_col: str = "event_dt",
        factor_col: str = "factor",
) -> pd.DataFrame:
    """
    수정주가 계산: adj(d) = close(d) * Π factor(event_dt > d)

    규칙:
    - 이벤트 당일(event_dt == trd_dt): factor 미적용
    - 이벤트 이후(trd_dt > event_dt): factor 미적용
    - 이벤트 이전(trd_dt < event_dt): 미래 이벤트 factor 적용
    """

    if df_price is None or df_price.empty:
        return pd.DataFrame()

    if df_factor is None or df_factor.empty:
        df_price = df_price.copy()
        df_price["cumulative_factor"] = 1.0
        df_price["adjusted_price"] = df_price["close"]
        return df_price

    df_price = df_price.copy()
    df_factor = df_factor.copy()

    df_price[price_date_col] = pd.to_datetime(df_price[price_date_col]).dt.normalize()
    df_factor[factor_date_col] = pd.to_datetime(df_factor[factor_date_col]).dt.normalize()

    out = []

    for sid, p in df_price.groupby("security_id", sort=False):
        p = p.sort_values(price_date_col).copy()

        f = df_factor[df_factor["security_id"] == sid].copy()
        if f.empty:
            p["cumulative_factor"] = 1.0
            p["adjusted_price"] = p["close"]
            out.append(p)
            continue

        f = f.sort_values(factor_date_col)

        # 🔥 미래→과거 누적곱 계산
        f["future_cumprod"] = f[factor_col].iloc[::-1].cumprod().iloc[::-1]

        # 🔥 forward merge: 각 거래일에 대해 "가장 가까운 미래 이벤트"를 찾음
        p2 = pd.merge_asof(
            p,
            f[[factor_date_col, "future_cumprod"]],
            left_on=price_date_col,
            right_on=factor_date_col,
            direction="forward",
            allow_exact_matches=False,
        )

        # 매칭 안된 경우 = 1.0
        p2["cumulative_factor"] = p2["future_cumprod"].fillna(1.0)

        # 🔥 추가 검증: 이벤트 당일은 강제로 1.0 설정
        if not f.empty:
            event_dates = set(f[factor_date_col])
            is_event_day = p2[price_date_col].isin(event_dates)
            p2.loc[is_event_day, "cumulative_factor"] = 1.0

        p2["adjusted_price"] = p2["close"] * p2["cumulative_factor"]

        p2 = p2.drop(columns=["future_cumprod", factor_date_col], errors="ignore")
        out.append(p2)

    return pd.concat(out, ignore_index=True)


def get_last_n_business_days(end_dt: str, n: int = 20) -> tuple[str, str]:
    """
    end_dt 기준으로 주말 제외 최근 n거래일 범위 계산
    return: (start_dt, end_dt)
    """
    end = datetime.strptime(end_dt, "%Y-%m-%d").date()
    days = []
    cur = end

    while len(days) < n:
        if cur.weekday() < 5:  # 0~4 = Mon~Fri
            days.append(cur)
        cur -= timedelta(days=1)

    start = days[-1]
    return start.isoformat(), end.isoformat()


def load_recent_adj_prices_from_athena(
        security_ids: list[str],
        country_code: str,
        end_dt: str,
        window: int = 20,
) -> pd.DataFrame:
    """
    Athena에서 최근 N일 adj_close 조회
    """

    if not security_ids:
        return pd.DataFrame()

    sid_list = ", ".join(f"'{sid}'" for sid in security_ids)
    start_dt, end_dt = get_last_n_business_days(end_dt=end_dt, n=20)

    sql = f"""
    SELECT
        security_id,
        ticker,
        trd_dt,
        close
    FROM domain_price_master
    WHERE country_code = '{country_code}'
      AND security_id IN ({sid_list})
      AND trd_dt <= '{end_dt}'
      AND trd_dt >= '{start_dt}'
    ORDER BY security_id, trd_dt;

    """

    return query_athena(sql)


def build_adj_price_sparkline(
        df_adjusted: pd.DataFrame,
        window: int = 20,
) -> dict[str, list[float]]:
    """
    security_id → 최근 N일 adjusted_price list
    """

    df_adjusted = df_adjusted.sort_values(["security_id", "trd_dt"])

    return (
        df_adjusted
        .groupby("security_id")["adjusted_price"]
        .apply(lambda x: x.tail(window).tolist())
        .to_dict()
    )


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