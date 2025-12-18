# services/coverage_service.py

import pandas as pd
from services.athena_service import query_athena


ASSET_TABLE = "domain_asset_master"
PRICE_TABLE = "domain_price_master"


def find_asset_without_price(trd_dt: str) -> pd.DataFrame:
    """
    Asset Master에는 있으나
    Price Master에는 없는 종목 목록
    """

    sql = f"""
    SELECT
      a.security_id,
      a.ticker
    FROM {ASSET_TABLE} a
    LEFT JOIN {PRICE_TABLE} p
      ON upper(trim(a.security_id)) = upper(trim(p.security_id))
     AND p.trd_dt = '{trd_dt}'
    WHERE a.trd_dt = '{trd_dt}'
      AND p.security_id IS NULL
    ORDER BY a.ticker;

    """

    df = query_athena(sql)

    if df.empty:
        return df

    return df


def find_price_without_asset(trd_dt: str) -> pd.DataFrame:
    """
    Price Master에는 있으나
    Asset Master에는 없는 종목 목록
    """

    sql = f"""
        SELECT
          p.security_id,
          p.ticker,
          p.country_code
        FROM {PRICE_TABLE} p
        LEFT JOIN {ASSET_TABLE} a
          ON upper(trim(p.security_id)) = upper(trim(a.security_id))
         AND a.trd_dt = '{trd_dt}'          -- ✅ JOIN에서 날짜 고정
        WHERE p.trd_dt = '{trd_dt}'
          AND a.security_id IS NULL
        ORDER BY p.ticker;

    """

    df = query_athena(sql)

    if df.empty:
        return df

    # ---------------------------------------------
    # inferred_reason 자동 분류 (기본)
    # ---------------------------------------------
    df["inferred_reason"] = "asset_missing"

    return df
