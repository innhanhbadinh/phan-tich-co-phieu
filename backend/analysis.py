"""Định giá CI Highest (giống file Excel) và phân tích kỹ thuật."""
import math

# ====================================================================== ĐỊNH GIÁ CI HIGHEST

DISCOUNT = 0.07      # "Lạm phát (%)" trong file Excel
HAIRCUT = 0.314      # hệ số (1 - 0.1*3.14)
YEARS = 10


def _pv_10y(profit, r=DISCOUNT, years=YEARS):
    return sum(profit / (1 + r) ** t for t in range(1, years + 1))


def ci_value(profit, equity, shares_m, r=DISCOUNT, haircut=HAIRCUT):
    """Giá trị thực / cp (đồng). profit, equity: tỷ đồng; shares_m: triệu cp."""
    total = (_pv_10y(profit, r) + equity) * (1 - haircut)
    return total * 1e9 / (shares_m * 1e6), total


def ci_highest(profit, equity, dividend_rate, price, shares_m, r=DISCOUNT, haircut=HAIRCUT):
    """Tái hiện Sheet1 của file 'Định giá CI Lv5 - Highest'."""
    v0, total0 = ci_value(profit, equity, shares_m, r, haircut)
    # Sau 1 năm (Sheet1!C24:C41)
    div_paid = dividend_rate * 10 * shares_m              # tỷ đồng
    retained = profit - div_paid
    equity1 = equity + retained
    roe = profit / equity if equity else 0
    profit1 = profit + roe * retained
    v1, total1 = ci_value(profit1, equity1, shares_m, r, haircut)

    lai_von = v0 / price - 1 if price else None
    dong_tien = 0.95 * dividend_rate * 10000 / price if price else None
    tang_gt = v1 / v0 - 1 if v0 else None
    tong = None if None in (lai_von, dong_tien, tang_gt) else lai_von + dong_tien + tang_gt
    return {
        "gia_tri_thuc": v0,
        "tong_gia_tri_dn": total0,
        "gia_tri_sau_1_nam": v1,
        "lai_von": lai_von,
        "dong_tien": dong_tien,
        "tang_gia_tri": tang_gt,
        "tong_loi_ich": tong,
        "chi_tiet": {
            "co_tuc_chi_tra": div_paid, "loi_nhuan_giu_lai": retained, "roe": roe,
            "von_csh_sau_1_nam": equity1, "loi_nhuan_moi": profit1,
            "chiet_khau": r, "he_so_an_toan": haircut,
        },
    }


# ====================================================================== CHẤT LƯỢNG DOANH NGHIỆP

def quality_checks(income, profit_ttm, equity, lai_von):
    """Các điều kiện trong sheet HƯỚNG DẪN của file Excel."""
    out = []
    last4 = income[:4]
    rev = sum((q["values"].get("DTTBHCCDV") or 0) for q in last4)
    gp = sum((q["values"].get("LNGBHCCDV") or 0) for q in last4)
    if rev > 0 and any("LNGBHCCDV" in q["values"] for q in last4):
        gm = gp / rev
        out.append({"ten": "Tỷ lệ lãi gộp > 15%", "gia_tri": gm, "dat": gm > 0.15,
                    "ghi_chu": f"Lãi gộp 4 quý gần nhất {gm:.1%}"})
    else:
        out.append({"ten": "Tỷ lệ lãi gộp > 15%", "gia_tri": None, "dat": None,
                    "ghi_chu": "Không áp dụng (ngân hàng / bảo hiểm / chứng khoán)"})

    roe = profit_ttm / equity if equity else None
    if roe is not None:
        out.append({"ten": "ROE > 7% (tốt nhất > 20%)", "gia_tri": roe, "dat": roe > 0.07,
                    "ghi_chu": f"ROE {roe:.1%}" + (" — rất tốt" if roe > 0.20 else "")})

    # Lợi nhuận theo năm (từ các quý) — 5 năm gần nhất có đủ 4 quý
    years = {}
    for q in income:
        y = q.get("year")
        ni = q["values"].get("NetIncome")
        if y is None or ni is None:
            continue
        years.setdefault(y, []).append(ni)
    full = sorted((y, sum(v) / 1e6) for y, v in years.items() if len(v) == 4)[-5:]
    if len(full) >= 3:
        ups = sum(1 for a, b in zip(full, full[1:]) if b[1] >= a[1])
        neg = any(v <= 0 for _, v in full)
        ok = (not neg) and ups >= len(full) - 2 and full[-1][1] >= full[0][1]
        cagr = (full[-1][1] / full[0][1]) ** (1 / (len(full) - 1)) - 1 if full[0][1] > 0 and full[-1][1] > 0 else None
        txt = ", ".join(f"{y}: {v:,.0f}" for y, v in full) + " tỷ"
        if cagr is not None:
            txt += f" (tăng bình quân {cagr:.1%}/năm)"
        out.append({"ten": "Lợi nhuận ổn định, tăng trưởng", "gia_tri": cagr, "dat": ok, "ghi_chu": txt,
                    "theo_nam": [{"nam": y, "loi_nhuan": v} for y, v in full]})
    else:
        out.append({"ten": "Lợi nhuận ổn định, tăng trưởng", "gia_tri": None, "dat": None,
                    "ghi_chu": "Không đủ dữ liệu năm"})

    if lai_von is not None:
        out.append({"ten": "Lãi vốn không quá 50%", "gia_tri": lai_von, "dat": lai_von <= 0.5,
                    "ghi_chu": "Lãi vốn > 50%: cần xem xét kỹ, có thể là DN nhỏ nhiều rủi ro"
                    if lai_von > 0.5 else f"Lãi vốn {lai_von:.1%}"})
    return out


