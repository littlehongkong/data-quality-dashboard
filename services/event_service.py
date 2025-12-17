# services/event_service.py

import io
import pandas as pd
import pyarrow.parquet as pq

from clients.s3_client import get_s3_client
from config.settings import ENV, DOMAIN_GROUP, WAREHOUSE_BUCKET

def _event_log_key(domain: str, country_code: str) -> str:
    return (
        f"env={ENV}/stage=event_logs/domain_group={DOMAIN_GROUP}/"
        f"domain={domain}/country_code={country_code}/event_log.parquet"
    )


def load_event_log_parquet(domain: str, country_code: str) -> pd.DataFrame:
    """
    event_logs 의 append parquet 단일 파일 로드
    """
    s3 = get_s3_client()
    key = _event_log_key(domain, country_code)

    obj = s3.get_object(Bucket=WAREHOUSE_BUCKET, Key=key)
    buf = io.BytesIO(obj["Body"].read())

    table = pq.read_table(buf)
    df = table.to_pandas()

    # 안전장치: 문자열 컬럼 정리
    for c in ["country_code", "exchange_code", "old_security_id", "new_security_id"]:
        if c in df.columns:
            df[c] = df[c].astype(str)

    return df


def filter_symbol_change_by_trd_dt(df: pd.DataFrame, trd_dt: str) -> pd.DataFrame:
    """
    event_log.parquet 내부 컬럼 기준으로 날짜 필터
    - event_dt 또는 trd_dt 어느 쪽이든 대응
    """

    if "effective" in df.columns:
        filtered = df[df["effective"].dt.date == pd.to_datetime(trd_dt).date()]
        return filtered


def validate_symbol_change_integrity(df_evt: pd.DataFrame, df_asset_master: pd.DataFrame) -> pd.DataFrame:
    """
    old_security_id / new_security_id 가 asset_master 기준으로 존재하는지
    integrity_status 계산
    """
    asset_ids = set(df_asset_master["security_id"].astype(str).unique())

    def _status(row):
        old_id = str(row.get("old_security_id"))
        new_id = str(row.get("new_security_id"))

        if old_id == new_id:
            return "meaningless", "old_security_id == new_security_id"
        if old_id not in asset_ids:
            return "invalid", "old_security_id not found in asset_master"
        if new_id not in asset_ids:
            return "partial", "new_security_id not found in asset_master"
        return "valid", "OK"

    out = df_evt.copy()
    statuses = out.apply(_status, axis=1, result_type="expand")
    out["integrity_status"] = statuses[0]
    out["integrity_reason"] = statuses[1]
    return out
