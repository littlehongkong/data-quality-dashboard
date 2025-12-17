# event_view.py
import streamlit as st

from views.symbol_change_view import render_symbol_change_view
from views.adjustment_factor_view import render_adjustment_factor_view

def render_event_view(trd_dt: str):
    st.header("📊 Data Integrity Monitor")

    tab_event, tab_price = st.tabs([
        "🧩 Event Integrity (Symbol Change)",
        "📊 Price Integrity (Adjustment Factor)"
    ])

    with tab_event:
        render_symbol_change_view(trd_dt=trd_dt)

    with tab_price:
        render_adjustment_factor_view(trd_dt=trd_dt)