# ====================================================================== PHÂN TÍCH KỸ THUẬT

def sma(xs, n):
    out = [None] * len(xs)
    s = 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(xs, n):
    out = [None] * len(xs)
    if len(xs) < n:
        return out
    k = 2 / (n + 1)
    e = sum(xs[:n]) / n
    out[n - 1] = e
    for i in range(n, len(xs)):
        e = xs[i] * k + e * (1 - k)
        out[i] = e
    return out


def _wilder(xs, n):
    out = [None] * len(xs)
    if len(xs) < n:
        return out
    a = sum(xs[:n]) / n
    out[n - 1] = a
    for i in range(n, len(xs)):
        a = (a * (n - 1) + xs[i]) / n
        out[i] = a
    return out


def rsi(closes, n=14):
    gains = [0.0] + [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [0.0] + [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    ag, al = _wilder(gains[1:], n), _wilder(losses[1:], n)
    out = [None]
    for g, l in zip(ag, al):
        if g is None:
            out.append(None)
        else:
            out.append(100.0 if l == 0 else 100 - 100 / (1 + g / l))
    return out


def macd(closes, fast=12, slow=26, sig=9):
    ef, es = ema(closes, fast), ema(closes, slow)
    line = [a - b if a is not None and b is not None else None for a, b in zip(ef, es)]
    valid = [x for x in line if x is not None]
    s = ema(valid, sig)
    signal = [None] * (len(line) - len(valid)) + s
    hist = [a - b if a is not None and b is not None else None for a, b in zip(line, signal)]
    return line, signal, hist


def stochastic(h, l, c, k=9, smooth=6):
    raw = [None] * len(c)
    for i in range(k - 1, len(c)):
        hh, ll = max(h[i - k + 1:i + 1]), min(l[i - k + 1:i + 1])
        raw[i] = 50.0 if hh == ll else (c[i] - ll) / (hh - ll) * 100
    valid = [x for x in raw if x is not None]
    sm = sma(valid, smooth)
    return [None] * (len(raw) - len(valid)) + sm


def williams_r(h, l, c, n=14):
    out = [None] * len(c)
    for i in range(n - 1, len(c)):
        hh, ll = max(h[i - n + 1:i + 1]), min(l[i - n + 1:i + 1])
        out[i] = -50.0 if hh == ll else (hh - c[i]) / (hh - ll) * -100
    return out


def cci(h, l, c, n=14):
    tp = [(a + b + d) / 3 for a, b, d in zip(h, l, c)]
    out = [None] * len(c)
    for i in range(n - 1, len(c)):
        w = tp[i - n + 1:i + 1]
        m = sum(w) / n
        md = sum(abs(x - m) for x in w) / n
        out[i] = 0.0 if md == 0 else (tp[i] - m) / (0.015 * md)
    return out


def adx(h, l, c, n=14):
    tr, pdm, mdm = [], [], []
    for i in range(1, len(c)):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
        tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    atr_, p_, m_ = _wilder(tr, n), _wilder(pdm, n), _wilder(mdm, n)
    pdi, mdi, dx = [], [], []
    for a, p, m in zip(atr_, p_, m_):
        if a is None or a == 0:
            pdi.append(None); mdi.append(None); dx.append(None)
            continue
        P, M = 100 * p / a, 100 * m / a
        pdi.append(P); mdi.append(M)
        dx.append(0.0 if P + M == 0 else 100 * abs(P - M) / (P + M))
    dxv = [x for x in dx if x is not None]
    ad = _wilder(dxv, n)
    ad = [None] * (len(dx) - len(dxv)) + ad
    return [None] + ad, [None] + pdi, [None] + mdi, [None] + atr_


def _last(xs):
    for x in reversed(xs):
        if x is not None:
            return x
    return None


def _sig(name, value, action, note=""):
    return {"ten": name, "gia_tri": value, "tin_hieu": action, "ghi_chu": note}


def _rating(buy, sell, total):
    if total == 0:
        return "Trung tính"
    s = (buy - sell) / total
    if s >= 0.5:
        return "Mua mạnh"
    if s >= 0.1:
        return "Mua"
    if s <= -0.5:
        return "Bán mạnh"
    if s <= -0.1:
        return "Bán"
    return "Trung tính"


def technical(bars, price=None):
    if len(bars) < 30:
        return {"loi": "Không đủ dữ liệu giá để phân tích kỹ thuật"}
    o = [b["open"] for b in bars]
    h = [b["high"] for b in bars]
    l = [b["low"] for b in bars]
    c = [b["close"] for b in bars]
    v = [b["volume"] for b in bars]
    px = price or c[-1]

    # ---- Dao động
    ind = []
    r = _last(rsi(c, 14))
    if r is not None:
        a = "Quá bán" if r < 30 else "Quá mua" if r > 70 else "Bán" if r < 45 else "Mua" if r > 55 else "Trung tính"
        ind.append(_sig("RSI(14)", r, a))
    st = _last(stochastic(h, l, c, 9, 6))
    if st is not None:
        a = "Quá bán" if st < 20 else "Quá mua" if st > 80 else "Bán" if st < 45 else "Mua" if st > 55 else "Trung tính"
        ind.append(_sig("STOCH(9,6)", st, a))
    ml, ms, mh = macd(c)
    if _last(ml) is not None and _last(ms) is not None:
        a = "Mua" if _last(ml) > _last(ms) else "Bán"
        ind.append(_sig("MACD(12,26,9)", _last(ml), a, f"Đường tín hiệu {_last(ms):,.1f}"))
    ad, pdi, mdi, atr_ = adx(h, l, c, 14)
    if _last(ad) is not None:
        A, P, M = _last(ad), _last(pdi), _last(mdi)
        if A < 20:
            a, note = "Trung tính", "Xu hướng yếu / đi ngang"
        else:
            a = "Mua" if P > M else "Bán"
            note = ("Xu hướng mạnh" if A > 25 else "Xu hướng vừa") + (" tăng" if P > M else " giảm")
        ind.append(_sig("ADX(14)", A, a, note + f" (+DI {P:.1f} / −DI {M:.1f})"))
    wr = _last(williams_r(h, l, c, 14))
    if wr is not None:
        a = "Quá bán" if wr < -80 else "Quá mua" if wr > -20 else "Mua" if wr > -50 else "Bán"
        ind.append(_sig("Williams %R", wr, a))
    cc = _last(cci(h, l, c, 14))
    if cc is not None:
        a = "Quá bán" if cc < -200 else "Quá mua" if cc > 200 else "Mua" if cc > 50 else "Bán" if cc < -50 else "Trung tính"
        ind.append(_sig("CCI(14)", cc, a))
    if len(c) > 12:
        roc = (c[-1] / c[-13] - 1) * 100
        ind.append(_sig("ROC(12)", roc, "Mua" if roc > 0 else "Bán", "% thay đổi 12 phiên"))
    at = _last(atr_)
    if at is not None:
        ind.append(_sig("ATR(14)", at, "—", f"Biên độ dao động TB {at / px:.1%}/phiên"))

    # "Quá mua" / "Quá bán" được hiển thị riêng, không tính vào số tín hiệu Mua/Bán
    osc_buy = sum(1 for x in ind if x["tin_hieu"] == "Mua")
    osc_sell = sum(1 for x in ind if x["tin_hieu"] == "Bán")
    osc_total = sum(1 for x in ind if x["tin_hieu"] != "—")

    # ---- Trung bình động
    mas = []
    for n in (5, 10, 20, 50, 100, 200):
        if len(c) < n:
            continue
        s, e = sma(c, n)[-1], ema(c, n)[-1]
        mas.append({"ten": f"MA{n}", "sma": s, "ema": e,
                    "tin_hieu_sma": "Mua" if px > s else "Bán",
                    "tin_hieu_ema": "Mua" if px > e else "Bán"})
    ma_buy = sum((m["tin_hieu_sma"] == "Mua") + (m["tin_hieu_ema"] == "Mua") for m in mas)
    ma_total = 2 * len(mas)
    ma_sell = ma_total - ma_buy

    # ---- Bollinger, khối lượng
    bb = None
    if len(c) >= 20:
        w = c[-20:]
        m = sum(w) / 20
        sd = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
        bb = {"giua": m, "tren": m + 2 * sd, "duoi": m - 2 * sd,
              "vi_tri": (px - (m - 2 * sd)) / (4 * sd) if sd else 0.5}
    vol20 = sum(v[-20:]) / min(20, len(v))
    vol_ratio = v[-1] / vol20 if vol20 else None

    # OBV (On-Balance Volume) — dòng tiền theo khối lượng
    obv = [0.0]
    for i in range(1, len(c)):
        obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0))
    obv_chg20 = obv[-1] - obv[-21] if len(obv) > 20 else None
    prev = v[-80:-20] if len(v) > 40 else []
    vol_prev = sum(prev) / len(prev) if prev else None

    # ---- Pivot cổ điển từ phiên gần nhất
    H, L, C = h[-1], l[-1], c[-1]
    P = (H + L + C) / 3
    pivots = {"S3": L - 2 * (H - P), "S2": P - (H - L), "S1": 2 * P - H, "P": P,
              "R1": 2 * P - L, "R2": P + (H - L), "R3": H + 2 * (P - L)}

    hi52, lo52 = max(h), min(l)
    hi20, lo20 = max(h[-20:]), min(l[-20:])

    # ---- Xu hướng
    s20, s50 = sma(c, 20)[-1], sma(c, 50)[-1] if len(c) >= 50 else None
    s200 = sma(c, 200)[-1] if len(c) >= 200 else None
    if s50 and s200:
        if px > s20 > s50 > s200:
            trend = "Tăng mạnh (giá > MA20 > MA50 > MA200)"
        elif px < s20 < s50 < s200:
            trend = "Giảm mạnh (giá < MA20 < MA50 < MA200)"
        elif px > s200:
            trend = "Tăng dài hạn, đang điều chỉnh / tích lũy" if px < s50 else "Tăng dài hạn"
        else:
            trend = "Giảm dài hạn, đang hồi phục" if px > s50 else "Giảm dài hạn"
    else:
        trend = "Tăng" if s50 and px > s50 else "Giảm" if s50 else "Chưa đủ dữ liệu"

    summary = {
        "dao_dong": {"mua": osc_buy, "ban": osc_sell, "tong": osc_total,
                     "danh_gia": _rating(osc_buy, osc_sell, osc_total)},
        "trung_binh_dong": {"mua": ma_buy, "ban": ma_sell, "tong": ma_total,
                            "danh_gia": _rating(ma_buy, ma_sell, ma_total)},
    }
    tb = osc_buy + ma_buy
    ts = osc_sell + ma_sell
    summary["tong_ket"] = _rating(tb, ts, osc_total + ma_total)

    # ---- 3 tiêu chí kỹ thuật cho sheet "SS Các Tiêu Chí"
    long_ma = s200 or s50
    if long_ma is None or s50 is None:
        trend_ss = {"kq": "-", "ghi_chu": "Chưa đủ dữ liệu"}
    else:
        ma_name = "MA200" if s200 else "MA50"
        if px > long_ma and s20 > s50:
            k = "V"
        elif px < long_ma and s20 < s50:
            k = "X"
        else:
            k = "O"
        trend_ss = {"kq": k, "ghi_chu": f"Giá {'>' if px > long_ma else '<'} {ma_name} ({long_ma:,.0f}); "
                                         f"MA20 {'>' if s20 > s50 else '<'} MA50"}
    tk = summary["tong_ket"]
    buy_ss = {"kq": "V" if tk in ("Mua", "Mua mạnh") else "X" if tk in ("Bán", "Bán mạnh") else "O",
              "ghi_chu": f"Tổng kết kỹ thuật: {tk}"}
    if obv_chg20 is None or not vol_prev:
        in_ss = {"kq": "-", "ghi_chu": "Chưa đủ dữ liệu"}
    else:
        vr = vol20 / vol_prev
        k = "V" if obv_chg20 > 0 and vr >= 1 else "X" if obv_chg20 < 0 else "O"
        in_ss = {"kq": k, "ghi_chu": f"OBV 20 phiên {'tăng' if obv_chg20 > 0 else 'giảm'}; "
                                     f"KL TB 20 phiên = {vr:.2f} lần 60 phiên trước"}
    ss = {"TREND": trend_ss, "BUY": buy_ss, "IN": in_ss}

    # ---- KẾT LUẬN KỸ THUẬT: chấm điểm tổng hợp (-100 … +100)
    pts, pros, cons = [], [], []

    def add(score, maxw, text):
        pts.append((score, maxw))
        if score > 0:
            pros.append(text)
        elif score < 0:
            cons.append(text)

    A = _last(ad)
    amp = 1.5 if A is not None and A > 25 else 1.0          # xu hướng mạnh → tăng trọng số xu hướng
    tw = 2 * amp
    if trend_ss["kq"] == "V":
        add(tw, 3, f"Xu hướng tăng: {trend_ss['ghi_chu']}")
    elif trend_ss["kq"] == "X":
        add(-tw, 3, f"Xu hướng giảm: {trend_ss['ghi_chu']}")
    else:
        add(0, 3, "")
    if ma_total:
        s = (ma_buy - ma_sell) / ma_total * 2
        add(s, 2, f"Giá nằm trên {ma_buy}/{ma_total} đường MA" if s > 0 else f"Giá nằm dưới {ma_sell}/{ma_total} đường MA")
    if osc_total:
        s = (osc_buy - osc_sell) / osc_total * 1.5
        add(s, 1.5, f"Chỉ báo dao động: {osc_buy} mua / {osc_sell} bán")
    mlv, msv = _last(ml), _last(ms)
    hv = [x for x in mh if x is not None]
    if mlv is not None and msv is not None:
        add(1 if mlv > msv else -1, 1, "MACD nằm trên đường tín hiệu" if mlv > msv else "MACD nằm dưới đường tín hiệu")
        if len(hv) >= 2:
            up = hv[-1] > hv[-2]
            add(0.5 if up else -0.5, 0.5, "Động lượng MACD đang cải thiện" if up else "Động lượng MACD đang yếu đi")
    if r is not None:
        if r < 30:
            add(1, 1, f"RSI {r:.0f} quá bán — có thể hồi kỹ thuật")
        elif r > 70:
            add(-1, 1, f"RSI {r:.0f} quá mua — rủi ro điều chỉnh")
        elif r >= 50:
            add(0.5, 1, f"RSI {r:.0f} trên 50 — phe mua chiếm ưu thế")
        else:
            add(-0.5, 1, f"RSI {r:.0f} dưới 50 — phe bán chiếm ưu thế")
    if in_ss["kq"] == "V":
        add(1, 1, f"Dòng tiền vào: {in_ss['ghi_chu']}")
    elif in_ss["kq"] == "X":
        add(-1, 1, f"Dòng tiền ra: {in_ss['ghi_chu']}")
    if bb:
        if px < bb["duoi"]:
            add(0.5, 0.5, "Giá dưới dải Bollinger dưới — vùng quá bán")
        elif px > bb["tren"]:
            add(-0.5, 0.5, "Giá trên dải Bollinger trên — vùng quá mua")
    total_w = sum(w for _, w in pts) or 1
    score = round(sum(s for s, _ in pts) / total_w * 100)
    score = max(-100, min(100, score))
    signal = ("MUA MẠNH" if score >= 40 else "MUA" if score >= 15 else
              "BÁN MẠNH" if score <= -40 else "BÁN" if score <= -15 else "THEO DÕI")

    below = [x for x in (pivots["S1"], pivots["S2"], lo20, bb and bb["duoi"], s50, s200) if x and x < px]
    above = [x for x in (pivots["R1"], pivots["R2"], hi20, bb and bb["tren"], s50, s200) if x and x > px]
    ket_luan = {
        "diem": score, "tin_hieu": signal,
        "ly_do_mua": pros, "ly_do_ban": cons,
        "ho_tro": max(below) if below else None,     # None: giá đang dưới mọi mốc hỗ trợ
        "khang_cu": min(above) if above else None,   # None: giá đang trên mọi mốc kháng cự
        "adx_manh": A is not None and A > 25,
    }

    # ---- Nhận định bằng lời (mô tả, không phải khuyến nghị)
    notes = [f"Xu hướng: {trend}."]
    if r is not None:
        if r < 30:
            notes.append(f"RSI {r:.1f} trong vùng quá bán — có thể hồi kỹ thuật, nhưng quá bán có thể kéo dài khi xu hướng giảm.")
        elif r > 70:
            notes.append(f"RSI {r:.1f} trong vùng quá mua — rủi ro điều chỉnh ngắn hạn tăng.")
        else:
            notes.append(f"RSI {r:.1f} ở vùng trung tính.")
    if _last(ad) is not None:
        notes.append(f"ADX {_last(ad):.1f}: " + ("xu hướng hiện tại mạnh." if _last(ad) > 25 else "xu hướng chưa mạnh."))
    if vol_ratio:
        notes.append(f"Khối lượng phiên gần nhất bằng {vol_ratio:.1f} lần trung bình 20 phiên.")
    notes.append(f"Cách đỉnh 1 năm {px / hi52 - 1:+.1%}, cách đáy 1 năm {px / lo52 - 1:+.1%}.")
    if s200:
        notes.append(("Giá trên" if px > s200 else "Giá dưới") + f" MA200 ({s200:,.0f}) — mốc phân định xu hướng dài hạn.")

    # Chuỗi cho biểu đồ
    times = [b["time"] for b in bars]
    rs = rsi(c, 14)
    series = {
        "ma20": [{"time": t, "value": round(x, 1)} for t, x in zip(times, sma(c, 20)) if x is not None],
        "ma50": [{"time": t, "value": round(x, 1)} for t, x in zip(times, sma(c, 50)) if x is not None],
        "ma200": [{"time": t, "value": round(x, 1)} for t, x in zip(times, sma(c, 200)) if x is not None],
        "rsi": [{"time": t, "value": round(x, 2)} for t, x in zip(times, rs) if x is not None],
        "macd": [{"time": t, "value": round(x, 2)} for t, x in zip(times, ml) if x is not None],
        "macd_signal": [{"time": t, "value": round(x, 2)} for t, x in zip(times, ms) if x is not None],
        "macd_hist": [{"time": t, "value": round(x, 2)} for t, x in zip(times, mh) if x is not None],
    }

    return {
        "gia": px, "xu_huong": trend, "chi_bao": ind, "trung_binh_dong": mas,
        "tong_hop": summary, "pivot": pivots, "bollinger": bb, "kl_so_tb20": vol_ratio,
        "dinh_1_nam": hi52, "day_1_nam": lo52, "dinh_20_phien": hi20, "day_20_phien": lo20,
        "nhan_dinh": notes, "series": series, "so_phien": len(bars), "ss": ss, "ket_luan": ket_luan,
    }
