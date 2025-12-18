# services/athena_service.py

import boto3
import pandas as pd
import time
from config.settings import WAREHOUSE_BUCKET, AWS_REGION, ATHENA_OUTPUT



def query_athena(sql: str) -> pd.DataFrame:
    client = boto3.client("athena", region_name=AWS_REGION)

    response = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": WAREHOUSE_BUCKET},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
    )

    qid = response["QueryExecutionId"]

    while True:
        res = client.get_query_execution(QueryExecutionId=qid)
        status = res["QueryExecution"]["Status"]["State"]

        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)

    if status != "SUCCEEDED":
        reason = res["QueryExecution"]["Status"].get(
            "StateChangeReason", "UNKNOWN"
        )
        raise RuntimeError(
            f"Athena query failed: {status}\nReason: {reason}\nSQL:\n{sql}"
        )

    output = res["QueryExecution"]["ResultConfiguration"]["OutputLocation"]
    return pd.read_csv(output)

