from datetime import datetime, timedelta

def get_prev_business_day(trd_dt: str) -> str:
    dt = datetime.strptime(trd_dt, "%Y-%m-%d")
    if dt.weekday() == 0:
        dt -= timedelta(days=3)
    else:
        dt -= timedelta(days=1)
    return dt.strftime("%Y-%m-%d")
