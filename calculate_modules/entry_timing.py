"""
calculate_modules/entry_timing.py
-------------------------------------
สูตรคำนวณโมดูล "Entry Timing" (⏱️) — คู่กับ pages_content/entry_timing.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key โดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

calculate_timing_module(df_price_ticker) รับ:
    df_price_ticker : pd.DataFrame ราคาหุ้น 1 ตัว เรียงตามวันที่ (จากตาราง stock_daily_prices)
                      ต้องมีคอลัมน์: close, high, low, RSI14, MACD, ADX, EMA20, EMA50

คืนค่าเป็น dict ที่ต้องมี key:
    timing_score, rsi, macd, adx, ema20, ema50, trend_signal, resistance_60d, support_60d

ที่มาของสูตร: ดูละเอียดใน DATA_FORMULA_AUDIT.md หัวข้อ 3 (Module: Entry Timing)
สรุปสั้น: RSI/MACD/ADX/EMA เป็นค่าสำเร็จรูปจาก Dataset ต้นทาง (ไม่ได้คำนวณในไฟล์นี้)
ส่วนสูตรแปลงเป็นคะแนน 0-100 (rsi_pts, macd_pts, trend_pts) และน้ำหนักถ่วง 35/30/35%
เป็นค่าที่กำหนดเอง — ถ้าจะปรับปรุงตรรกะการให้สัญญาณซื้อ/ขาย แก้ได้ที่ไฟล์นี้ไฟล์เดียว
"""

import numpy as np

from calculate_modules.common import clean_float


def calculate_timing_module(df_price_ticker):
    """Module 3: Entry Timing"""
    latest = df_price_ticker.iloc[-1]

    price = clean_float(latest.get('close'), default=10.0)
    rsi = clean_float(latest.get('RSI14'), default=50.0)
    macd = clean_float(latest.get('MACD'), default=0.0)
    adx = clean_float(latest.get('ADX'), default=20.0)
    ema20 = clean_float(latest.get('EMA20'), default=price)
    ema50 = clean_float(latest.get('EMA50'), default=price)

    rsi_pts = 100 - abs(rsi - 48) * 1.7
    macd_pts = 85 if macd > 0 else 40
    trend_pts = 50 + (15 if price > ema20 else -10) + (15 if ema20 > ema50 else -10)

    timing_score = (rsi_pts * 0.35) + (macd_pts * 0.30) + (trend_pts * 0.35)
    timing_score = round(float(np.clip(timing_score, 25, 95)), 1)

    signal = "BULLISH" if timing_score >= 65 else ("BEARISH" if timing_score < 45 else "NEUTRAL")

    # Key levels จากข้อมูลจริงย้อนหลัง 60 วันทำการ (Recent High/Low method)
    recent = df_price_ticker.tail(60)
    resistance = round(float(recent['high'].max()), 2) if not recent.empty else price * 1.05
    support = round(float(recent['low'].min()), 2) if not recent.empty else price * 0.95

    return {
        'timing_score': timing_score,
        'rsi': round(rsi, 1),
        'macd': round(macd, 3),
        'adx': round(adx, 1),
        'ema20': round(ema20, 2),
        'ema50': round(ema50, 2),
        'trend_signal': signal,
        'resistance_60d': resistance,
        'support_60d': support,
    }
