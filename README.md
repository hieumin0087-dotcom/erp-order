# 🤖 Hướng dẫn sử dụng ERP Bot

## Mô tả
Bot tự động đọc email từ influencer và điền thông tin vào form ERP.

## Yêu cầu hệ thống
- ✅ Python 3.x đã cài đặt
- ✅ Các thư viện: `playwright`, `python-dotenv`, `imaplib` (built-in)
- ✅ Google Chrome

## Cách chạy

### 1. Chạy bot
```bash
py .\bot_erp.py
```

### 2. Nhập thông tin khi được yêu cầu
- **Email người gửi**: Nhập email của influencer (ví dụ: `influencer@example.com`)
- **URL ERP**: Nhập link trang ERP cần điền form

### 3. Theo dõi quá trình
Bot sẽ:
1. 🔗 Kết nối với Gmail
2. 📧 Tìm và đọc tất cả email từ người gửi đã nhập
3. 🔍 Trích xuất số điện thoại (10-12 chữ số) và link YouTube
4. 🌐 Mở trình duyệt Chrome
5. 🔐 Đợi bạn đăng nhập (chỉ lần đầu)
6. 📋 Tự động điều hướng đến form "Influencer orders"
7. 📝 Điền thông tin vào các trường

### 4. Hoàn tất
- Kiểm tra thông tin đã điền
- Nhấn Submit thủ công
- Nhấn Enter trong PowerShell để đóng trình duyệt

## Lưu ý quan trọng
- ⚠️ **Lần đầu chạy**: Bạn cần đăng nhập thủ công vào ERP và xác thực OTP (nếu có)
- 💾 **Lưu session**: Thư mục `user_data` sẽ lưu phiên đăng nhập, lần sau sẽ tự động vào
- 🔐 **Bảo mật**: File `.env` chứa mật khẩu, không chia sẻ với người khác

## Cấu trúc file
```
C:\Trợ lý AI\
├── bot_erp.py         # Mã nguồn chính
├── .env               # Thông tin xác thực
└── user_data/         # Dữ liệu phiên đăng nhập
```

## Xử lý lỗi
- **Không tìm thấy email**: Kiểm tra email người gửi có đúng không
- **Không điền được form**: Bot sẽ để bạn điền thủ công
- **Lỗi đăng nhập**: Xóa thư mục `user_data` và chạy lại

## Liên hệ
Nếu gặp vấn đề, hãy kiểm tra:
1. Credentials trong `.env` có đúng không
2. Python và các thư viện đã cài đặt chưa
3. Kết nối internet ổn định
