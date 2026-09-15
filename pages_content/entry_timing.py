"""
pages_content/entry_timing.py
-------------------------
หน้า "Entry Timing" ของ CIS Dashboard

วิธีทดสอบหน้านี้แบบเดี่ยว (ไม่ต้องรอทีมคนอื่น):
    streamlit run preview_my_page.py
    (แล้วเลือกโมดูลนี้จาก dropdown ในไฟล์ preview_my_page.py)

ข้อมูลที่ใช้ได้ใน ctx (ดูนิยามเต็มใน common.py -> class PageContext):
    ctx.selected_ticker, ctx.stock_info, ctx.stock_daily, ctx.fin_stock, ctx.sector_peers,
    ctx.scores_df, ctx.fin_df, ctx.feat_imp_df, ctx.backtest_df, ctx.risk_hist_df,
    ctx.health_yearly_df, ctx.fair_value_yearly_df,
    ctx.current_price, ctx.change_pct, ctx.change_val, ctx.change_color, ctx.change_sign, ctx.arrow_sign

ห้ามแก้ CSS ส่วนกลางหรือ helper function ใน common.py จากไฟล์นี้ — ถ้าจำเป็นต้องแก้ ให้แจ้ง Layout Lead ก่อน
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from common import fmt_mb, fmt_ratio, safe, show_chart, render_nav_footer, COMPANY_NAMES, SECTOR_MAP


def render(ctx):
    st.markdown("""<div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:15px;">
    <div><div style="display:flex; align-items:center; gap:8px;"><h2 style="margin:0; font-size:23px; font-weight:bold; color:#F8FAFC; letter-spacing:0.5px;">ENTRY TIMING ANALYSIS</h2></div>
    <div style="font-size:15px; color:#94A3B8; margin-top:2px;">วิเคราะห์จังหวะเข้าลงทุนด้วย Technical Indicators จริงจากราคาปิดรายวัน</div></div>
    </div>""", unsafe_allow_html=True)

    timing_score = safe(ctx.stock_info.get('timing_score'), 50)
    trend_signal = ctx.stock_info.get('trend_signal', 'NEUTRAL')
    sig_color = "#10B981" if trend_signal == "BULLISH" else ("#EF4444" if trend_signal == "BEARISH" else "#F59E0B")
    sig_icon = "🐂" if trend_signal == "BULLISH" else ("🐻" if trend_signal == "BEARISH" else "⚖️")
    suggested_action = "Wait for Pullback" if trend_signal == "BULLISH" else ("Avoid / Wait for Reversal" if trend_signal == "BEARISH" else "Watch & Wait")

    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns([1.1, 2.5, 0.9, 0.95])

    with r1_c1:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:495px; display:flex; flex-direction:column; justify-content:space-between; text-align:center;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; text-align:left;">OVERALL ENTRY SIGNAL</div>
    <div style="margin:auto 0;">
    <div style="margin:0 auto; width:150px;"><svg viewBox="0 0 100 58" style="width:140px; height:89px; display:block; margin:0 auto;">
    <path d="M 12 50 A 38 38 0 0 1 88 50" fill="none" stroke="#1E293B" stroke-width="10" stroke-linecap="round" />
    <path d="M 12 50 A 38 38 0 0 1 88 50" fill="none" stroke="{sig_color}" stroke-width="10" stroke-linecap="round" stroke-dasharray="{round(119.38*min(1,timing_score/100),2)} 119.38" />
    <text x="50" y="44" text-anchor="middle" font-size="25" fill="{sig_color}">{sig_icon}</text></svg></div>
    <div style="font-size:19px; font-weight:bold; color:{sig_color}; margin-top:4px;">{trend_signal}</div>
    <div style="font-size:14px; color:#CBD5E1;">Score {timing_score:.0f}/100</div></div>
    <div style="background-color:#151E2F; border:1px solid #1E293B; border-radius:8px; padding:10px 12px; margin-bottom:10px;">
    <div style="font-size:12.5px; color:{sig_color}; font-weight:bold;">SUGGESTED ACTION</div>
    <div style="font-size:16.5px; font-weight:bold; color:#FFFFFF; margin-top:2px;">{suggested_action}</div></div>
    <div><div style="display:flex; justify-content:space-between; font-size:13px; color:#94A3B8; margin-bottom:4px;"><span>SIGNAL STRENGTH</span><span style="font-weight:bold; color:#CBD5E1;">{'High' if timing_score>=65 or timing_score<35 else 'Medium'}</span></div>
    <div style="display:flex; align-items:center; gap:8px;"><span style="font-size:15px; font-weight:bold; color:#FFFFFF;">{timing_score:.0f}<span style="font-size:12.5px; color:#64748B;">/100</span></span>
    <div style="background:#1E293B; height:10px; flex-grow:1; border-radius:5px; overflow:hidden;"><div style="background:{sig_color}; width:{timing_score:.0f}%; height:100%;"></div></div></div></div>
    </div>""", unsafe_allow_html=True)

    with r1_c2:
        st.markdown("""
        <style>
        section.main div[data-testid="stRadio"] > div { display: flex; justify-content: flex-end; gap: 4px; flex-wrap: nowrap; background: transparent; margin-bottom: 2px; }
        section.main div[data-testid="stRadio"] label { background-color: #151E2F !important; border: 1px solid #1E293B !important; border-radius: 6px !important; padding: 4px 10px !important; margin: 0 !important; cursor: pointer !important; }
        section.main div[data-testid="stRadio"] label > div:first-child { display: none !important; }
        section.main div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p { font-size: 10px !important; color: #94A3B8 !important; font-weight: 600 !important; margin: 0 !important; }
        section.main div[data-testid="stRadio"] label:has(input:checked) { background-color: #2563EB !important; border-color: #2563EB !important; }
        section.main div[data-testid="stRadio"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #FFFFFF !important; font-weight: bold !important; }
        </style>
        """, unsafe_allow_html=True)

        head_c1, head_c2 = st.columns([1, 2.2])
        with head_c1:
            st.markdown("""<div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; padding-top:4px;">PRICE CHART (Actual OHLC)</div>""", unsafe_allow_html=True)
        with head_c2:
            tf_selected = st.radio("Timeframe", ["1M", "3M", "6M", "1Y", "2Y", "ALL"], index=2, horizontal=True, label_visibility="collapsed", key="timing_timeframe_selector")

        tf_bars = {"1M": 22, "3M": 66, "6M": 132, "1Y": 252, "2Y": 504, "ALL": len(ctx.stock_daily)}
        n_bars = min(tf_bars.get(tf_selected, 132), len(ctx.stock_daily))
        chart_df = ctx.stock_daily.tail(n_bars).copy()
        chart_df['SMA100'] = ctx.stock_daily['close'].rolling(100, min_periods=1).mean().tail(n_bars).values

        fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.78, 0.22])
        fig_main.add_trace(go.Candlestick(
            x=chart_df['date'], open=chart_df['open'], high=chart_df['high'], low=chart_df['low'], close=chart_df['close'],
            name='Price', increasing_line_color='#10B981', increasing_fillcolor='#10B981',
            decreasing_line_color='#EF4444', decreasing_fillcolor='#EF4444', whiskerwidth=0.7, line=dict(width=1.2)
        ), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=chart_df['date'], y=chart_df['EMA20'], line=dict(color='#F59E0B', width=1.4), name='EMA 20'), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=chart_df['date'], y=chart_df['EMA50'], line=dict(color='#38BDF8', width=1.4), name='EMA 50'), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=chart_df['date'], y=chart_df['SMA100'], line=dict(color='#A855F7', width=1.4), name='SMA 100'), row=1, col=1)

        bar_colors = ['#10B981' if c >= o else '#EF4444' for c, o in zip(chart_df['close'], chart_df['open'])]
        vol_col = chart_df['volume'] if 'volume' in chart_df.columns else pd.Series([0] * len(chart_df))
        fig_main.add_trace(go.Bar(x=chart_df['date'], y=vol_col, marker_color=bar_colors, name='Volume', showlegend=False), row=2, col=1)

        fig_main.add_annotation(xref="paper", yref="y1", x=1.0, y=ctx.current_price, text=f"<b>{ctx.current_price:.2f}</b>", showarrow=True,
                                 arrowhead=0, arrowwidth=1.5, arrowcolor=ctx.change_color, ax=44, ay=0, font=dict(size=12.5, color="#FFFFFF"),
                                 bgcolor=ctx.change_color, bordercolor=ctx.change_color, borderwidth=1, borderpad=3)

        fig_main.update_layout(
            height=395, margin=dict(l=10, r=52, t=8, b=8), paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
            xaxis=dict(gridcolor="#1E293B", showticklabels=False, zeroline=False),
            xaxis2=dict(gridcolor="#1E293B", tickfont=dict(size=11.5, color="#64748B"), nticks=7, zeroline=False),
            yaxis=dict(gridcolor="#1E293B", tickfont=dict(size=11.5, color="#64748B"), side='right', zeroline=False),
            yaxis2=dict(gridcolor="#1E293B", showticklabels=False, zeroline=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0.01, font=dict(size=12, color="#CBD5E1")),
            xaxis_rangeslider_visible=False
        )
        show_chart(fig_main, key="entry_timing_candles", expand_height=750)

    with r1_c3:
        r1_val = safe(ctx.stock_info.get('resistance_60d'), ctx.current_price * 1.05)
        s1_val = safe(ctx.stock_info.get('support_60d'), ctx.current_price * 0.95)
        w20 = ctx.stock_daily.tail(20)
        w120 = ctx.stock_daily.tail(120)
        r2_val = round(float(w20['high'].max()), 2) if not w20.empty else r1_val
        r3_val = round(float(w120['high'].max()), 2) if not w120.empty else r1_val * 1.02
        s2_val = round(float(w20['low'].min()), 2) if not w20.empty else s1_val
        s3_val = round(float(w120['low'].min()), 2) if not w120.empty else s1_val * 0.98

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:495px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">KEY LEVELS (Actual, from price history)</div>
    <div><div style="font-size:12.5px; font-weight:bold; color:#EF4444; margin-bottom:6px;">RESISTANCE</div>
    <div style="display:flex; justify-content:space-between; font-size:13.5px; color:#CBD5E1; padding:4px 0; border-bottom:1px dashed #1E293B;"><span style="color:#64748B;">R3 (120d high)</span><b style="color:#F8FAFC;">{r3_val:.2f}</b></div>
    <div style="display:flex; justify-content:space-between; font-size:13.5px; color:#CBD5E1; padding:4px 0; border-bottom:1px dashed #1E293B;"><span style="color:#64748B;">R2 (20d high)</span><b style="color:#F8FAFC;">{r2_val:.2f}</b></div>
    <div style="display:flex; justify-content:space-between; font-size:13.5px; color:#CBD5E1; padding:4px 0;"><span style="color:#64748B;">R1 (60d high)</span><b style="color:#F8FAFC;">{r1_val:.2f}</b></div></div>
    <div style="border:1px dashed #3B82F6; padding:10px 0; text-align:center; background:rgba(59,130,246,0.08); border-radius:8px; margin:auto 0;">
    <div style="font-size:12.5px; color:#93C5FD; font-weight:bold;">CURRENT PRICE</div><div style="font-size:18.5px; font-weight:bold; color:#38BDF8; margin-top:2px;">{ctx.current_price:.2f}</div></div>
    <div><div style="font-size:12.5px; font-weight:bold; color:#10B981; margin-bottom:6px;">SUPPORT</div>
    <div style="display:flex; justify-content:space-between; font-size:13.5px; color:#CBD5E1; padding:4px 0; border-bottom:1px dashed #1E293B;"><span style="color:#64748B;">S1 (60d low)</span><b style="color:#F8FAFC;">{s1_val:.2f}</b></div>
    <div style="display:flex; justify-content:space-between; font-size:13.5px; color:#CBD5E1; padding:4px 0; border-bottom:1px dashed #1E293B;"><span style="color:#64748B;">S2 (20d low)</span><b style="color:#F8FAFC;">{s2_val:.2f}</b></div>
    <div style="display:flex; justify-content:space-between; font-size:13.5px; color:#CBD5E1; padding:4px 0;"><span style="color:#64748B;">S3 (120d low)</span><b style="color:#F8FAFC;">{s3_val:.2f}</b></div></div>
    </div>""", unsafe_allow_html=True)

    with r1_c4:
        buy_zone_lo, buy_zone_hi = s1_val, round((s1_val + ctx.current_price) / 2, 2)
        stop_loss = s3_val
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:495px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">RECOMMENDED ZONE</div>
    <div><div style="font-size:13px; color:#94A3B8;">Ideal Buy Zone</div>
    <div style="font-size:17.5px; font-weight:bold; color:#10B981; margin-top:2px;">{buy_zone_lo:.2f} - {buy_zone_hi:.2f}</div>
    <div style="font-size:12.5px; color:#64748B;">อ้างอิงจากแนวรับ 60 วันย้อนหลัง</div></div>
    <div style="background:rgba(239,68,68,0.08); border-left:3px solid #EF4444; padding:8px 10px; border-radius:4px; margin-top:auto;">
    <div style="font-size:12.5px; color:#EF4444; font-weight:bold;">STOP LOSS</div>
    <div style="font-size:16px; font-weight:bold; color:#EF4444; margin-top:2px;">&lt; {stop_loss:.2f}</div>
    <div style="font-size:12px; color:#94A3B8; margin-top:2px;">ตัดขาดทุนหากหลุดแนวรับ 120 วัน</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)

    last30 = ctx.stock_daily.tail(30)
    rsi_now = safe(ctx.stock_info.get('rsi'), 50)
    macd_now = safe(ctx.stock_info.get('macd'), 0)
    adx_now = safe(ctx.stock_info.get('adx'), 20)

    def sparkline_svg(series, color, height=50):
        vals = series.dropna().tolist()
        if len(vals) < 2:
            return ""
        lo, hi = min(vals), max(vals)
        rng = (hi - lo) or 1
        w = 160
        pts = []
        for i, v in enumerate(vals):
            x = 5 + (w - 10) * i / (len(vals) - 1)
            y = 48 - ((v - lo) / rng) * 40
            pts.append(f"{x:.1f} {y:.1f}")
        path = "M " + " L ".join(pts)
        return f'<svg viewBox="0 0 {w} {height}" style="width:100%; height:{height}px; display:block;"><path d="{path}" fill="none" stroke="{color}" stroke-width="2"/></svg>'

    with r2_c1:
        macd_status = "BULLISH" if macd_now > 0 else "BEARISH"
        macd_color = "#10B981" if macd_now > 0 else "#EF4444"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:14.5px; font-weight:bold; color:#CBD5E1;">MACD</span><span style="color:{macd_color}; font-size:13.5px; font-weight:bold;">{macd_status}</span></div>
    <div style="font-size:23px; font-weight:bold; color:#FFFFFF; margin-top:4px;">{macd_now:.3f}</div></div>
    <div style="margin-top:auto;">{sparkline_svg(last30['MACD'], macd_color)}</div></div>""", unsafe_allow_html=True)

    with r2_c2:
        rsi_status = "OVERBOUGHT" if rsi_now >= 70 else ("OVERSOLD" if rsi_now <= 30 else "NEUTRAL")
        rsi_color = "#EF4444" if rsi_now >= 70 else ("#10B981" if rsi_now <= 30 else "#F59E0B")
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:14.5px; font-weight:bold; color:#CBD5E1;">RSI (14)</span><span style="color:{rsi_color}; font-size:13.5px; font-weight:bold;">{rsi_status}</span></div>
    <div style="font-size:26px; font-weight:bold; color:#FFFFFF; margin-top:4px;">{rsi_now:.1f}</div></div>
    <div style="margin-top:auto;">{sparkline_svg(last30['RSI14'], '#A855F7')}</div></div>""", unsafe_allow_html=True)

    with r2_c3:
        adx_status = "STRONG TREND" if adx_now >= 25 else "WEAK / RANGE"
        adx_color = "#10B981" if adx_now >= 25 else "#94A3B8"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:14.5px; font-weight:bold; color:#CBD5E1;">ADX (14)</span><span style="color:{adx_color}; font-size:13.5px; font-weight:bold;">{adx_status}</span></div>
    <div style="font-size:26px; font-weight:bold; color:#FFFFFF; margin-top:4px;">{adx_now:.1f}</div></div>
    <div style="margin-top:auto;">{sparkline_svg(last30['ADX'], '#F8FAFC')}</div></div>""", unsafe_allow_html=True)

    with r2_c4:
        ema_status = "GOLDEN (Bullish)" if ctx.stock_info.get('ema20', 0) > ctx.stock_info.get('ema50', 0) else "DEATH (Bearish)"
        ema_color = "#10B981" if ctx.stock_info.get('ema20', 0) > ctx.stock_info.get('ema50', 0) else "#EF4444"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:14.5px; font-weight:bold; color:#CBD5E1;">EMA20 / EMA50</span><span style="color:{ema_color}; font-size:13.5px; font-weight:bold;">{ema_status}</span></div>
    <div style="font-size:16.5px; font-weight:bold; color:#F59E0B; margin-top:4px;">{safe(ctx.stock_info.get('ema20')):.2f} <span style="color:#64748B; font-size:13.5px;">/</span> <span style="color:#38BDF8;">{safe(ctx.stock_info.get('ema50')):.2f}</span></div></div>
    <div style="margin-top:auto;">{sparkline_svg(last30['EMA20'], '#F59E0B')}</div></div>""", unsafe_allow_html=True)

    with r2_c5:
        vol_now = safe(last30.iloc[-1]['volume']) if not last30.empty else 0
        vol_avg = safe(last30.iloc[-1]['Volume Avg']) if not last30.empty and 'Volume Avg' in last30.columns else vol_now
        vol_diff = ((vol_now - vol_avg) / vol_avg * 100) if vol_avg else 0
        vol_status = "Increasing" if vol_diff > 0 else "Decreasing"
        vol_color = "#10B981" if vol_diff > 0 else "#EF4444"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="font-size:14.5px; font-weight:bold; color:#CBD5E1;">VOLUME (vs 20D avg)</div>
    <div style="font-size:16.5px; font-weight:bold; color:{vol_color}; margin-top:4px;">{vol_status}</div><div style="font-size:13px; color:#94A3B8;">{vol_diff:+.1f}% vs Avg.</div></div>
    <div style="margin-top:auto;">{sparkline_svg(last30['volume'], vol_color)}</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    r3_c1, r3_c2, r3_c3, r3_c4 = st.columns([1.1, 1.25, 1.4, 1.55])

    short_bull = ctx.current_price > safe(ctx.stock_info.get('ema20'))
    med_bull = safe(ctx.stock_info.get('ema20')) > safe(ctx.stock_info.get('ema50'))
    long_ref = ctx.stock_daily.iloc[max(0, len(ctx.stock_daily) - 252)]['close'] if len(ctx.stock_daily) > 0 else ctx.current_price
    long_bull = ctx.current_price > long_ref

    def trend_row(label, sub, is_bull):
        c = "#10B981" if is_bull else "#EF4444"
        txt = "Bullish ↗" if is_bull else "Bearish ↘"
        return f"""<div style="background:#151E2F; border:1px solid #1E293B; border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center;">
    <span style="font-size:14px; color:#CBD5E1;">{label} <span style="font-size:12.5px; color:#64748B;">({sub})</span></span>
    <span style="background:rgba(16,185,129,0.15); color:{c}; font-size:14px; font-weight:bold; padding:3px 10px; border-radius:12px;">{txt}</span></div>"""

    with r3_c1:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:295px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">TREND ANALYSIS</div>
    <div style="display:flex; flex-direction:column; gap:10px; margin:auto 0;">
    {trend_row("Short Term", "Price vs EMA20", short_bull)}
    {trend_row("Medium Term", "EMA20 vs EMA50", med_bull)}
    {trend_row("Long Term", "vs ~1Y ago", long_bull)}
    </div></div>""", unsafe_allow_html=True)

    with r3_c2:
        summary_items = []
        summary_items.append((short_bull, "ราคาปัจจุบันอยู่เหนือ EMA20" if short_bull else "ราคาปัจจุบันอยู่ต่ำกว่า EMA20"))
        summary_items.append((med_bull, "EMA20 อยู่เหนือ EMA50 (แนวโน้มขาขึ้นระยะกลาง)" if med_bull else "EMA20 อยู่ต่ำกว่า EMA50 (แนวโน้มขาลงระยะกลาง)"))
        summary_items.append((macd_now > 0, "MACD เป็นบวก ส่งสัญญาณโมเมนตัมขาขึ้น" if macd_now > 0 else "MACD เป็นลบ ส่งสัญญาณโมเมนตัมขาลง"))
        summary_items.append((adx_now >= 25, f"ADX ที่ {adx_now:.1f} ยืนยันแนวโน้มแข็งแรง" if adx_now >= 25 else f"ADX ที่ {adx_now:.1f} บ่งชี้ตลาด sideway"))
        sig_html = "".join([f'<div style="display:flex; gap:8px;"><span style="color:{"#10B981" if ok else "#EF4444"}; font-size:15px;">{"✔" if ok else "✖"}</span><span>{txt}</span></div>' for ok, txt in summary_items])
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:295px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">SIGNAL SUMMARY</div>
    <div style="font-size:14px; color:#CBD5E1; line-height:1.6; display:flex; flex-direction:column; gap:6px; margin:auto 0;">{sig_html}</div>
    </div>""", unsafe_allow_html=True)

    with r3_c3:
        # หา EMA20/EMA50 crossover จริงในช่วง 120 วันล่าสุด
        hist120 = ctx.stock_daily.tail(120).copy().reset_index(drop=True)
        hist120['diff'] = hist120['EMA20'] - hist120['EMA50']
        hist120['cross'] = np.sign(hist120['diff']).diff().fillna(0)
        events = hist120[hist120['cross'] != 0].tail(5)
        rows_html = ""
        for _, ev in events.iloc[::-1].iterrows():
            label = "Golden Cross" if ev['cross'] > 0 else "Death Cross"
            lc = "#10B981" if ev['cross'] > 0 else "#EF4444"
            rows_html += f"""<tr style="border-bottom:1px solid #1E293B;"><td style="padding:4px 0; color:#94A3B8;">{ev['date'].strftime('%d %b %Y')}</td>
    <td><span style="color:{lc}; font-weight:bold;">{label}</span></td><td>{ev['close']:.2f}</td><td style="color:#64748B;">EMA Crossover</td></tr>"""
        if not rows_html:
            rows_html = '<tr><td colspan="4" style="padding:8px 0; color:#64748B; text-align:center;">ไม่พบสัญญาณ Cross ในช่วง 120 วันล่าสุด</td></tr>'
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:295px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">RECENT SIGNAL HISTORY (EMA Crossovers, actual)</div>
    <table style="width:100%; text-align:left; font-size:13.5px; color:#CBD5E1; border-collapse:collapse; margin:auto 0;">
    <tr style="border-bottom:1px solid #1E293B; color:#64748B; font-size:12.5px;"><th style="padding:4px 0;">Date</th><th>Signal</th><th>Price</th><th>Type</th></tr>
    {rows_html}
    </table></div>""", unsafe_allow_html=True)

    with r3_c4:
        risk_lvl = "HIGH" if adx_now < 15 else ("MEDIUM" if adx_now < 25 else "LOW")
        risk_lvl_color = {"LOW": "#10B981", "MEDIUM": "#F59E0B", "HIGH": "#EF4444"}[risk_lvl]
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:295px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; margin-bottom:6px;">TECHNICAL NOTES</div>
    <p style="font-size:13px; color:#CBD5E1; line-height:1.55; margin:0;">
    สัญญาณรวมล่าสุดของ {ctx.selected_ticker} คือ <b>{trend_signal}</b> (Timing Score {timing_score:.0f}/100) แนวรับใกล้สุดอยู่ที่ {s1_val:.2f} บาท และแนวต้านอยู่ที่ {r1_val:.2f} บาท หากราคาหลุด {s3_val:.2f} ควรพิจารณาตัดขาดทุน
    </p></div>
    <div style="display:flex; justify-content:space-between; align-items:flex-end; border-top:1px solid #1E293B; padding-top:10px;">
    <div><div style="font-size:12.5px; color:#94A3B8; font-weight:bold; margin-bottom:4px;">RISK LEVEL (จาก ADX)</div>
    <div style="font-size:16px; font-weight:bold; color:{risk_lvl_color};">{risk_lvl}</div></div>
    <div style="text-align:right;"><div style="font-size:12.5px; color:#94A3B8; font-weight:bold;">MACD SIGNAL</div>
    <div style="font-size:15px; font-weight:bold; color:{macd_color}; margin-top:2px;">{macd_status}</div></div>
    </div></div>""", unsafe_allow_html=True)

    render_nav_footer("m3", prev_page=" ⚖️ Fair Value", next_page=" 🔮 AI Prediction")

