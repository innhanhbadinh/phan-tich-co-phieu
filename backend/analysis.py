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


def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def _group_rating(score):
    """score -100..100 -> nhãn"""
    return ("Mua mạnh" if score >= 40 else "Mua" if score >= 15 else
            "Bán mạnh" if score <= -40 else "Bán" if score <= -15 else "Trung tính")


def core_signals(c, v, ml, ms, mh, rs):
    """Chấm điểm 3 nhóm chỉ báo chính: Khối lượng (50%), MACD (30%), RSI (20%).
    Mỗi nhóm cho điểm -100..+100; trả thêm danh sách chi tiết và lý do."""
    n = len(c)
    out = {}

    # ================= KHỐI LƯỢNG / THANH KHOẢN =================
    vd, vpros, vcons = [], [], []
    vma = sum(v[-21:-1]) / 20 if n > 21 else (sum(v) / n if n else 0)   # TB 20 phiên trước phiên gần nhất
    chg = c[-1] / c[-2] - 1 if n > 1 and c[-2] else 0.0
    vr1 = v[-1] / vma if vma else None
    vr5 = (sum(v[-5:]) / 5) / vma if vma and n >= 5 else None
    gtgd20 = sum(a * b for a, b in zip(v[-20:], c[-20:])) / min(20, n) / 1e9   # tỷ đồng / phiên
    prev60 = v[-80:-20]
    liq_trend = (sum(v[-20:]) / 20) / (sum(prev60) / len(prev60)) if len(prev60) >= 20 and sum(prev60) else None

    # a) Phiên gần nhất: giá + khối lượng
    a = 0.0
    if vr1 is not None:
        if chg > 0:
            a = 1.0 if vr1 >= 1.5 else 0.6 if vr1 >= 1.0 else 0.2 if vr1 >= 0.7 else 0.0
            txt = (f"Phiên gần nhất tăng {chg:+.1%} với KL {vr1:.1f} lần TB20"
                   + (" — tiền vào mạnh (KL đột biến)" if vr1 >= 1.5 else
                      " — có KL xác nhận" if vr1 >= 1.0 else " — KL thấp, lực mua chưa thuyết phục"))
        elif chg < 0:
            a = -1.0 if vr1 >= 1.5 else -0.6 if vr1 >= 1.0 else -0.2 if vr1 >= 0.7 else 0.0
            txt = (f"Phiên gần nhất giảm {chg:+.1%} với KL {vr1:.1f} lần TB20"
                   + (" — bán tháo / phân phối mạnh" if vr1 >= 1.5 else
                      " — áp lực bán có KL" if vr1 >= 1.0 else " — KL thấp, lực bán yếu (có thể cạn cung)"))
        else:
            txt = f"Phiên gần nhất đứng giá, KL {vr1:.1f} lần TB20"
        vd.append({"ten": "Giá & KL phiên gần nhất", "gia_tri": vr1, "don_vi": "x TB20",
                   "tin_hieu": "Mua" if a > 0.3 else "Bán" if a < -0.3 else "Trung tính", "ghi_chu": txt})
        (vpros if a > 0.3 else vcons if a < -0.3 else []).append(txt)

    # b) Ngày tích lũy / phân phối trong 10 phiên
    acc = dis = 0
    for i in range(max(1, n - 10), n):
        if vma and v[i] > vma:
            if c[i] > c[i - 1]:
                acc += 1
            elif c[i] < c[i - 1]:
                dis += 1
    b = _clamp((acc - dis) / 4)
    txt = f"10 phiên: {acc} phiên tăng có KL lớn (tích lũy), {dis} phiên giảm có KL lớn (phân phối)"
    vd.append({"ten": "Tích lũy / phân phối 10 phiên", "gia_tri": acc - dis, "don_vi": "phiên",
               "tin_hieu": "Mua" if b > 0.2 else "Bán" if b < -0.2 else "Trung tính", "ghi_chu": txt})
    if b > 0.2:
        vpros.append(txt)
    elif b < -0.2:
        vcons.append(txt)

    # c) OBV: hướng dòng tiền và phân kỳ với giá
    obv = [0.0]
    for i in range(1, n):
        obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0))
    cobv = 0.0
    if n > 21:
        obv_up = obv[-1] > obv[-21]
        px_up = c[-1] > c[-21]
        obv_ma = sum(obv[-20:]) / 20
        if obv_up and not px_up:
            cobv, txt = 1.0, "Phân kỳ dương: giá giảm 20 phiên nhưng OBV tăng — dòng tiền vào ngầm"
        elif not obv_up and px_up:
            cobv, txt = -1.0, "Phân kỳ âm: giá tăng 20 phiên nhưng OBV giảm — dòng tiền rút ra"
        elif obv_up:
            cobv = 0.8 if obv[-1] > obv_ma else 0.4
            txt = "OBV tăng 20 phiên — dòng tiền vào cùng chiều giá"
        else:
            cobv = -0.8 if obv[-1] < obv_ma else -0.4
            txt = "OBV giảm 20 phiên — dòng tiền ra cùng chiều giá"
        vd.append({"ten": "OBV (dòng tiền) 20 phiên", "gia_tri": obv[-1] - obv[-21], "don_vi": "cp",
                   "tin_hieu": "Mua" if cobv > 0 else "Bán", "ghi_chu": txt})
        (vpros if cobv > 0 else vcons).append(txt)

    # d) Thanh khoản
    if liq_trend is not None:
        vd.append({"ten": "Thanh khoản 20 phiên so với 60 phiên trước", "gia_tri": liq_trend, "don_vi": "lần",
                   "tin_hieu": "—", "ghi_chu": "Thanh khoản đang " + ("tăng" if liq_trend >= 1.1 else
                                                                     "giảm" if liq_trend <= 0.9 else "ổn định")})
    vd.append({"ten": "Giá trị giao dịch TB 20 phiên", "gia_tri": gtgd20, "don_vi": "tỷ đ",
               "tin_hieu": "—", "ghi_chu": "Thanh khoản thấp — khó mua bán, tín hiệu kỹ thuật kém tin cậy"
               if gtgd20 < 1 else "Thanh khoản trung bình" if gtgd20 < 10 else "Thanh khoản tốt"})

    vol_score = round((0.35 * a + 0.35 * b + 0.30 * cobv) * 100)
    out["khoi_luong"] = {"ten": "Khối lượng", "trong_so": 50, "diem": vol_score,
                         "danh_gia": _group_rating(vol_score), "chi_tiet": vd, "pros": vpros, "cons": vcons}

    # ================= MACD =================
    md, mpros, mcons = [], [], []
    mlv, msv = _last(ml), _last(ms)
    hv = [x for x in mh if x is not None]
    macd_score = 0
    if mlv is not None and msv is not None and len(hv) >= 4:
        # tìm điểm cắt trong 5 phiên gần nhất
        cross, ago = 0, None
        for k in range(1, min(6, len(hv))):
            if hv[-k] > 0 >= hv[-k - 1]:
                cross, ago = 1, k - 1
                break
            if hv[-k] < 0 <= hv[-k - 1]:
                cross, ago = -1, k - 1
                break
        if cross:
            i_cross = n - 1 - ago
            vconf = vma and v[i_cross] >= vma
            base = (0.8 if vconf else 0.5) * cross
            when = "phiên gần nhất" if ago == 0 else f"{ago} phiên trước"
            txt = (f"MACD vừa cắt {'lên' if cross > 0 else 'xuống'} đường tín hiệu ({when})"
                   + (" — có KL xác nhận" if vconf else " — KL chưa xác nhận"))
        else:
            base = 0.5 if mlv > msv else -0.5
            txt = f"MACD nằm {'trên' if mlv > msv else 'dưới'} đường tín hiệu"
        md.append({"ten": "MACD so với đường tín hiệu", "gia_tri": mlv - msv, "don_vi": "",
                   "tin_hieu": "Mua" if base > 0 else "Bán", "ghi_chu": txt + f" (MACD {mlv:,.0f} / tín hiệu {msv:,.0f})"})
        (mpros if base > 0 else mcons).append(txt)

        rising = hv[-1] > hv[-2] > hv[-3]
        falling = hv[-1] < hv[-2] < hv[-3]
        hscore = 0.3 if rising else -0.3 if falling else 0.0
        txt = ("Histogram tăng 3 phiên — động lượng cải thiện" if rising else
               "Histogram giảm 3 phiên — động lượng suy yếu" if falling else "Histogram đi ngang")
        md.append({"ten": "Histogram MACD", "gia_tri": hv[-1], "don_vi": "",
                   "tin_hieu": "Mua" if hscore > 0 else "Bán" if hscore < 0 else "Trung tính", "ghi_chu": txt})
        if hscore > 0:
            mpros.append(txt)
        elif hscore < 0:
            mcons.append(txt)

        zscore = 0.2 if mlv > 0 else -0.2
        txt = "MACD trên 0 — xu hướng trung hạn tăng" if mlv > 0 else "MACD dưới 0 — xu hướng trung hạn giảm"
        md.append({"ten": "MACD so với đường 0", "gia_tri": mlv, "don_vi": "",
                   "tin_hieu": "Mua" if zscore > 0 else "Bán", "ghi_chu": txt})
        macd_score = round(_clamp(base + hscore + zscore) * 100)
    out["macd"] = {"ten": "MACD", "trong_so": 30, "diem": macd_score,
                   "danh_gia": _group_rating(macd_score), "chi_tiet": md, "pros": mpros, "cons": mcons}

    # ================= RSI =================
    rd, rpros, rcons = [], [], []
    rv = [x for x in rs if x is not None]
    rsi_score = 0
    if len(rv) >= 4:
        r, rp = rv[-1], rv[-2]
        if rp < 30 <= r:
            sc, txt = 1.0, f"RSI {r:.1f} vừa thoát vùng quá bán — tín hiệu hồi phục"
        elif r < 30:
            sc, txt = 0.6, f"RSI {r:.1f} quá bán — có thể hồi kỹ thuật (cần KL xác nhận)"
        elif rp > 70 >= r:
            sc, txt = -1.0, f"RSI {r:.1f} vừa rời vùng quá mua — rủi ro điều chỉnh"
        elif r > 70:
            sc, txt = -0.6, f"RSI {r:.1f} quá mua — rủi ro điều chỉnh"
        elif min(rv[-4:-1]) < 50 <= r:
            sc, txt = 0.5, f"RSI {r:.1f} vừa vượt lên 50 — phe mua chiếm ưu thế"
        elif max(rv[-4:-1]) >= 50 > r:
            sc, txt = -0.5, f"RSI {r:.1f} vừa thủng 50 — phe bán chiếm ưu thế"
        elif r >= 50:
            sc, txt = 0.25, f"RSI {r:.1f} trên 50 — phe mua nhỉnh hơn"
        else:
            sc, txt = -0.25, f"RSI {r:.1f} dưới 50 — phe bán nhỉnh hơn"
        rd.append({"ten": "RSI(14)", "gia_tri": r, "don_vi": "",
                   "tin_hieu": "Quá bán" if r < 30 else "Quá mua" if r > 70 else "Mua" if sc > 0 else "Bán",
                   "ghi_chu": txt})
        (rpros if sc > 0 else rcons).append(txt)
        rsi_score = round(sc * 100)
    rlabel = _group_rating(rsi_score)
    if rv and rv[-1] < 30:
        rlabel = "Quá bán"
    elif rv and rv[-1] > 70:
        rlabel = "Quá mua"
    out["rsi"] = {"ten": "RSI", "trong_so": 20, "diem": rsi_score,
                  "danh_gia": rlabel, "chi_tiet": rd, "pros": rpros, "cons": rcons}

    # ================= TỔNG HỢP =================
    total = 0.5 * vol_score + 0.3 * macd_score + 0.2 * rsi_score
    pros = vpros + mpros + rpros
    cons = vcons + mcons + rcons
    warn = []
    # MACD/RSI tích cực nhưng dòng tiền không xác nhận
    if (macd_score > 0 or rsi_score > 0) and vol_score < 0:
        warn.append("Tín hiệu MACD/RSI tích cực nhưng chưa được khối lượng xác nhận")
    if gtgd20 < 1:
        total *= 0.6
        warn.append(f"Thanh khoản thấp (~{gtgd20:,.2f} tỷ đ/phiên): tín hiệu bị giảm 40% độ tin cậy")
    score = int(round(max(-100, min(100, total))))
    signal = ("MUA MẠNH" if score >= 40 else "MUA" if score >= 15 else
              "BÁN MẠNH" if score <= -40 else "BÁN" if score <= -15 else "THEO DÕI")
    return {"diem": score, "tin_hieu": signal, "nhom": out, "ly_do_mua": pros, "ly_do_ban": cons,
            "canh_bao": warn, "gtgd_tb20": gtgd20, "kl_tb20": vma, "kl_so_tb20": vr1, "kl5_so_tb20": vr5}


