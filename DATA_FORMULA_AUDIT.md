# เอกสารตรวจสอบข้อมูลและสูตรคำนวณ — CIS Dashboard

เอกสารนี้รวบรวม **ทุกตัวเลข ทุกสูตร ทุกแหล่งข้อมูล** ที่ใช้ในแต่ละหน้าของ Dashboard โดยดึงมาจากซอร์สโค้ดจริง
(`calculate_scores.py` และ `app.py`) แบบตรงบรรทัด ไม่ใช่การสรุปคร่าวๆ เพื่อให้นำไปตรวจสอบเอง หรือป้อนให้ AI ตัวอื่นช่วยตรวจทานต่อได้

**วิธีอ่านเอกสารนี้:** ทุกสูตรจะมีป้ายกำกับ 1 ใน 2 แบบ

- 🟢 **มาตรฐาน (Standard)** — สูตรที่มีที่มาจากตำรา/ทฤษฎีทางการเงินหรือสถิติที่เป็นที่ยอมรับทั่วไป มีอ้างอิงชัดเจน
- 🟡 **ประมาณการเอง (Custom Heuristic)** — สูตรที่ผู้พัฒนา (ผม) กำหนดน้ำหนัก/ค่าคงที่เองเพื่อแปลงตัวเลขทางการเงินให้เป็นคะแนน 0-100 ที่เข้าใจง่าย **ไม่ได้อ้างอิงจากงานวิจัยหรือมาตรฐานอุตสาหกรรมใดโดยเฉพาะ** ควรมองว่าเป็น "กรอบให้คะแนนอย่างสมเหตุสมผล" ไม่ใช่สูตรที่ผ่านการพิสูจน์ทางวิชาการ

---

## 0. ภาพรวม Data Pipeline

```
ไฟล์ CSV (Dataset/) → import_data.py → SQLite (cis_database.db) → calculate_scores.py → ตารางผลลัพธ์ → app.py (แสดงผล)
```

### ตารางในฐานข้อมูล

| ตาราง | สร้างโดย | เนื้อหา |
|---|---|---|
| `stock_financials` | import_data.py | งบการเงินปี 2023-2025 จาก `master_all_8_stocks_financials.csv` (+ train/test) |
| `stock_daily_prices` | import_data.py | ราคา OHLCV + indicator รายวัน จาก `stock_cleaned_data_2023_2025.csv` |
| `stock_risk_static` | import_data.py | Beta/Volatility/Max Drawdown จาก `stock_risk_metrics.csv` |
| `cis_summary_scores` | calculate_scores.py | คะแนนสรุปทุกโมดูล (ตารางหลักที่ app.py ใช้) |
| `ai_feature_importance` | calculate_scores.py | น้ำหนัก feature ของโมเดล Random Forest |
| `ai_backtest_history` | calculate_scores.py | ผลทำนายจริงบนชุด Test ปี 2025 |
| `risk_rolling_history` | calculate_scores.py | Volatility/Drawdown รายสัปดาห์ (คำนวณจากราคาจริง) |
| `health_score_yearly` | calculate_scores.py | Health Score รายปี 2023-2025 |
| `fair_value_yearly` | calculate_scores.py | Fair Value ย้อนหลังรายปี เทียบราคาจริง |

**สิ่งสำคัญที่ควรรู้:** ค่า **RSI14, MACD, ADX, EMA20, EMA50** ไม่ได้ถูกคำนวณโดยระบบนี้ — เป็นค่าที่**มาพร้อมกับไฟล์ Dataset ตั้งแต่ต้น** (คอลัมน์สำเร็จรูปใน `stock_cleaned_data_2023_2025.csv`) ระบบแค่ดึงมาใช้ ดังนั้นถ้าจะเช็คความถูกต้องของค่าพวกนี้ ต้องตรวจสอบว่าไฟล์ต้นทางคำนวณมาถูกไหม (เช่น เปิดใน Excel/Python คำนวณ RSI14 เองแล้วเทียบ) ไม่ใช่เช็คโค้ดในโปรเจกต์นี้

