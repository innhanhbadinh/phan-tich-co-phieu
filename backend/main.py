"""API phân tích & định giá cổ phiếu từ dữ liệu CafeF.

Chạy thử:   uvicorn main:app --reload
Render:     uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import re
import time
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import cafef
from analysis import ci_highest, quality_checks, technical

app = FastAPI(title="Phân tích cổ phiếu CafeF")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

CACHE_TTL = 600  # giây
_cache = {}


@app.get("/")
def root():
    return {"ok": True, "huong_dan": "GET /api/analyze/FPT"}


@app.get("/api/health")
def health():
    return {"ok": True}


def build(symbol, raw):
    warnings = []
    inc, bs, rat = raw["income"], raw["balance"], raw["ratios"]

    # ---- Lợi nhuận sau thuế cổ đông công ty mẹ 4 quý gần nhất (tỷ đồng)
    quarters = []
    for q in inc[:4]:
        ni = q["values"].get("NetIncome")
        if ni is None:
            ni = q["values"].get("LNSTTNDN")
        quarters.append({"quy": q["time"], "lnst": (ni or 0) / 1e6})
    if len(quarters) < 4:
        warnings.append("Chưa đủ 4 quý báo cáo — LNST có thể chưa đầy đủ.")
    profit = sum(x["lnst"] for x in quarters)

    # ---- Vốn chủ sở hữu (tỷ đồng)
    eq_total = None
    if bs:
        vals = bs[0]["values"]
        eq_k = vals.get("TotalOwnerCapital")
        if eq_k is None:
            eq_k = vals.get("VonQui")  # ngân hàng
        eq_total = eq_k / 1e6 if eq_k else None
    if not eq_total:
        raise HTTPException(502, "Không lấy được vốn chủ sở hữu từ CafeF")
    minority = (raw["minority_vnd"] or 0) / 1e9
    if raw["minority_vnd"] is None:
        warnings.append("Không đọc được lợi ích cổ đông không kiểm soát — đang dùng tổng vốn chủ sở hữu.")
    equity = eq_total - minority

    # ---- Số cổ phiếu lưu hành (triệu cp)
    shares = cafef._num(rat.get("KlcpLuuHanh")) or cafef._num(rat.get("KlcpNY"))
    if not shares:
        raise HTTPException(502, "Không lấy được số lượng cổ phiếu lưu hành")
    shares_m = shares / 1e6

    # ---- Giá
    bars = raw["bars"]
    price = raw["realtime"].get("price") or (bars[-1]["close"] if bars else None)
    if not price:
        raise HTTPException(502, "Không lấy được thị giá")

    # ---- Cổ tức tiền mặt 12 tháng
    div_rate, div_used = cafef.cash_dividend_rate(raw["events"])
    if not div_used:
        warnings.append("Không thấy cổ tức tiền mặt trong 12 tháng qua — tỷ lệ cổ tức = 0%.")

    val = ci_highest(profit, equity, div_rate, price, shares_m)
    quality = quality_checks(inc, profit, equity, val["lai_von"])
    tech = technical(bars, price)
    q_by = {q["ten"]: q for q in quality}
    ss_base = {
        "tl_gop": q_by.get("Tỷ lệ lãi gộp > 15%", {}).get("gia_tri"),
        "loi_nhuan_on_dinh": q_by.get("Lợi nhuận ổn định, tăng trưởng", {}).get("dat"),
        "ky_thuat": tech.get("ss", {}),
    }

    return {
        "ma": symbol,
        "ten": (raw.get("company") or {}).get("t"),
        "san": (raw.get("company") or {}).get("san"),
        "cap_nhat": datetime.now(cafef.VN_TZ).strftime("%H:%M %d/%m/%Y"),
        "dau_vao": {
            "lnst_4_quy": profit,
            "von_chu_so_huu": equity,
            "tong_von_chu_so_huu": eq_total,
            "loi_ich_thieu_so": minority,
            "ty_le_co_tuc": div_rate,
            "thi_gia": price,
            "so_cp_trieu": shares_m,
            "quy_bctc": bs[0]["time"] if bs else None,
        },
        "chi_tiet_dau_vao": {"cac_quy": quarters, "co_tuc": div_used,
                             "eps": rat.get("EPScoBan"), "pe": rat.get("P/E"), "pb": rat.get("Beta")},
        "dinh_gia": val,
        "chat_luong": quality,
        "tieu_chi_ss": ss_base,
        "ky_thuat": tech,
        "nen": bars,
        "canh_bao": warnings,
        "nguon": f"https://cafef.vn/du-lieu/{symbol.lower()}.chn",
    }


@app.get("/api/symbols")
async def symbols():
    """Danh sách mã cho ô gợi ý tìm kiếm (HOSE, HNX, UPCoM) lấy từ CafeF."""
    try:
        return await cafef.company_list()
    except (httpx.HTTPError, ValueError) as e:
        raise HTTPException(502, f"Không lấy được danh sách mã từ CafeF: {type(e).__name__}")


@app.get("/api/analyze/{symbol}")
async def analyze(symbol: str):
    symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{3,10}", symbol):
        raise HTTPException(400, "Mã cổ phiếu không hợp lệ")
    hit = _cache.get(symbol)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        raw = await cafef.fetch_all(symbol)
    except cafef.CafeFError as e:
        raise HTTPException(404, str(e))
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Không kết nối được CafeF: {type(e).__name__}")
    if not raw["income"]:
        raise HTTPException(404, f"Không có báo cáo tài chính cho mã {symbol}")
    data = build(symbol, raw)
    _cache[symbol] = (time.time(), data)
    return data