def technical(bars, price=None):
    if len(bars) < 30:
        return {"loi": "Không đủ dữ liệu giá để phân tích kỹ thuật"}
    o = [b["open"] for b in bars]
    h = [b["high"] for b in bars]
    l = [b["low"] for b in bars]
    c = [b["close"] for b in bars]
    v = [b["volume"] for b in bars]
    px = price or c[-1]

    # ---- Chỉ báo chính
    rs = rsi(c, 14)
    r = _last(rs)
    ml, ms, mh = macd(c)

    # ---- Trung bình động
    mas = []
    for n in (5, 10, 20, 50, 100, 200):
        if len(c) < n:
            continue
        s, e = sma(c, n)[-1], ema(c, n)[-1]
        mas.append({"ten": f"MA{n}", "sma": s, "ema": e,
                    "tin_hieu_sma": "Mua" if px > s else "Bán",
                    "tin_hieu_ema": "Mua" if px > e else "Bán"})

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

    core = core_signals(c, v, ml, ms, mh, rs)
    summary = {k: {"diem": g["diem"], "danh_gia": g["danh_gia"]} for k, g in core["nhom"].items()}
    summary["tong_ket"] = core["tin_hieu"]

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
    tk = core["tin_hieu"]
    buy_ss = {"kq": "V" if tk in ("MUA", "MUA MẠNH") else "X" if tk in ("BÁN", "BÁN MẠNH") else "O",
              "ghi_chu": f"Kết luận kỹ thuật (KL·MACD·RSI): {tk} ({core['diem']:+d})"}
    if obv_chg20 is None or not vol_prev:
        in_ss = {"kq": "-", "ghi_chu": "Chưa đủ dữ liệu"}
    else:
        vr = vol20 / vol_prev
        k = "V" if obv_chg20 > 0 and vr >= 1 else "X" if obv_chg20 < 0 else "O"
        in_ss = {"kq": k, "ghi_chu": f"OBV 20 phiên {'tăng' if obv_chg20 > 0 else 'giảm'}; "
                                     f"KL TB 20 phiên = {vr:.2f} lần 60 phiên trước"}
    ss = {"TREND": trend_ss, "BUY": buy_ss, "IN": in_ss}

    # ---- KẾT LUẬN KỸ THUẬT: Khối lượng 50% · MACD 30% · RSI 20%
    below = [x for x in (pivots["S1"], pivots["S2"], lo20, s50, s200) if x and x < px]
    above = [x for x in (pivots["R1"], pivots["R2"], hi20, s50, s200) if x and x > px]
    ket_luan = dict(core,
                    ho_tro=max(below) if below else None,     # None: giá đang dưới mọi mốc hỗ trợ
                    khang_cu=min(above) if above else None)   # None: giá đang trên mọi mốc kháng cự

    # ---- Nhận định bằng lời (mô tả, không phải khuyến nghị)
    notes = [f"Xu hướng: {trend}."]
    if r is not None:
        if r < 30:
            notes.append(f"RSI {r:.1f} trong vùng quá bán — có thể hồi kỹ thuật, nhưng quá bán có thể kéo dài khi xu hướng giảm.")
        elif r > 70:
            notes.append(f"RSI {r:.1f} trong vùng quá mua — rủi ro điều chỉnh ngắn hạn tăng.")
        else:
            notes.append(f"RSI {r:.1f} ở vùng trung tính.")
    if core["kl_so_tb20"]:
        notes.append(f"Khối lượng phiên gần nhất bằng {core['kl_so_tb20']:.1f} lần trung bình 20 phiên; "
                     f"giá trị giao dịch TB 20 phiên ~{core['gtgd_tb20']:,.1f} tỷ đồng.")
    notes.append(f"Cách đỉnh 1 năm {px / hi52 - 1:+.1%}, cách đáy 1 năm {px / lo52 - 1:+.1%}.")
    if s200:
        notes.append(("Giá trên" if px > s200 else "Giá dưới") + f" MA200 ({s200:,.0f}) — mốc phân định xu hướng dài hạn.")

    # Chuỗi cho biểu đồ
    times = [b["time"] for b in bars]
    series = {
        "vol_ma20": [{"time": t, "value": round(x)} for t, x in zip(times, sma([float(x) for x in v], 20)) if x is not None],
        "ma20": [{"time": t, "value": round(x, 1)} for t, x in zip(times, sma(c, 20)) if x is not None],
        "ma50": [{"time": t, "value": round(x, 1)} for t, x in zip(times, sma(c, 50)) if x is not None],
        "ma200": [{"time": t, "value": round(x, 1)} for t, x in zip(times, sma(c, 200)) if x is not None],
        "rsi": [{"time": t, "value": round(x, 2)} for t, x in zip(times, rs) if x is not None],
        "macd": [{"time": t, "value": round(x, 2)} for t, x in zip(times, ml) if x is not None],
        "macd_signal": [{"time": t, "value": round(x, 2)} for t, x in zip(times, ms) if x is not None],
        "macd_hist": [{"time": t, "value": round(x, 2)} for t, x in zip(times, mh) if x is not None],
    }

    return {
        "gia": px, "xu_huong": trend, "chi_bao": [dict(x, nhom=g["ten"]) for g in core["nhom"].values() for x in g["chi_tiet"]],
        "trung_binh_dong": mas,
        "tong_hop": summary, "pivot": pivots, "bollinger": bb, "kl_so_tb20": vol_ratio,
        "dinh_1_nam": hi52, "day_1_nam": lo52, "dinh_20_phien": hi20, "day_20_phien": lo20,
        "nhan_dinh": notes, "series": series, "so_phien": len(bars), "ss": ss, "ket_luan": ket_luan,
    }