**อัปเดต (Dataset ราคาหุ้นเวอร์ชันใหม่):** ไฟล์ราคาหุ้นถูกเปลี่ยนจาก `stock_cleaned_data_2016_2025.csv` (ช่วงข้อมูล 2016-2025)
เป็น `stock_cleaned_data_2023_2025.csv` (ช่วงข้อมูล ก.พ. 2023 - ธ.ค. 2025, 702 แถวต่อหุ้น) — ไม่กระทบผลลัพธ์เพราะระบบใช้แค่ช่วงปี 2023-2025 อยู่แล้ว
ไฟล์ใหม่มีคอลัมน์เพิ่มมา 3 ตัวที่ **ยังไม่มีโมดูลไหนใช้งาน** เก็บไว้ในตาราง `stock_daily_prices` เผื่ออนาคต:
- `adj_close` (Adjusted Close — ราคาปรับด้วยเงินปันผล/การแตกหุ้น อาจมีประโยชน์ถ้าจะคำนวณผลตอบแทนรวม (Total Return) ให้แม่นยำกว่าราคาปิดปกติ)
- `macd_signal`, `macd_hist` (เส้น Signal และ Histogram ของ MACD — Entry Timing ปัจจุบันใช้แค่ค่า MACD ดิบ ถ้าอยากปรับปรุงสัญญาณซื้อขายให้ละเอียดขึ้นสามารถใช้ 2 ค่านี้เสริมได้)

---

## 1. Module: Company Health (💚)

**ไฟล์/ฟังก์ชัน:** `calculate_scores.py` → `calculate_health_module()` (บรรทัด 77-103)
**ข้อมูลนำเข้า:** `stock_financials` ปีล่าสุดที่มี (2025) — คอลัมน์ `roe`, `roa`, `de_ratio`, `current_ratio`

### สูตรคำนวณ (โค้ดจริง)

```python
s_roe  = clip(roe * 3.5, 0, 100)
s_roa  = clip(roa * 7.0, 0, 100)
s_liq  = clip(current_ratio * 45.0, 0, 100)
s_debt = clip((2.5 - de_ratio) * 40.0, 0, 100)

health_score = (s_roe * 0.30) + (s_roa * 0.25) + (s_liq * 0.20) + (s_debt * 0.25)
health_score = clip(health_score, 25, 98)   # บังคับพิสัยคะแนนไม่ให้ต่ำกว่า 25 หรือสูงกว่า 98
```

| ค่า | ป้ายกำกับ | หมายเหตุ |
|---|---|---|
| ROE, ROA, D/E, Current Ratio (ตัวชี้วัดดิบ) | 🟢 มาตรฐาน | เป็นอัตราส่วนการเงินสากล (ROE = Net Income/Equity เป็นต้น) มาจากงบการเงินจริงในไฟล์ CSV โดยตรง ไม่ได้คำนวณเอง |
| ตัวคูณ 3.5 / 7.0 / 45.0 / 40.0 และน้ำหนัก 30/25/20/25% | 🟡 ประมาณการเอง | กำหนดขึ้นเพื่อให้ ROE~15%, ROA~7%, Current Ratio~1.5x, D/E~1.0x ได้คะแนนราวๆ 60-75/100 (ระดับ "ดี") ไม่มีที่มาจากงานวิจัย เป็นการ calibrate ด้วยมือ |
| การ clip คะแนนขั้นต่ำ 25 สูงสุด 98 | 🟡 ประมาณการเอง | เพื่อกันไม่ให้คะแนนติด 0 หรือ 100 พอดี (ดูสมจริงกว่า) ไม่มีนัยทางการเงิน |

### 7 Dimensions (หน้า Company Health เท่านั้น)

**ไฟล์:** `app.py` บรรทัด ~608-641

```python
dim_profit     = s_profitability            # = (s_roe*0.6 + s_roa*0.4) จาก calculate_scores.py
dim_growth     = clip(50 + revenue_growth_yoy * 2, 0, 100)
dim_stability  = s_debt                     # ค่าเดียวกับที่ใช้ใน health_score
dim_liquidity  = s_liquidity                # = s_liq ค่าเดียวกับที่ใช้ใน health_score
dim_cashflow   = clip(50 + ocf_to_ni * 5, 0, 100)
dim_efficiency = clip(roa * 7, 0, 100)      # สูตรเดียวกับ s_roa เป๊ะ (ตั้งใจให้สื่อ "ประสิทธิภาพ")
dim_earnings   = clip(50 + interest_coverage * 0.3, 0, 100)
```

🟡 **ทั้งหมดเป็นสูตรประมาณการเอง** — สังเกตว่า `dim_efficiency` ใช้สูตรเดียวกับ `s_roa` ในการคำนวณ Health Score หลัก (ซ้ำกัน ไม่ใช่มิติที่เป็นอิสระจริง) และ `Weight` ที่แสดง (30%/15%/20%/10%/10%/10%/5%) เป็นตัวเลขที่ใส่ไว้ **เพื่ออธิบายแนวคิด ไม่ได้ถูกใช้คำนวณ `health_score` จริง** (health_score หลักใช้แค่ 4 องค์ประกอบข้างต้น ไม่ใช่ 7 มิตินี้) — **นี่คือจุดที่ควรเพ่งตรวจสอบเป็นพิเศษ เพราะอาจทำให้เข้าใจผิดว่า 7 มิตินี้ถ่วงน้ำหนักกันจริงเป็น 100%**

