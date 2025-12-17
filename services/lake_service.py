from clients.s3_client import get_s3_client
from config.settings import ENV, DOMAIN_GROUP, LAKE_BUCKET
from config.domain_mapping import DOMAIN_MAPPING
import pandas as pd
import json

def find_lake_meta(trd_dt: str) -> list[dict]:
    base_prefix = f"env={ENV}/stage=meta/domain_group={DOMAIN_GROUP}/"
    rows = []

    paginator = get_s3_client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=LAKE_BUCKET, Prefix=base_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("_last_validated.json"):
                continue
            if f"trd_dt={trd_dt}/" not in key:
                continue

            parts = key.split("/")
            domain = [p for p in parts if p.startswith("domain=")][0].replace("domain=", "")

            exchange_code = None
            for p in parts:
                if p.startswith("exchange_code="):
                    exchange_code = p.replace("exchange_code=", "")
            exchange_code = exchange_code or "ALL"

            meta = json.loads(
                get_s3_client().get_object(Bucket=LAKE_BUCKET, Key=key)["Body"].read()
            )

            rows.append({
                "logical": next(
                    (k for k, v in DOMAIN_MAPPING.items() if domain in v.get("lake", [])),
                    "unknown"
                ),
                "domain": domain,
                "exchange_code": exchange_code,
                "status": meta.get("status"),
                "record_count": meta.get("record_count", 0),
                "message": meta.get("message"),
                "s3_key": f"s3://{LAKE_BUCKET}/{key}",
            })

    return rows

def build_lake_summary(df: pd.DataFrame) -> pd.DataFrame:
    def final_status(statuses):
        statuses = set(statuses)
        if statuses.issubset({"success", "skipped"}):
            return "success"
        if "success" in statuses:
            return "partial"
        return "failed"

    return (
        df.groupby("logical")
        .agg(
            exchanges=("exchange_code", "nunique"),
            success=("status", lambda x: sum(s == "success" for s in x)),
            skipped=("status", lambda x: sum(s == "skipped" for s in x)),
            failed=("status", lambda x: sum(s in ["failed", "error", "missing"] for s in x)),
            total_records=("record_count", "sum"),
            status=("status", final_status),
        )
        .reset_index()
    )
