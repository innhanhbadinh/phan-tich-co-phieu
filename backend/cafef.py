"""Lấy dữ liệu cổ phiếu từ CafeF (cafef.vn/du-lieu).

Đơn vị CafeF trả về:
- PriceHistory / PriceRealTimeHeader: giá tính bằng NGHÌN đồng (58.3 = 58.300 đ)
- FinanceReport (JSON): giá trị tính bằng NGHÌN đồng
- Trang báo cáo tài chính HTML: giá trị tính bằng ĐỒNG
"""
import re
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

BASE = "https://cafef.vn/du-lieu"
AJAX = BASE + "/Ajax/PageNew"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, text/html, */*; q=0.01",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://cafef.vn/du-lieu.chn",
    "X-Requested-With": "XMLHttpRequest",
}

VN_TZ = timezone(timedelta(hours=7))


class CafeFError(Exception):
    pass


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True)


async def _get_json(client, url, params):
    r = await client.get(url, params=params)
    if r.status_code != 200:
        raise CafeFError(f"CafeF trả về mã {r.status_code} cho {url.rsplit('/', 1)[-1]}")
    try:
        return r.json()
    except ValueError:
        raise CafeFError(f"CafeF không trả JSON cho {url.rsplit('/', 1)[-1]} (có thể bị chặn)")


def _num(s):
    """'1,885,727,648' -> 1885727648.0 ; '9.94' -> 9.94 ; '' -> None"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = re.sub(r"<[^>]+>", "", str(s)).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _vn_num(s):
    """Số kiểu Việt Nam trên trang HTML: '1.144.217.283.327' hoặc '(1.234)' -> float, '' -> None"""
    s = (s or "").strip()
    if not s or s in ("-", "--"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _ms_date(s):
    """'/Date(1789923600000)/' -> date"""
    m = re.search(r"(-?\d+)", s or "")
    if not m:
        return None
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=VN_TZ).date()


# ---------------------------------------------------------------- giá

async def price_history(client, symbol, max_pages=12):
    """Khoảng 1 năm giao dịch gần nhất (CafeF giới hạn 30 dòng/trang). Trả về list tăng dần theo ngày."""
    url = AJAX + "/DataHistory/PriceHistory.ashx"
    rows, total = [], None
    for page in range(1, max_pages + 1):
        j = await _get_json(client, url, {
            "Symbol": symbol, "StartDate": "", "EndDate": "", "PageIndex": page, "PageSize": 30,
        })
        data = (j or {}).get("Data") or {}
        total = data.get("TotalCount") or 0
        chunk = data.get("Data") or []
        rows.extend(chunk)
        if not chunk or len(rows) >= total:
            break
    if not rows:
        raise CafeFError(f"Không có dữ liệu giá cho mã {symbol}")

    bars = {}
    for x in rows:
        try:
            d = datetime.strptime(x["Ngay"], "%d/%m/%Y").date()
        except (KeyError, ValueError):
            continue
        close_raw = _num(x.get("GiaDongCua"))
        close_adj = _num(x.get("GiaDieuChinh")) or close_raw
        if not close_raw or not close_adj:
            continue
        k = close_adj / close_raw  # hệ số điều chỉnh (chia tách, thưởng, cổ tức)
        o = _num(x.get("GiaMoCua")) or close_raw
        h = _num(x.get("GiaCaoNhat")) or max(o, close_raw)
        lo = _num(x.get("GiaThapNhat")) or min(o, close_raw)
        bars[d] = {
            "time": d.isoformat(),
            "open": round(o * k * 1000, 1),
            "high": round(h * k * 1000, 1),
            "low": round(lo * k * 1000, 1),
            "close": round(close_adj * 1000, 1),
            "volume": int(_num(x.get("KhoiLuongKhopLenh")) or 0),
        }
    return [bars[d] for d in sorted(bars)]


async def realtime_price(client, symbol):
    j = await _get_json(client, AJAX + "/PriceRealTimeHeader.ashx", {"Symbol": symbol})
    data = (j or {}).get("Data") or {}
    gia = _num(data.get("Gia"))
    ref = _num(data.get("GiaThamChieu"))
    return {
        "price": gia * 1000 if gia else None,
        "ref_price": ref * 1000 if ref else None,
        "time": _ms_date(data.get("ThoiGian")).isoformat() if data.get("ThoiGian") else None,
    }


# ---------------------------------------------------------------- báo cáo tài chính (JSON)

async def finance_report(client, symbol, rtype, rows=20):
    """rtype=1: kết quả kinh doanh, rtype=2: cân đối kế toán. Theo quý, mới nhất trước."""
    j = await _get_json(client, AJAX + "/FinanceReport.ashx", {
        "Type": rtype, "Symbol": symbol, "TotalRow": rows,
        "EndDate": "4-2099", "ReportType": "QUY", "Sort": "DESC",
    })
    out = []
    for p in ((j or {}).get("Data") or {}).get("Value") or []:
        out.append({
            "time": p.get("Time"),
            "year": p.get("Year"),
            "quarter": p.get("Quater"),
            "values": {v.get("Code"): _num(v.get("Value")) for v in p.get("Value") or []},
            "names": {v.get("Code"): v.get("Name") for v in p.get("Value") or []},
        })
    return out


async def ratios(client, symbol):
    j = await _get_json(client, AJAX + "/ChiSoTaiChinh.ashx", {"Symbol": symbol})
    out = {}
    for d in (j or {}).get("Data") or []:
        out[d.get("Code")] = d.get("Value")
    return out


async def events(client, symbol):
    j = await _get_json(client, AJAX + "/LichSuKien.ashx", {"Symbol": symbol})
    out = []
    for d in (j or {}).get("Data") or []:
        dt = _ms_date(d.get("Time"))
        if dt:
            out.append({"date": dt, "texts": d.get("Text") or []})
    return out


# ---------------------------------------------------------------- lợi ích cổ đông không kiểm soát (HTML)

async def minority_interest(client, symbol, year, quarter):
    """Lợi ích cổ đông không kiểm soát (đồng) tại quý (year, quarter). None nếu không đọc được."""
    url = f"{BASE}/bao-cao-tai-chinh/{symbol.lower()}/bsheet/{year}/{quarter}/0/0/bao-cao-tai-chinh-.chn"
    r = await client.get(url, headers={"Accept": "text/html"})
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(cells) > 2:
            rows.append(cells)
    header = next((c for c in rows if any(re.search(r"Quý\s*\d", x) for x in c)), None)
    target = f"Quý{quarter}-{year}"
    col = None
    if header:
        for i, h in enumerate(header):
            if re.sub(r"\s+", "", h) == target:
                col = i
    for c in rows:
        if re.search(r"không kiểm soát|thiểu số", c[0], re.I):
            if col is not None and col < len(c):
                v = _vn_num(c[col])
            else:  # không thấy tiêu đề → lấy ô số cuối cùng
                nums = [_vn_num(x) for x in c[1:] if _vn_num(x) is not None]
                v = nums[-1] if nums else None
            return v if v is not None else 0.0
    return None


# ---------------------------------------------------------------- tổng hợp

def cash_dividend_rate(evts, today=None):
    """Tổng tỷ lệ cổ tức tiền mặt (theo mệnh giá) trong 365 ngày gần nhất. 10% -> 0.10"""
    today = today or datetime.now(VN_TZ).date()
    start = today - timedelta(days=365)
    total, used = 0.0, []
    for e in evts:
        if not (start <= e["date"] <= today):
            continue
        for t in e["texts"]:
            if "tiền" not in t.lower():
                continue
            m = re.search(r"tỷ lệ\s*([\d.,]+)\s*%", t, re.I)
            if m:
                rate = float(m.group(1).replace(",", ".")) / 100
            else:
                m = re.search(r"([\d.,]+)\s*đ(ồng)?\s*/\s*c", t, re.I)
                if not m:
                    continue
                rate = float(m.group(1).replace(".", "").replace(",", ".")) / 10000
            total += rate
            used.append({"date": e["date"].isoformat(), "text": t, "rate": rate})
    return round(total, 4), used


async def fetch_all(symbol):
    symbol = symbol.upper()
    async with make_client() as c:
        bars, rt, inc, bs, rat, evts = await asyncio.gather(
            price_history(c, symbol),
            realtime_price(c, symbol),
            finance_report(c, symbol, 1, 20),
            finance_report(c, symbol, 2, 4),
            ratios(c, symbol),
            events(c, symbol),
        )
        mi = None
        if bs:
            try:
                mi = await minority_interest(c, symbol, bs[0]["year"], bs[0]["quarter"])
            except httpx.HTTPError:
                mi = None
    return {"bars": bars, "realtime": rt, "income": inc, "balance": bs,
            "ratios": rat, "events": evts, "minority_vnd": mi}
