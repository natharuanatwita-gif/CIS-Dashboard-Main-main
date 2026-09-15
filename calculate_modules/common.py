"""
calculate_modules/common.py
-----------------------------
โค้ดส่วนกลางที่ทุกโมดูลคำนวณใช้ร่วมกัน (คู่กับ pages_content ที่มี common.py ของตัวเองเหมือนกัน)

⚠️ กติกา: ไฟล์นี้เป็นของกลาง แก้ได้แต่ต้องแจ้งทีม (โดยเฉพาะคนที่ดูแล calculate_scores.py หลัก)
เพราะ clean_float() และ SECTOR_MAP ถูกใช้โดยแทบทุกโมดูล ถ้าแก้พฤติกรรมจะกระทบทุกคน
"""

import pandas as pd

# แผนที่กลุ่มอุตสาหกรรมของหุ้นทั้ง 8 ตัว — ใช้ทั้งใน fair_value.py (เลือก target P/E ตามกลุ่ม)
# และใน calculate_scores.py หลัก (กำหนดคอลัมน์ 'sector' ก่อนส่งต่อให้ industry_benchmark.py จัดอันดับ)
SECTOR_MAP = {
    'ADVANC': 'Technology & Telecomm',
    'TRUE':   'Technology & Telecomm',
    'THCOM':  'Technology & Telecomm',
    'DELTA':  'Electronic Components',
    'HANA':   'Electronic Components',
    'KCE':    'Electronic Components',
    'CCET':   'Electronic Components',
    'JMART':  'Commerce & Technology'
}


def clean_float(val, default=0.0):
    """แปลงค่าตัวเลขที่อาจมี comma/% ปนอยู่ (จากการอ่าน CSV) ให้เป็น float อย่างปลอดภัย
    ใช้ฟังก์ชันนี้ตัวเดียวกันทุกโมดูล ห้ามเขียน parser ของตัวเองซ้ำ"""
    if pd.isna(val) or val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).replace(',', '').replace('%', '').strip()
        if cleaned in ['', '-', 'nan', 'None']:
            return default
        return float(cleaned)
    except Exception:
        return default
