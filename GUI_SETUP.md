# 🖥️ Hướng dẫn cài đặt GUI App

## Bước 1: Cài đặt thư viện cần thiết

Mở PowerShell trong thư mục `C:\Trợ lý AI` và chạy:

```powershell
pip install customtkinter
pip install pywin32
pip install winshell
```

## Bước 2: Tạo shortcut trên Desktop

Chạy lệnh sau để tạo icon trên Desktop:

```powershell
py create_shortcut.py
```

## Bước 3: Sử dụng

### Cách 1: Click vào icon "ERP Bot" trên Desktop
- Một cửa sổ chat sẽ hiện ra
- Gõ lệnh và nhấn Enter hoặc nút "Gửi"

### Cách 2: Chạy trực tiếp
```powershell
py bot_gui.py
```

## Các lệnh có thể sử dụng

1. **Đọc email**:
   ```
   Check mail từ influencer@example.com
   ```

2. **Điền form ERP**:
   ```
   Điền form ERP tại https://erp.example.com
   ```

## Giao diện

- **Cửa sổ chat**: Hiển thị hội thoại giữa bạn và bot
- **Ô nhập lệnh**: Nhập các yêu cầu
- **Nút Gửi**: Gửi lệnh cho bot
- **Chế độ tối**: Giao diện hiện đại, dễ nhìn

Bot sẽ tự động:
- Đọc email theo yêu cầu
- Trích xuất dữ liệu
- Mở trình duyệt và điền form

---

**Lưu ý**: Giao diện sử dụng theme tối (dark mode) để trải nghiệm thị giác tốt hơn.
