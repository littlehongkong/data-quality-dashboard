# services/asset_service.py

import io
import pandas as pd
import pyarrow.parquet as pq

from clients.s3_client import get_s3_client
from config.settings import ENV, DOMAIN_GROUP, WAREHOUSE_BUCKET


def load_asset_master_snapshot(trd_dt: str, country_code: str) -> pd.DataFrame:
    s3 = get_s3_client()

    key = (
        f"env={ENV}/stage=snapshot/domain_group={DOMAIN_GROUP}/"
        f"domain=asset_master/country_code={country_code}/"
        f"trd_dt={trd_dt}/asset_master.parquet"
    )

    obj = s3.get_object(Bucket=WAREHOUSE_BUCKET, Key=key)
    buf = io.BytesIO(obj["Body"].read())
    return pq.read_table(buf).to_pandas()
