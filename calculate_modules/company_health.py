"""
calculate_modules/company_health.py
-------------------------------------
สูตรคำนวณโมดูล "Company Health" (💚) — คู่กับ pages_content/company_health.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key โดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

calculate_health_module(df_fin_ticker) รับ:
    df_fin_ticker : pd.DataFrame งบการเงินของหุ้น "1 ตัว" ทุกปีที่มี (มาจากตาราง stock_financials
                    กรองด้วย ticker แล้ว) ต้องมีคอลัมน์: year, roe, roa, de_ratio, current_ratio

คืนค่าเป็น dict ที่ต้องมี key ต่อไปนี้เสมอ (คนอื่น/orchestrator/หน้า UI จะเรียกใช้ key พวกนี้):
    health_score      : float 0-100  (คะแนนรวม ใช้ทั้งหน้า Overview และ Company Health)
    roe, roa           : float       (% ตามที่อยู่ในงบ)
    de_ratio            : float       (เท่า)
    current_ratio        : float       (เท่า)
    s_profitability      : float 0-100 (ใช้ในหน้า Company Health ส่วน 7 Dimensions)
    s_liquidity          : float 0-100
    s_debt               : float 0-100 (ใช้ซ้ำในหน้า Risk Analysis ด้วย เป็น proxy Financial Risk)

build_health_score_yearly(df_fin_ticker) คืน pd.DataFrame คอลัมน์ [year, health_score]
    ใช้วาดกราฟ "Company Health Score Trend" ในหน้า Company Health

ที่มาของสูตร: ดูละเอียดใน DATA_FORMULA_AUDIT.md หัวข้อ 1 (Module: Company Health)
สรุปสั้น: ROE/ROA/D/E/Current Ratio เป็นอัตราส่วนมาตรฐาน แต่ตัวคูณ (3.5, 7.0, 45.0, 40.0)
และน้ำหนักถ่วง (30/25/20/25%) เป็นค่าที่กำหนดเอง (custom heuristic) ไม่ใช่มาตรฐานอุตสาหกรรม
ถ้าจะปรับปรุงสูตรนี้ ทำได้ที่ไฟล์นี้ไฟล์เดียว โดยคง key ที่ return ให้ครบตาม contract ด้านบน
"""

import numpy as np

from calculate_modules.common import clean_float


def calculate_health_module(df_fin_ticker):
    """Module 1: Company Health (ใช้งบปีล่าสุดที่มีจริง)"""
    row_latest = df_fin_ticker.sort_values(by='year').iloc[[-1]]
    r = row_latest.iloc[0]
    roe = clean_float(r.get('roe'), default=10.0)
    roa = clean_float(r.get('roa'), default=5.0)
    de = clean_float(r.get('de_ratio'), default=1.0)
    curr_ratio = clean_float(r.get('current_ratio'), default=1.2)

    s_roe = np.clip(roe * 3.5, 0, 100)
    s_roa = np.clip(roa * 7.0, 0, 100)
    s_liq = np.clip(curr_ratio * 45.0, 0, 100)
    s_debt = np.clip((2.5 - de) * 40.0, 0, 100)

    health_score = (s_roe * 0.30) + (s_roa * 0.25) + (s_liq * 0.20) + (s_debt * 0.25)
    health_score = round(float(np.clip(health_score, 25, 98)), 1)

    return {
        'health_score': health_score,
        'roe': round(roe, 2),
        'roa': round(roa, 2),
        'de_ratio': round(de, 2),
        'current_ratio': round(curr_ratio, 2),
        's_profitability': round(float((s_roe * 0.6) + (s_roa * 0.4)), 1),
        's_liquidity': round(float(s_liq), 1),
        's_debt': round(float(s_debt), 1),
    }


def build_health_score_yearly(df_fin_ticker):
    """คำนวณคะแนน Health รายปี (2023-2025) จากงบการเงินจริงแต่ละปี เพื่อวาดกราฟ trend
    (ใช้สูตรเดียวกับ calculate_health_module() เป๊ะ แค่ทำซ้ำทีละปีแทนที่จะเอาแค่ปีล่าสุด)"""
    import pandas as pd
    rows = []
    for _, r in df_fin_ticker.sort_values('year').iterrows():
        roe = clean_float(r.get('roe'), default=10.0)
        roa = clean_float(r.get('roa'), default=5.0)
        de = clean_float(r.get('de_ratio'), default=1.0)
        curr_ratio = clean_float(r.get('current_ratio'), default=1.2)
        s_roe = np.clip(roe * 3.5, 0, 100)
        s_roa = np.clip(roa * 7.0, 0, 100)
        s_liq = np.clip(curr_ratio * 45.0, 0, 100)
        s_debt = np.clip((2.5 - de) * 40.0, 0, 100)
        score = (s_roe * 0.30) + (s_roa * 0.25) + (s_liq * 0.20) + (s_debt * 0.25)
        rows.append({'year': int(r['year']), 'health_score': round(float(np.clip(score, 25, 98)), 1)})
    return pd.DataFrame(rows)
