# Công cụ phân tích & định giá cổ phiếu (dữ liệu CafeF)

Gõ mã cổ phiếu → tool tự lấy dữ liệu từ CafeF, tính **định giá CI Highest** (giống file Excel) và **phân tích kỹ thuật**.

```
backend/   → FastAPI, chạy trên Render (Root Directory = backend)
docs/      → index.html, chạy trên GitHub Pages (Settings → Pages → /docs)
```

- Web: https://innhanhbadinh.github.io/phan-tich-co-phieu/
- API: https://phan-tich-co-phieu-api.onrender.com/api/analyze/FPT

## Cách deploy đang dùng

- **Render** (service `phan-tich-co-phieu-api`, Python 3, Free, Singapore): Root Directory `backend`,
  Build `pip install -r requirements.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
  Mỗi lần commit file trong `backend/` Render tự deploy lại.
- **GitHub Pages**: Settings → Pages → nhánh `main`, thư mục `/docs`.
  `API_BASE` trong `docs/index.html` trỏ tới địa chỉ Render ở trên.

## Các phần trên trang

1. **Định giá CI Highest** — giống file Excel, sửa được đầu vào.
2. **Kết luận kỹ thuật** — điểm −100…+100 tổng hợp xu hướng, MA, chỉ báo dao động, MACD, RSI, ADX, OBV, Bollinger
   → Mua mạnh / Mua / Theo dõi / Bán / Bán mạnh, kèm lý do và hỗ trợ/kháng cự gần nhất.
3. **Tiêu chí SS** — theo sheet "SS Các Tiêu Chí": TL gộp ≥ 15%, ROE ≥ 7%, P/B < 2, P/E ≤ 10, CORE,
   BEST (ROE ≥ 20% và $$$ ≥ 50%), BUY, IN, TREND → số tiêu chí đạt /9.
4. Điều kiện doanh nghiệp tốt, dữ liệu CafeF, biểu đồ và bảng chỉ báo.

## Dữ liệu lấy từ CafeF

| Đầu vào | Nguồn CafeF |
|---|---|
| LNST 4 quý | `FinanceReport.ashx` (Type=1) — LNST cổ đông công ty mẹ |
| Vốn chủ sở hữu | `FinanceReport.ashx` (Type=2) trừ *Lợi ích cổ đông không kiểm soát* (trang báo cáo tài chính) |
| Tỷ lệ cổ tức | `LichSuKien.ashx` — cộng cổ tức tiền mặt trong 12 tháng gần nhất |
| Thị giá | `PriceRealTimeHeader.ashx` |
| Số CP lưu hành | `ChiSoTaiChinh.ashx` |
| Lịch sử giá ~1 năm | `PriceHistory.ashx` (giá điều chỉnh) |

Tất cả đầu vào đều sửa tay được trên giao diện, kết quả tính lại ngay.

## Lưu ý

- Render gói miễn phí "ngủ" sau 15 phút không dùng — lần gọi đầu mất khoảng 50 giây. Kết quả mỗi mã được lưu đệm 10 phút.
- CafeF có thể đổi cấu trúc API hoặc chặn máy chủ nước ngoài. Nếu báo lỗi kết nối, xem log trên Render; có thể cần đổi sang máy chủ ở Việt Nam/Singapore (Render có region Singapore).
- Công thức CI Highest giả định lợi nhuận đi ngang 10 năm, nên thường định giá thấp doanh nghiệp tăng trưởng nhanh.
