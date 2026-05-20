# 🚀 Hướng dẫn nhanh - ERP Bot (Non-blocking)

## Cách 1: Tạo Shortcut trên Desktop

### Bước 1: Chạy lệnh
```powershell
py create_shortcut_simple.py
```

### Bước 2: Double-click file `temp_shortcut.vbs`
Shortcut "ERP Bot" sẽ xuất hiện trên Desktop

## Cách 2: Chạy trực tiếp

### Dùng file BAT (có prompt)
```powershell
launch_bot.bat
```
Sau đó nhập email và URL khi được hỏi.

### Dùng Python CLI (không prompt)
```powershell
py bot_erp_cli.py <email> <url>
```

**Ví dụ:**
```powershell
py bot_erp_cli.py influencer@gmail.com https://erp.example.com
```

## Các file quan trọng

- `bot_erp_cli.py` - Bot chính (CLI, tự thoát)
- `launch_bot.bat` - Batch file để chạy nhanh
- `create_shortcut_simple.py` - Tạo shortcut (không blocking)
- `temp_shortcut.vbs` - VBScript để tạo shortcut Desktop

## Lưu ý

✅ Tất cả scripts đều TỰ ĐỘNG THOÁT sau khi hoàn thành
✅ Không có blocking calls (input, mainloop, subprocess wait)
✅ Chỉ dùng thư viện Python mặc định + playwright

## Quy trình hoạt động

1. Đọc email từ Gmail (IMAP)
2. Trích xuất số điện thoại + link YouTube
3. Mở browser ERP
4. Điền form tự động
5. Chờ 30s để user kiểm tra
6. Tự động đóng và exit