### Industry Comparison (ค่าเฉลี่ยกลุ่ม)
```python
sector_avg = fin_df[fin_df.ticker in sector_peers][latest_year].mean()  # ค่าเฉลี่ยจริงจาก 8 หุ้นในกลุ่มเดียวกัน
```
🟢 มาตรฐาน (ค่าเฉลี่ยเลขคณิตธรรมดา) — แต่ฐานตัวอย่างมีแค่ 2-4 หุ้นต่อกลุ่มเท่านั้น (ไม่ใช่ทั้งอุตสาหกรรมจริงในตลาด) ควรระวังการตีความว่าเป็น "ค่าเฉลี่ยอุตสาหกรรม" ทั้งตลาด

---

## 2. Module: Fair Value (⚖️)

**ไฟล์/ฟังก์ชัน:** `calculate_scores.py` → `calculate_valuation_module()` (บรรทัด 106-151)

### 2.1 DCF Model (Discounted Cash Flow)

```python
wacc, g = 0.082, 0.02          # WACC 8.2%, Terminal Growth 2%
dcf_equity = (FCF * 1.05) / (wacc - g) - net_debt
dcf_fair   = dcf_equity / จำนวนหุ้น
```

🟢 **มาตรฐาน** — สูตร Gordon Growth Model / Perpetuity DCF (`Value = CF1 / (r - g)`) เป็นสูตรตำราการเงินมาตรฐาน (Damodaran, CFA Institute Valuation Curriculum) อ้างอิงได้

🟡 **ประมาณการเอง (ค่าคงที่ที่เลือกใช้):**
- **WACC = 8.2% คงที่ทุกหุ้น** — ในทางปฏิบัติ WACC ควรคำนวณแยกรายบริษัท (จาก Cost of Equity ผ่าน CAPM + Cost of Debt ถ่วงน้ำหนักโครงสร้างทุนจริง) การใช้ค่าคงที่เดียวเป็นการประมาณอย่างหยาบ
- **Terminal Growth = 2% คงที่ทุกหุ้น** — ปกติควรอิงจากอัตราเงินเฟ้อระยะยาว/อัตราเติบโต GDP แต่ที่นี่ hardcode ไว้
- **`FCF * 1.05`** — สมมติ FCF ปีถัดไปโตจากปีล่าสุด 5% ตายตัว ไม่ได้พยากรณ์จากแนวโน้มจริงของแต่ละบริษัท
- **การ clip `dcf_fair` ให้อยู่ในช่วง 0.65x-1.85x ของราคาตลาดปัจจุบัน** (บรรทัด 129) — นี่คือจุดสำคัญที่ควรรู้: **ถ้า DCF คำนวณออกมาต่ำ/สูงกว่าราคาตลาดมาก ระบบจะ "หนีบ" ค่าให้ไม่ห่างเกิน 65%-185% ของราคาตลาดเสมอ** ทำให้ Fair Value ที่แสดงจะไม่มีวันต่างจากราคาตลาดปัจจุบันได้เกินขอบเขตนี้ ไม่ว่าค่า DCF ดิบจะออกมาเท่าไหร่ — เป็นการ "ควบคุมไม่ให้ตัวเลขแปลกประหลาดเกินไป" แต่ก็หมายความว่า **Margin of Safety ที่แสดงจะไม่มีวันเกิน ±ประมาณ 35-45% โดยดีไซน์** แม้ธุรกิจจะดี/แย่กว่านั้นจริงก็ตาม

### 2.2 P/E Relative Valuation

```python
target_pe = 22.0  ถ้าอยู่กลุ่ม Technology, ไม่งั้น 18.0
pe_fair = EPS ล่าสุด * target_pe
```

🟢 **มาตรฐาน** — วิธี Relative Valuation ด้วย P/E เป็นวิธีที่ใช้กันทั่วไปในการประเมินมูลค่า

🟡 **ประมาณการเอง** — เกณฑ์ P/E เป้าหมาย 22x (เทคโนโลยี) กับ 18x (อื่นๆ) เป็นตัวเลขที่ผมกำหนดเองแบบกว้างๆ **ไม่ได้อ้างอิง P/E เฉลี่ยจริงของตลาดหุ้นไทย (SET) หรือ P/E เฉลี่ยของกลุ่มอุตสาหกรรมจริง ณ ช่วงเวลานั้น** ถ้าต้องการความแม่นยำ ควรแทนที่ด้วย P/E เฉลี่ยจริงของกลุ่มที่ดึงจากตลาดจริง

