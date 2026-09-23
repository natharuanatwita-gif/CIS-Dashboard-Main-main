"""
calculate_modules/fair_value.py — v3
=======================================
สูตรคำนวณโมดูล "Fair Value" (⚖️) — คู่กับ pages_content/fair_value.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key เดิมโดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===
คืนค่าเป็น dict ที่ต้องมี key เดิมครบ:
    valuation_score, fair_value, dcf_fair_value, pe_fair_value,
    margin_of_safety, pe_ratio, pb_ratio, market_cap_mb, eps
    wacc_used, terminal_growth_used, fcf_growth_assumed, fcf_base_used   (v2)

⚠️ Breaking change ที่ต้องรู้ (v3): fair_value, margin_of_safety, dcf_fair_value, pe_fair_value
   อาจเป็น None ได้แล้ว (เดิมไม่เคยเป็น None) — ฝั่ง UI ต้องอ่านผ่าน safe()/fmt_ratio() เสมอ

=== v3 CHANGELOG (ตอบสนองรายงาน Audit ทั้ง 6 ประเด็น) ===
[ISSUE 01] Clip 65%-185% ใช้เฉพาะตอนคำนวณคะแนน (calc_sub_score) เท่านั้น
           ค่าที่แสดงผลจริง (dcf_fair_value / pe_fair_value / fair_value / margin_of_safety) เป็นค่าดิบ
           เพิ่ม raw_dcf_fair_value, raw_pe_fair_value, dcf_is_clipped, pe_is_clipped ให้ UI ทำ Warning Badge ได้
[ISSUE 02] เลิกใช้ fallback current_price*0.85 (P/E) และ *0.90 (DCF) เมื่อ EPS/FCF ติดลบ
           ค่านั้นเป็น None ("ประเมินไม่ได้") และคะแนนย่อยของโมเดลนั้นถูกบังคับเป็น 0 คะแนน (penalty)
[ISSUE 03] pe_score / dcf_score คำนวณแยกจากกันจริงผ่าน calc_sub_score() ไม่ใช้ val_score ตัวเดียวซ้ำ 2 แถบ
[ISSUE 04] confidence_level ใช้ระบบ Penalty System 3 ระดับ อิงคุณภาพข้อมูล ไม่ใช่ขนาด MOS อย่างเดียว:
           ขาดทุน/ประเมินไม่ได้ -> Low, ชนกรอบ Clip -> Medium, กำไร+ไม่ชนกรอบ+MOS>15% -> High, อื่นๆ -> Medium
[ISSUE 05] Guard กัน crash เมื่อ df_fin_ticker เป็น None/ว่างเปล่า หรือ current_price <= 0
[ISSUE 06] เพิ่ม valuation_methodology_note (Disclaimer) อธิบายที่มาของ WACC/Target P/E ว่าเป็น
           Sector Baseline ที่ทีมกำหนดเอง พร้อมระบุแผนพัฒนาเป็น Dynamic (ใช้ Beta รายบริษัท) ในเฟสถัดไป
"""

import numpy as np
import pandas as pd
from calculate_modules.common import clean_float, SECTOR_MAP

SHARES_OUTSTANDING = {
    'ADVANC': 2974000000, 'CCET': 10400000000, 'DELTA': 12473000000, 'HANA': 885000000,
    'JMART': 1450000000, 'KCE': 1182000000, 'THCOM': 1096000000, 'TRUE': 34500000000
}

SECTOR_WACC = {
    'Technology & Telecomm': 0.078, 'Electronic Components': 0.088, 'Commerce & Technology': 0.092,
}
SECTOR_TERMINAL_G = {
    'Technology & Telecomm': 0.020, 'Electronic Components': 0.015, 'Commerce & Technology': 0.025,
}
DEFAULT_WACC = 0.082
DEFAULT_TERMINAL_G = 0.02
NEAR_TERM_GROWTH_PREMIUM = 0.015

VALUATION_METHODOLOGY_NOTE = (
    "WACC และ Target P/E อ้างอิงจาก Sector Baseline ที่ทีมกำหนดเอง (ไม่ใช่ค่า Beta รายบริษัทจริงผ่าน CAPM) "
    "เนื่องจาก Data Contract ปัจจุบันยังไม่ส่งค่า Beta รายตัวเข้ามา — แผนพัฒนาเฟสถัดไปจะปรับให้ดึงค่า P/E Band "
    "ย้อนหลัง 5 ปีและ Beta รายบริษัทมาคำนวณแบบ Dynamic ใช้ตัวเลขนี้ประกอบการตัดสินใจ ไม่ใช่คำแนะนำการลงทุน"
)

