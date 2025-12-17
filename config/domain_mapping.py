DOMAIN_MAPPING = {
    "exchange": {
        "lake": ["exchange_list"],
        "warehouse": ["exchange_master"]
    },
    "exchange_detail": {
        "lake": ["exchange_detail"]
    },
    "asset": {
        "lake": ["symbol_list"],
        "warehouse": ["asset_master"]
    },
    "price": {
        "lake": ["prices"],
        "warehouse": ["price_master"]
    },
    "fundamental": {
        "lake": ["fundamentals"],
        "warehouse": ["fundamental_master"]
    },
    "dividend": {
        "lake": ["dividends"],
        "warehouse": ["dividend_master"],
    },
    "split": {
        "lake": ["splits"],
        "warehouse": ["split_master"],
    },
    "symbol_change": {
        "lake": ["symbol_changes"],
        "warehouse": ["symbol_change_events"],
    },
    "adjust_factor":{
        "warehouse": "adjustment_factor_master"
    },
    "holiday": {
        "warehouse": "holiday_master"
    }
}

MULTI_COUNTRY_WAREHOUSE_DOMAINS = {
    "exchange_master": {
        "logical": "exchange",
        "expected_countries": ["KOR", "USA"],
        "country_field": "country_code",  # parquet/meta 내부 필드명
    },
    # 추후 확장 예시
    # "holiday_master": {
    #     "logical": "holiday",
    #     "expected_countries": ["KOR", "USA"],
    #     "country_field": "country_code",
    # },
}