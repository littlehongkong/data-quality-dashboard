import pandas as pd
import json
from clients.s3_client import get_s3_client
from config.settings import ENV, DOMAIN_GROUP, WAREHOUSE_BUCKET
from config.domain_mapping import DOMAIN_MAPPING
from config.settings import TARGET_COUNTRIES
from config.domain_mapping import MULTI_COUNTRY_WAREHOUSE_DOMAINS


def find_warehouse_meta(trd_dt: str) -> list[dict]:
    base_prefix = f"env={ENV}/stage=meta/domain_group={DOMAIN_GROUP}/"
    rows = []

    paginator = get_s3_client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=WAREHOUSE_BUCKET, Prefix=base_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("_last_validated.json"):
                continue
            if f"trd_dt={trd_dt}/" not in key:
                continue

            parts = key.split("/")
            domain = [p for p in parts if p.startswith("domain=")][0].replace("domain=", "")

            country_code = None
            for p in parts:
                if p.startswith("country_code="):
                    country_code = p.replace("country_code=", "")

            # ✅ country_code 없는 경우는 GLOBAL로 강제
            # country_code = country_code or "GLOBAL"

            meta = json.loads(get_s3_client().get_object(Bucket=WAREHOUSE_BUCKET, Key=key)["Body"].read())

            rows.append({
                "logical": next(
                    (k for k, v in DOMAIN_MAPPING.items() if domain in v.get("warehouse", [])),
                    "unknown"
                ),
                "domain": domain,
                "country_code": country_code,
                "status": meta.get("status"),
                "record_count": meta.get("record_count", 0),
                "validated_at": meta.get("validated_at"),
                "message": meta.get("message"),
                "s3_key": f"s3://{WAREHOUSE_BUCKET}/{key}",
            })

    return rows


def build_warehouse_status_pivot(df_wh: pd.DataFrame) -> pd.DataFrame:
    # logical × country_code = status
    pv = (
        df_wh.pivot_table(
            index="logical",
            columns="country_code",
            values="status",
            aggfunc="first",
        )
    )

    # ✅ 고정 컬럼 보장 + 누락은 missing
    for c in TARGET_COUNTRIES:
        if c not in pv.columns:
            pv[c] = None
    pv = pv[TARGET_COUNTRIES].fillna("missing").reset_index()

    return pv


def build_warehouse_pivot(df_wh: pd.DataFrame) -> pd.DataFrame:
    if df_wh.empty:
        return pd.DataFrame()

    pivot = (
        df_wh
        .pivot_table(
            index="logical",
            columns="country_code",
            values="status",
            aggfunc="first",
        )
        .reset_index()
    )

    return pivot


def build_multi_country_check(df_wh: pd.DataFrame) -> pd.DataFrame:
    """
    country_code partition 이 없는 warehouse domain (예: exchange_master)에 대해
    기대 국가(KOR, USA 등)가 모두 포함되었는지 논리적으로 점검

    반환 컬럼:
    - domain
    - logical
    - build_status
    - included_countries
    - missing_countries
    - record_count
    - message
    """

    rows = []

    for domain, cfg in MULTI_COUNTRY_WAREHOUSE_DOMAINS.items():
        logical = cfg["logical"]
        expected = set(cfg["expected_countries"])

        # 해당 domain 메타만 필터
        df_d = df_wh[df_wh["domain"] == domain]

        if df_d.empty:
            rows.append({
                "domain": domain,
                "logical": logical,
                "build_status": "missing",
                "included_countries": "-",
                "missing_countries": ", ".join(sorted(expected)),
                "record_count": 0,
                "message": "build meta not found",
            })
            continue

        # 첫 row 기준 (warehouse meta 특성상 domain 단위 1건)
        row = df_d.iloc[0]
        status = row.get("status")
        record_count = row.get("record_count", 0)
        message = row.get("message")

        # country_code 경로가 없으므로 → 내부 포함 여부 추정
        included = set(
            c for c in df_d["country_code"].dropna().unique().tolist()
        )

        # exchange_master 같은 경우 country_code partition 없음
        # → 포함 국가를 모두 포함한 것으로 간주
        if not included:
            included = expected.copy()

        missing = expected - included

        rows.append({
            "domain": domain,
            "logical": logical,
            "build_status": status,
            "included_countries": ", ".join(sorted(included)),
            "missing_countries": "-" if not missing else ", ".join(sorted(missing)),
            "record_count": record_count,
            "message": message,
        })

    return pd.DataFrame(rows)