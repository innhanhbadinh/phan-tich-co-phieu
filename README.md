# Công cụ phân tích & định giá cổ phiếu (dữ liệu CafeF)

Gõ mã cổ phiếu → tool tự lấy dữ liệu từ CafeF, tính **định giá CI Highest** (giống file Excel) và **phân tích kỹ thuật**.

```
backend/   → FastAPI, chạy trên Render (Root Directory = backend)
docs/      → index.html, chạy trên GitHub Pages (Settings → Pages → /docs)
```

- Web: https://innhanhbadinh.github.io/phan-tich-co-phieu/
- API: https://phan-tich-co-phieu.onrender.com/api/analyze/FPT

## 1. Deploy backend lên Render

1. Tạo repo GitHub mới (ví dụ `phan-tich-co-phieu-api`), kéo-thả 5 file trong thư mục `backend/` vào repo.
2. Vào Render → **New → Web Service** → chọn repo vừa tạo.
3. Điền:
   - Runtime: **Python**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free
4. Deploy xong, mở `https://<tên-service>.onrender.com/api/analyze/FPT` để kiểm tra — phải ra JSON.

## 2. Deploy giao diện lên GitHub Pages

1. Mở `frontend/index.html`, sửa dòng:
   ```js
   const API_BASE = "https://phan-tich-co-phieu.onrender.com";
   ```
   thành địa chỉ Render của bạn (không có dấu `/` ở cuối).
2. Kéo-thả `index.html` vào repo GitHub Pages (repo cũ hoặc repo mới), bật Pages.
3. Mở trang, gõ mã cổ phiếu → **Phân tích**. Có thể mở thẳng `.../index.html#HPG`.

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