### 2.3 Blended Fair Value & Margin of Safety

```python
blended_fair = (dcf_fair * 0.55) + (pe_fair * 0.45)
margin_of_safety = (blended_fair - current_price) / blended_fair * 100
valuation_score = clip((margin_of_safety + 20) * 1.4, 25, 95)
```

🟢 สูตร Margin of Safety (ส่วนต่างราคากับมูลค่าที่แท้จริง) เป็นแนวคิดมาตรฐานจาก Value Investing (Benjamin Graham)
🟡 น้ำหนัก 55%/45% ระหว่าง DCF กับ P/E, และสูตรแปลง MOS → คะแนน 0-100 เป็นการกำหนดเอง

### 2.4 P/E, P/B, Market Cap ปัจจุบัน
```python
P/E = current_price / EPS
P/B = current_price / (Total_Equity / จำนวนหุ้น)
Market Cap = current_price * จำนวนหุ้น
```
🟢 **มาตรฐาน 100%** — เป็นนิยามสากลของ P/E, P/B, Market Cap ไม่มีการปรับแต่ง

**⚠️ จุดที่ควรตรวจสอบเป็นพิเศษ:** ตัวแปร `SHARES_OUTSTANDING` (จำนวนหุ้นจดทะเบียน) ใน `calculate_scores.py` บรรทัด 27-36 เป็น **ตัวเลขคงที่ที่ผมกรอกไว้ ณ ช่วงเวลาที่พัฒนา ไม่ได้ดึงจาก Dataset หรือ API ใดๆ** ถ้าจำนวนหุ้นจริงของบริษัทมีการเปลี่ยนแปลง (เพิ่มทุน/ซื้อหุ้นคืน) ค่านี้จะไม่อัปเดตตาม และจะกระทบความถูกต้องของ Market Cap, P/E, P/B, DCF ทั้งหมด — **แนะนำให้เช็คตัวเลขนี้กับข้อมูลจริงจากตลาดหลักทรัพย์ก่อนนำไปอ้างอิงจริงจัง**

---

## 3. Module: Entry Timing (⏱️)

**ไฟล์/ฟังก์ชัน:** `calculate_scores.py` → `calculate_timing_module()` (บรรทัด 154-189)
**ข้อมูลนำเข้า:** RSI14, MACD, ADX, EMA20, EMA50 จาก `stock_daily_prices` (ค่าสำเร็จรูปจาก Dataset ต้นทาง — ดูหัวข้อ 0)

```python
rsi_pts   = 100 - abs(RSI - 48) * 1.7
macd_pts  = 85 ถ้า MACD > 0, ไม่งั้น 40
trend_pts = 50 + (15 ถ้าราคา > EMA20 ไม่งั้น -10) + (15 ถ้า EMA20 > EMA50 ไม่งั้น -10)

timing_score = (rsi_pts*0.35) + (macd_pts*0.30) + (trend_pts*0.35)
```