_EMPTY_KEYS = [
    'valuation_score', 'fair_value', 'dcf_fair_value', 'pe_fair_value', 'margin_of_safety',
    'pe_ratio', 'pb_ratio', 'market_cap_mb', 'eps',
    'wacc_used', 'terminal_growth_used', 'fcf_growth_assumed', 'fcf_base_used',
    'raw_dcf_fair_value', 'raw_pe_fair_value', 'dcf_is_clipped', 'pe_is_clipped',
    'pe_score', 'dcf_score',
]


def calc_sub_score(raw_fair_value, current_price):
    """คะแนนย่อย 0-100 ของโมเดลเดียว — Clip เฉพาะตอนคำนวณคะแนน (ไม่กระทบค่าที่แสดงผล)"""
    if raw_fair_value is None or current_price is None or current_price <= 0:
        return None, False
    fair_for_score = float(np.clip(raw_fair_value, current_price * 0.65, current_price * 1.85))
    is_clipped = abs(fair_for_score - raw_fair_value) > 1e-6
    margin = (fair_for_score - current_price) / fair_for_score * 100 if fair_for_score > 0 else 0.0
    score = round(float(np.clip((margin + 20) * 1.4, 25, 95)), 1)
    return score, is_clipped


def calculate_valuation_module(df_fin_ticker, current_price, ticker):
    """Module 2: Fair Value (DCF + Relative PE) — v3"""

    if df_fin_ticker is None or df_fin_ticker.empty or current_price is None or current_price <= 0:
        out = {k: None for k in _EMPTY_KEYS}
        out['valuation_score'] = 0.0
        out['valuation_status'] = 'NO_DATA'
        out['confidence_level'] = 'Low'
        out['valuation_methodology_note'] = VALUATION_METHODOLOGY_NOTE
        out['warning_message'] = 'ไม่มีข้อมูลงบการเงิน หรือราคาหุ้นไม่ถูกต้อง ไม่สามารถประเมินมูลค่าได้'
        return out

    fin_sorted = df_fin_ticker.sort_values(by='year')
    row_latest = fin_sorted.iloc[[-1]]
    r = row_latest.iloc[0]

    shares = SHARES_OUTSTANDING.get(ticker, 1000000000)
    net_inc = clean_float(r.get('net_income'), default=1000.0)
    eps = clean_float(r.get('eps'), default=0.5)

    fcf_hist = fin_sorted['free_cash_flow'].apply(clean_float).tail(2)
    fcf_base = float(fcf_hist.mean()) if len(fcf_hist) > 0 else net_inc * 0.75

    total_debt = clean_float(r.get('total_liabilities'), default=0.0)
    cash = clean_float(r.get('cash_and_equivalents'), default=0.0)
    net_debt = total_debt - cash

    sector = SECTOR_MAP.get(ticker, '')
    wacc = SECTOR_WACC.get(sector, DEFAULT_WACC)
    g = SECTOR_TERMINAL_G.get(sector, DEFAULT_TERMINAL_G)
    near_term_growth = g + NEAR_TERM_GROWTH_PREMIUM

    dcf_equity = ((fcf_base * (1 + near_term_growth)) / (wacc - g)) - net_debt
    raw_dcf_fair_value = (dcf_equity / shares) if (dcf_equity > 0 and shares > 0) else None

    target_pe = 22.0 if 'Technology' in sector else 18.0
    raw_pe_fair_value = (eps * target_pe) if eps > 0 else None

    dcf_score, dcf_is_clipped = calc_sub_score(raw_dcf_fair_value, current_price)
    pe_score, pe_is_clipped = calc_sub_score(raw_pe_fair_value, current_price)
    dcf_score_for_blend = dcf_score if dcf_score is not None else 0.0
    pe_score_for_blend = pe_score if pe_score is not None else 0.0
    dcf_is_clipped = bool(dcf_is_clipped)
    pe_is_clipped = bool(pe_is_clipped)

    fair_components = [(raw_dcf_fair_value, 0.55), (raw_pe_fair_value, 0.45)]
    valid_fair = [(v, w) for v, w in fair_components if v is not None]
    if not valid_fair:
        blended_fair = None
        mos = None
        valuation_status = 'NOT_RATED'
    else:
        total_w = sum(w for _, w in valid_fair)
        blended_fair = round(sum(v * w for v, w in valid_fair) / total_w, 2)
        mos = round((blended_fair - current_price) / blended_fair * 100, 1)
        valuation_status = 'OK' if len(valid_fair) == 2 else 'PARTIAL'

    val_score = round(dcf_score_for_blend * 0.55 + pe_score_for_blend * 0.45, 1)

    is_profitable = eps > 0 and fcf_base > 0
    if (not is_profitable) or valuation_status in ('NOT_RATED', 'NO_DATA'):
        confidence_level = 'Low'
    elif dcf_is_clipped or pe_is_clipped:
        confidence_level = 'Medium'
    elif mos is not None and mos > 15:
        confidence_level = 'High'
    else:
        confidence_level = 'Medium'

    warning_message = None
    if valuation_status == 'NOT_RATED':
        warning_message = 'ไม่สามารถประเมินมูลค่าได้เนื่องจากบริษัทมีผลการดำเนินงานขาดทุน (EPS และ/หรือ FCF ติดลบ)'
    elif valuation_status == 'PARTIAL':
        warning_message = 'ประเมินได้เพียงวิธีเดียว (อีกวิธีขาดทุน/คำนวณไม่ได้) ควรใช้ระมัดระวังเป็นพิเศษ'
    elif dcf_is_clipped or pe_is_clipped:
        warning_message = 'ค่าประเมินดิบเกินกรอบปกติของโมเดล ตัวเลข Fair Value ที่แสดงเป็นค่าดิบยังไม่ได้ปรับ'

    pe_ratio_now = round(float(current_price / eps), 2) if eps > 0 else None
    book_value_per_share = clean_float(r.get('total_equity'), 0.0) / shares if shares else 0.0
    pb_ratio_now = round(float(current_price / book_value_per_share), 2) if book_value_per_share > 0 else None
    market_cap = round(current_price * shares / 1e6, 1)

    return {
        'valuation_score': val_score,
        'fair_value': blended_fair,
        'dcf_fair_value': round(raw_dcf_fair_value, 2) if raw_dcf_fair_value is not None else None,
        'pe_fair_value': round(raw_pe_fair_value, 2) if raw_pe_fair_value is not None else None,
        'margin_of_safety': mos,
        'pe_ratio': pe_ratio_now,
        'pb_ratio': pb_ratio_now,
        'market_cap_mb': market_cap,
        'eps': round(eps, 2),
        'wacc_used': round(wacc * 100, 2),
        'terminal_growth_used': round(g * 100, 2),
        'fcf_growth_assumed': round(near_term_growth * 100, 2),
        'fcf_base_used': round(fcf_base, 1),
        'raw_dcf_fair_value': round(raw_dcf_fair_value, 2) if raw_dcf_fair_value is not None else None,
        'raw_pe_fair_value': round(raw_pe_fair_value, 2) if raw_pe_fair_value is not None else None,
        'dcf_is_clipped': dcf_is_clipped,
        'pe_is_clipped': pe_is_clipped,
        'pe_score': pe_score_for_blend,
        'dcf_score': dcf_score_for_blend,
        'valuation_status': valuation_status,
        'confidence_level': confidence_level,
        'valuation_methodology_note': VALUATION_METHODOLOGY_NOTE,
        'warning_message': warning_message,
    }


def build_fair_value_yearly(df_fin_ticker, df_price_ticker, ticker):
    import pandas as pd
    rows = []
    price_df = df_price_ticker.copy()
    price_df['date'] = pd.to_datetime(price_df['date'])
    for yr in sorted(df_fin_ticker['year'].unique()):
        fin_upto = df_fin_ticker[df_fin_ticker['year'] <= yr]
        if fin_upto.empty:
            continue
        year_end_prices = price_df[price_df['date'] <= f'{yr}-12-31']
        if year_end_prices.empty:
            continue
        year_end_price = clean_float(year_end_prices.sort_values('date').iloc[-1]['close'])
        try:
            val = calculate_valuation_module(fin_upto, year_end_price, ticker)
            rows.append({'year': int(yr), 'price': round(year_end_price, 2), 'fair_value': val['fair_value']})
        except Exception:
            continue
    return pd.DataFrame(rows)
