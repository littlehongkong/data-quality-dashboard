import pandas as pd

# =========================================================
# 🎨 STYLE
# =========================================================
def status_style(val):
    if val == "success":
        return "background-color:#14532d;color:white;"
    if val == "partial":
        return "background-color:#92400e;color:white;"
    if val == "skipped":
        return "background-color:#374151;color:white;"
    if val in ("failed", "error", "missing"):
        return "background-color:#7f1d1d;color:white;"
    return ""


def mc_status_style(val):
    if val == "success":
        return "background-color:#14532d;color:white;"
    if val == "skipped":
        return "background-color:#374151;color:white;"
    if val in ("failed", "missing"):
        return "background-color:#7f1d1d;color:white;"
    return ""

def diff_style(val):
    if pd.isna(val):
        return "color:#9ca3af;"
    if val == 0:
        return "color:#16a34a;font-weight:bold;"   # 완전 일치
    if val < 0:
        return "color:#dc2626;font-weight:bold;"   # warehouse 누락
    return "color:#92400e;font-weight:bold;"       # warehouse 초과


# -------------------------------------------------
# ✅ Event integrity 전용 스타일 (symbol_change)
# -------------------------------------------------
def integrity_style(val):
    """
    integrity_status 컬럼 전용
    """
    if val == "valid":
        return "background-color:#14532d;color:white;"
    if val == "partial":
        return "background-color:#92400e;color:white;"
    if val == "invalid":
        return "background-color:#7f1d1d;color:white;"
    if val == "meaningless":
        return "background-color:#374151;color:#e5e7eb;"
    return ""