| ตัวชี้วัดดิบ | ป้ายกำกับ |
|---|---|
| RSI, MACD, ADX, EMA (นิยาม/สูตรคำนวณค่าเหล่านี้) | 🟢 มาตรฐาน (Technical Analysis ทั่วไป — Wilder's RSI, MACD ของ Appel, ADX ของ Wilder) **แต่คำนวณโดยไฟล์ Dataset ต้นทาง ไม่ใช่โค้ดในนี้** |
| สูตรแปลง RSI/MACD/EMA เป็นคะแนน 0-100 (`rsi_pts`, `macd_pts`, `trend_pts`) และน้ำหนัก 35/30/35% | 🟡 ประมาณการเอง — ทั้งหมด |

**จุดสังเกต:** `rsi_pts` ใช้สูตร `100 - |RSI-48|*1.7` หมายความว่า **RSI = 48 จะได้คะแนนเต็ม 100** (ไม่ใช่ RSI=50 ตามทฤษฎีที่มักถือว่าเป็นจุดกลาง) เป็นตัวเลขที่ผม calibrate เอง ไม่มีเหตุผลทางทฤษฎีรองรับเจาะจงว่าทำไมต้องเป็น 48

**Key Levels (Support/Resistance):** `resistance_60d = max(high, 60 วันล่าสุด)`, `support_60d = min(low, 60 วันล่าสุด)` — 🟢 เป็นวิธีหาแนวรับ-แนวต้านแบบพื้นฐานที่ใช้กันทั่วไป (Recent High/Low) แต่เป็นวิธีที่หยาบเมื่อเทียบกับการหา Pivot Point หรือ Volume Profile ที่ซับซ้อนกว่า

---

## 4. Module: AI Prediction (🔮)

**ไฟล์/ฟังก์ชัน:** `calculate_scores.py` → `train_and_predict_ai()` (บรรทัด 192-254)

### 4.1 นิยามปัญหา (Label Definition)
```python
target = 1 ถ้าราคาปิดในอีก 10 วันทำการข้างหน้า > ราคาปิดวันนี้, ไม่งั้น 0
features = [close, EMA20, EMA50, RSI14, MACD, ADX]
train = ข้อมูลปี 2023-2024, test = ข้อมูลปี 2025
model = RandomForestClassifier(n_estimators=200, max_depth=4, random_state=42)
```
🟢 **มาตรฐาน 100%** — Random Forest เป็นอัลกอริทึมมาตรฐานจาก scikit-learn, การแบ่ง Train/Test แบบ Out-of-time (ฝึกด้วยอดีต ทดสอบด้วยอนาคต) เป็นวิธีที่ถูกต้องสำหรับข้อมูลอนุกรมเวลา (ป้องกัน data leakage) `n_estimators`, `max_depth` เป็น hyperparameter ที่เลือกเอง (🟡 ปรับแต่งได้ ไม่ใช่ค่าที่ตายตัวจากทฤษฎี)

### 4.2 Metrics การประเมินโมเดล
```python
accuracy_score, precision_score, recall_score, f1_score, roc_auc_score  # จาก sklearn.metrics
```
🟢 **มาตรฐาน 100%** — เป็นฟังก์ชันสำเร็จรูปจาก scikit-learn ตามนิยามทางสถิติสากล ไม่มีการปรับแต่งสูตรใดๆ **นี่คือจุดที่น่าเชื่อถือที่สุดในระบบทั้งหมด** เพราะเป็น library มาตรฐานคำนวณให้ ไม่ใช่สูตรที่ผมเขียนเอง — ควรดูค่า **Accuracy/ROC-AUC ควบคู่กับ Prob. Up เสมอ** ถ้า Accuracy ~50-55% แปลว่าโมเดลแทบไม่ต่างจากการเดาสุ่ม

### 4.3 AI Score (คะแนนรวมที่แสดงบน Dashboard)
```python
ai_score = clip((prob_up * 0.7) + (accuracy * 0.3), 30, 95)
```
🟡 **ประมาณการเอง** — การผสม prob_up (70%) กับ accuracy (30%) เป็นสูตรที่กำหนดเอง เพื่อไม่ให้คะแนนสูงทั้งที่โมเดลไม่แม่นยำ

### 4.4 Forecast Band ในกราฟ (หน้า AI Prediction)
**ไฟล์:** `app.py` บรรทัด ~1258-1264
```python
drift = (prob_up - 50) / 50 * daily_vol * horizon_days
median_path = current_price * (1 + drift * (t/horizon_days))
band = current_price * daily_vol * sqrt(t) * 1.28   # ประมาณ 80% confidence band
```
🟢 รูปแบบการคำนวณ band อิงหลัก **Random Walk / Geometric Brownian Motion** (ความกว้างของช่วงความเชื่อมั่นโตตาม √เวลา) เป็นแนวคิดมาตรฐานทางการเงินเชิงปริมาณ
🟡 ค่าคงที่ 1.28 (ประมาณ 80% band ทางทฤษฎีควรเป็น z=1.28 สำหรับ one-tail 90% หรือ z=1.04 สำหรับ 70% two-tail — **ค่านี้ใช้แบบประมาณ ไม่ใช่การคำนวณ confidence interval ที่เข้มงวดทางสถิติ**) และการแปลง `prob_up` เป็น `drift` เป็นการประมาณเชิงเส้นอย่างง่าย ไม่ใช่แบบจำลองการเงินที่ผ่านการทดสอบ

### 4.5 Feature Importance
```python
model.feature_importances_   # จาก RandomForestClassifier ของ sklearn (Gini Importance)
```
🟢 **มาตรฐาน** — เป็นค่าที่ scikit-learn คำนวณให้อัตโนมัติจาก Mean Decrease in Impurity ของแต่ละ feature ในทุกต้นไม้ตัดสินใจ
⚠️ **ข้อควรระวังทางเทคนิค:** เดิมทีมีการตั้งชื่อว่า "SHAP-style Feature Importance" ในบางจุดของ UI แต่ **นี่ไม่ใช่ค่า SHAP จริง** (SHAP ต้องใช้ library `shap` แยกต่างหากซึ่งไม่ได้ติดตั้งในโปรเจกต์นี้) เป็นแค่ Feature Importance ปกติของ Random Forest ซึ่งตีความคล้ายกันแต่คำนวณด้วยวิธีต่างกัน (Gini Importance มีอคติต่อ feature ที่มีค่าต่อเนื่อง/หลากหลายค่ามากกว่า feature แบบ categorical)

---

## 5. Module: Risk Analysis (🛡️)

**ไฟล์/ฟังก์ชัน:** `calculate_scores.py` → `calculate_risk_module()` (บรรทัด 257-300)

### 5.1 Beta, Volatility, Max Drawdown (ค่าหลัก)
```python
beta = ค่าจาก stock_risk_metrics.csv โดยตรง (ถ้ามี)
annual_vol = ค่าจาก stock_risk_metrics.csv โดยตรง (ถ้ามี) 
max_dd = ค่าจาก stock_risk_metrics.csv โดยตรง (ถ้ามี)
```
🟢 **มาตรฐาน** — ดึงจากไฟล์ Dataset ที่เตรียมไว้ล่วงหน้าโดยตรง (นิยาม Beta = Cov(หุ้น,ตลาด)/Var(ตลาด) เป็นสูตรสากล) **แต่ระบบนี้ไม่ได้คำนวณ Beta เอง เพียงดึงค่าที่มีอยู่แล้วในไฟล์ CSV มาใช้** — ถ้าต้องการตรวจสอบความถูกต้องของ Beta ต้องกลับไปดูว่าไฟล์ `stock_risk_metrics.csv` คำนวณมาอย่างไร (ใช้ดัชนีอ้างอิงตัวไหน ช่วงเวลาไหน)

**Fallback (ถ้าไม่มีข้อมูลใน stock_risk_metrics.csv):**
```python
annual_vol_calc = std(daily_returns) * sqrt(252) * 100
max_dd_calc = min((price - cummax(price)) / cummax(price)) * 100
```
🟢 **มาตรฐาน 100%** — สูตร Annualized Volatility (√252 คือจำนวนวันเทรดต่อปีมาตรฐาน) และ Maximum Drawdown เป็นสูตรตำราการเงินเชิงปริมาณที่ใช้กันทั่วไป ไม่มีการปรับแต่ง

### 5.2 Value at Risk (VaR 95%)
```python
var_95 = 1.645 * daily_std * 100
```
🟢 **มาตรฐาน** — Parametric VaR (Variance-Covariance Method) โดย 1.645 คือ z-score ของ Normal Distribution ที่ระดับความเชื่อมั่น 95% (ค่ามาตรฐานทางสถิติ ตรวจสอบได้จากตาราง Z-table) **ข้อจำกัดที่ควรรู้:** วิธีนี้สมมติว่าผลตอบแทนแจกแจงแบบ Normal Distribution ซึ่งในทางปฏิบัติราคาหุ้นมักมี "หางอ้วน" (fat tails) มากกว่าการแจกแจงปกติจริง ทำให้ VaR แบบนี้มักประเมินความเสี่ยงต่ำกว่าความเป็นจริงในช่วงตลาดผันผวนรุนแรง

### 5.3 Sharpe & Sortino Ratio
```python
Sharpe  = (mean_daily_return * 252) / (daily_std * sqrt(252))
Sortino = (mean_daily_return * 252) / (downside_std * sqrt(252))
```
🟢 **มาตรฐาน 100%** — สูตร Sharpe Ratio (William Sharpe, 1966) และ Sortino Ratio เป็นสูตรการเงินสากล **ข้อสังเกต:** สูตรนี้ไม่ได้หัก Risk-free Rate ออกจาก return ก่อนคำนวณ (สูตรเต็มคือ `(Return - Risk_free) / Std`) ในที่นี้ปัดให้ Risk-free Rate = 0 ซึ่งเป็นการลดความซับซ้อน อาจทำให้ Sharpe/Sortino สูงกว่าที่ควรจะเป็นเล็กน้อยเมื่อเทียบกับสูตรเต็ม

### 5.4 Risk Score รวม
```python
risk_index = (volatility*0.45) + (max_drawdown*0.35) + (VaR*2.0)
risk_score = clip(100 - risk_index, 25, 92)
```
🟡 **ประมาณการเอง** — น้ำหนักและการแปลงเป็นคะแนน (คะแนนสูง = เสี่ยงต่ำ) เป็นการกำหนดเอง

### 5.5 Risk Dimension breakdown (6 วงกลมย่อยในหน้า Risk Analysis)
**ไฟล์:** `app.py` บรรทัด ~1405-1410
```python
market_risk     = clip(beta * 40, 5, 95)
price_risk      = clip(volatility * 1.3, 5, 95)
financial_risk  = clip(de_ratio * 25, 5, 95)
liquidity_risk  = clip((2.0 - current_ratio) * 40, 5, 95)
downside_risk   = clip(max_drawdown * 1.5, 5, 95)
overall_risk_dim = clip(100 - risk_score, 5, 95)
```
🟡 **ประมาณการเองทั้งหมด** — ตัวคูณ 40, 1.3, 25, 40, 1.5 ไม่มีที่มาทางทฤษฎี เป็นการปรับให้ตัวเลขทั่วไปตกอยู่ในช่วงที่ดูสมเหตุสมผล (0-100)

### 5.6 Stress Test Scenario
**ไฟล์:** `app.py` บรรทัด ~1509-1511
```python
crash_impact      = beta * -20        # Market Crash -20%
rate_impact       = -volatility * 0.35
recession_impact  = beta*-15 - max_drawdown*0.1
```
🟡 **ประมาณการเองทั้งหมด — ควรระวังเป็นพิเศษ** สูตร `impact = Beta × market_shock` มีที่มาจากนิยาม Beta จริง (ถ้า Beta=1.2 และตลาดร่วง 20% ตามทฤษฎี CAPM หุ้นควรร่วงประมาณ 24%) จึงพอมีหลักการรองรับระดับหนึ่ง 🟢 แต่ `rate_impact` และ `recession_impact` เป็นสูตรที่ผมประดิษฐ์ขึ้นเองล้วนๆ ไม่มีโมเดลเศรษฐศาสตร์รองรับ **ไม่ควรนำตัวเลขในตารางนี้ไปอ้างอิงเป็นการพยากรณ์ผลกระทบจริงจากเหตุการณ์เหล่านี้**

### 5.7 Calmar Ratio
```python
Calmar = (average_annual_return / max_drawdown)
```
🟢 มาตรฐาน (นิยาม Calmar Ratio สากล)

---

## 6. Module: Industry Benchmark (📊)

**ไฟล์:** `app.py` (คำนวณในชั้น display layer ทั้งหมด ไม่มีใน calculate_scores.py) + ใช้ `sector_rank`/`overall_rank` ที่คำนวณไว้แล้วใน `calculate_scores.py` บรรทัด 452-453

```python
sector_rank  = จัดอันดับ overall_score ภายในกลุ่มเซกเตอร์เดียวกัน (rank แบบ ascending=False)
overall_rank = จัดอันดับ overall_score เทียบทั้ง 8 หุ้น
percentile   = pandas .rank(pct=True) ต่อคอลัมน์คะแนนแต่ละมิติ เทียบทั้ง 8 หุ้นที่ติดตาม
```
🟢 การจัดอันดับ (Ranking) และ Percentile เป็นวิธีทางสถิติมาตรฐาน (ใช้ `pandas.rank()`)
⚠️ **ข้อจำกัดสำคัญที่ต้องเข้าใจ:** ฐานเทียบมีแค่ **8 หุ้นเท่านั้น** (ไม่ใช่ทั้งตลาด SET หรือทั้งอุตสาหกรรมจริง) คำว่า "Top 10%" หรือ "อันดับ 1 ใน Sector" ในหน้านี้หมายถึง **อันดับ 1 ใน 3-4 หุ้นที่อยู่ในกลุ่มเดียวกันจาก 8 หุ้นที่ระบบนี้ติดตามเท่านั้น ไม่ใช่อันดับ 1 ในอุตสาหกรรมจริงทั้งตลาดหลักทรัพย์** ควรระวังการตีความคำว่า "Industry Leader" ผิดไปว่าเทียบกับทุกบริษัทในตลาดจริง

---

## 7. หน้า Overview: Overall Score & Recommendation

**ไฟล์:** `calculate_scores.py` บรรทัด 443-461

```python
overall_score = (health*0.25) + (valuation*0.25) + (timing*0.15) + (ai*0.10) + (risk*0.15) + (industry*0.10)

recommendation:
    >= 75  → STRONG BUY
    >= 65  → BUY
    >= 50  → ACCUMULATE
    < 50   → REDUCE / SELL
```

🟡 **ประมาณการเองทั้งหมด** — ทั้งน้ำหนักถ่วง 25/25/15/10/15/10% และเกณฑ์ตัดสิน (threshold) 75/65/50 เป็นการกำหนดเองล้วนๆ ไม่มีโมเดล Asset Allocation หรือ Scoring System ทางวิชาการรองรับโดยตรง **นี่คือตัวเลขสรุปที่ผู้ใช้เห็นเป็นอันดับแรกและมีอิทธิพลต่อการตัดสินใจมากที่สุด แต่เป็นสูตรที่ "สังเคราะห์ขึ้นเพื่อจุดประสงค์ของโปรเจกต์นี้" ไม่ใช่ระบบให้คะแนนที่ผ่านการ validate ด้วยผลตอบแทนย้อนหลังจริง (backtested) ว่าหุ้นที่ได้ STRONG BUY เคยให้ผลตอบแทนดีกว่าจริงในอดีตหรือไม่**

---

## 8. ตารางสรุป: อะไรน่าเชื่อถือ อะไรควรตรวจสอบเพิ่ม

| ระดับความน่าเชื่อถือ | รายการ |
|---|---|
| 🟢 **เชื่อถือได้สูง** (สูตร/library มาตรฐาน คำนวณถูกต้องตามนิยาม) | ROE/ROA/D/E/Current Ratio ดิบ, Market Cap/P/E/P/B ปัจจุบัน, Sharpe/Sortino/Calmar, VaR (parametric), Annualized Volatility, Max Drawdown, DCF/P/E Relative concept, sklearn metrics (Accuracy/Precision/Recall/F1/ROC-AUC), Random Forest Feature Importance, Ranking/Percentile |
| 🟡 **ใช้ประกอบการตัดสินใจได้ แต่เป็น judgment call ของผู้พัฒนา ไม่ใช่มาตรฐานอุตสาหกรรม** | ทุกสูตรแปลง "ตัวชี้วัดดิบ → คะแนน 0-100" (เช่น `roe*3.5`, `rsi_pts`), น้ำหนักถ่วงทุกจุด (Health/Timing/Risk/Overall Score), เกณฑ์ STRONG BUY/BUY/ACCUMULATE, WACC/Terminal Growth/Target P/E ที่ hardcode, การ clip DCF ให้อยู่ในกรอบ 65-185% ของราคาตลาด |
| ⚠️ **ควรตรวจสอบกับแหล่งข้อมูลภายนอกก่อนอ้างอิงจริงจัง** | จำนวนหุ้นจดทะเบียน (`SHARES_OUTSTANDING`) เป็นค่าคงที่ที่กรอกด้วยมือ, Beta/Volatility/Max Drawdown จาก `stock_risk_metrics.csv` (ต้องเช็คว่าไฟล์ต้นทางคำนวณถูกต้อง/อัปเดตล่าสุดแค่ไหน), RSI/MACD/ADX/EMA (คำนวณจาก Dataset ต้นทาง ไม่ใช่โค้ดในนี้) |
| 🚫 **ไม่ควรนำไปอ้างอิงเป็นการพยากรณ์จริง** | Stress Test Scenario (rate_impact, recession_impact), Forecast Band ในหน้า AI Prediction (เป็นการประมาณแบบง่าย ไม่ใช่โมเดลพยากรณ์ที่ผ่านการ validate) |

---

## 9. แนวทางถ้าจะให้ AI ช่วยตรวจสอบต่อ

เอกสารนี้ถูกออกแบบให้ป้อนให้ AI (เช่น Claude, ChatGPT อีก instance หนึ่ง) ช่วยตรวจทานได้ทันที โดยแนะนำให้ถามเป็นคำถามเฉพาะจุด เช่น:

- "สูตร Gordon Growth Model ในหัวข้อ 2.1 ถูกต้องตามทฤษฎีไหม เขียนสูตรเต็มให้เทียบ"
- "น้ำหนัก 55/45 ระหว่าง DCF กับ P/E Relative ในหัวข้อ 2.3 มีมาตรฐานอุตสาหกรรมกำหนดไว้ไหม หรือเป็นเรื่องของดุลยพินิจ"
- "สูตร Sharpe Ratio ที่ไม่หัก Risk-free Rate (หัวข้อ 5.3) จะทำให้ค่าคลาดเคลื่อนไปมากแค่ไหนในทางปฏิบัติ"
- "การจัดอันดับ Industry Benchmark จากฐาน 8 หุ้น (หัวข้อ 6) ควรตีความอย่างไรไม่ให้เข้าใจผิด"

การถามทีละหัวข้อแบบนี้จะช่วยให้ AI ตัวที่ช่วยตรวจสอบโฟกัสได้ลึกกว่าการถามรวมทั้งเอกสารทีเดียว
