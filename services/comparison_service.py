import pandas as pd

def build_layer_dod_compare(
    df_today: pd.DataFrame,
    df_prev: pd.DataFrame,
    layer: str,
) -> pd.DataFrame:
    """
    layer: 'lake' or 'warehouse'
    """

    today = (
        df_today
        .groupby(["logical", "domain"], as_index=False)
        .agg(today_records=("record_count", "sum"))
    )

    prev = (
        df_prev
        .groupby(["logical", "domain"], as_index=False)
        .agg(prev_records=("record_count", "sum"))
    )

    df = pd.merge(
        today,
        prev,
        on=["logical", "domain"],
        how="left",
    )

    df["prev_records"] = df["prev_records"].fillna(0).astype(int)
    df["diff"] = df["today_records"] - df["prev_records"]

    df["diff_pct"] = df.apply(
        lambda r: None if r["prev_records"] == 0
        else round((r["diff"] / r["prev_records"]) * 100, 2),
        axis=1,
    )

    df["layer"] = layer

    return df.sort_values(["logical", "domain"])