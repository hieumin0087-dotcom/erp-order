# 🚀 Quy Trình Tự Động Hóa Xử Lý Đơn Hàng Influencer (Chi Tiết Kỹ Thuật)

Tài liệu này cung cấp cái nhìn chuyên sâu vào cơ chế vận hành của bot, từ khâu nhận diện dữ liệu cho đến khi điền hoàn tất trên website ERP.

---

## 🔁 Chi Tiết Từng Bước Trong Luồng Tự Động (One-Click Flow)

### Bước 1: Tiếp Nhận Email Đầu Vào
*   **Giao diện:** Ô nhập liệu `Auto-fill from Email` tại mục `Delivery Information`.
*   **Kích hoạt:** Sau khi bạn nhập email và nhấn **Enter** hoặc nút **Read Email**, bot sẽ tách riêng một tiến trình (thread) độc lập. Điều này giúp phần mềm vẫn mượt mà, bạn vẫn có thể cuộn chuột hoặc sửa các ô khác trong khi bot đang xử lý ngầm.

### Bước 2: Truy Xuất & Làm Sạch Nội Dung Email
*   **Kết nối IMAP:** Bot đăng nhập vào Gmail thông qua giao thức bảo mật APP PASSWORD. Nó tìm kiếm tất cả các thư có địa chỉ người gửi hoặc nội dung liên quan đến email bạn vừa nhập.
*   **Dọn dẹp BeautifulSoup:** Nội dung mail (thường chứa rất nhiều mã HTML, CSS rác từ các bảng biểu) được xử lý qua bộ lọc BeautifulSoup. Kết quả là một đoạn văn bản thuần túy (Plain Text) sạch sẽ, giúp AI đọc hiểu chính xác hơn và tiết kiệm "token" (chi phí/giới hạn của AI).

### Bước 3: Phân Tích Thông Tin Bằng AI (Gemini Flash / Groq)
*   **Cấu trúc Prompt:** Bot gửi nội dung mail sạch cho AI với các chỉ thị nghiêm ngặt: "Tìm tên, số điện thoại, địa chỉ, tỉnh thành, mã zip và link sản phẩm".
*   **Cơ chế Cứu hộ JSON:** AI đôi khi trả về kết quả bị thiếu hoặc sai định dạng. Bot đã được lập trình sẵn một bộ lọc **Regex Fallback**. Nếu định dạng JSON lỗi, bot sẽ tự dùng các mẫu biểu thức chính quy (Regular Expressions) để nhặt lại từng trường thông tin (tên, sđt...) từ văn bản thô.

### Bước 4: Đồng Bộ Hóa Field Thông Minh (Smart Sync)
*   **Sync Email:** Ngay sau khi đọc xong mail, bot lấy địa chỉ email đó điền ngược lên ô `Contact Information` và `Contact Email` (phía đỉnh form).
*   **Tiết kiệm thao tác:** Bạn không cần phải copy email từ dưới lên trên nữa.

### Bước 5: Tra Cứu Google Sheet & Social Scraper
*   **Lookup GSheet:** Bot dùng ID bảng tính `1Lx1hyB59VHuLPJBuf_908XIDyhF-JoFG2l95q2Zp0k4`. Nó sẽ quét qua 2 Tab (GID: 1162923450 và 517784804).
*   **Tìm link Social:** Nếu email khớp với bất kỳ dòng nào trong bảng, bot lấy Link YouTube/TikTok ở Cột G.
*   **Social Scraper (Playwright):** Bot mở trình duyệt ẩn, truy cập link social để lấy:
    *   **Channel Name:** Điền vào ô Kênh và đồng bộ lên ô `Nickname` ở đỉnh form.
    *   **Followers:** Tự động định dạng lại (ví dụ: 13.4K -> 13.4 và chọn đơn vị K).
    *   **Avatar:** Tải ảnh đại diện về máy để chuẩn bị upload lên ERP.

### Bước 6: Product Scraper Đa Nền Tảng (Generalized Scraper)
*   **Nhận diện Link:** Bot hỗ trợ mọi tên miền (colestore.ru, tikhubs.ru, bags-store.ru...).
*   **Tên & Brand:** Quét thẻ `<h1>` để lấy tên sản phẩm.
*   **Tách Brand thông minh:** Bot trích xuất tên shop từ URL (ví dụ: `colestore`). Nếu tên sản phẩm là "Colestore Louis Vuitton...", bot sẽ tự cắt bỏ chữ "Colestore" và lấy "**Louis Vuitton**" điền vào ô Brand.
*   **Hình ảnh:** Bot tự tìm các ảnh chất lượng cao (HQ), tải 4 ảnh về thư mục `product_images`.

### Bước 7: Điền Dữ Liệu Lên Website ERP (Selenium/Playwright)
Đây là bước phức tạp nhất, diễn ra khi bạn nhấn **Save Data** và xác nhận **OK**.

1.  **Khởi tạo trình duyệt:** Bot mở Chrome với Profile cá nhân (`C:/erp_profile`) để duy trì trạng thái đăng nhập, bạn không cần đăng nhập lại mỗi lần chạy.
2.  **Điều hướng:** Tự động truy cập trang tạo đơn: `https://erp.bx123.pro/celebrityOrder/save`.
3.  **Điền Influencer Info:**
    *   `Nickname`: Điền vào ID `#screenName`.
    *   `Contact Info`: Điền vào ID `#contact`.
    *   `Contact Type`: Chọn từ dropdown `#contactType` (1: WhatsApp, 2: Email, 6: TikTok...).
    *   `Cooperation Date`: Nhấp vào `#cooperationTime`, tự động click nút "Now" hoặc chọn ngày hiện tại.
    *   `Quality`: Chọn từ dropdown `#quality` (0: Unknown, 2: High...).
    *   `Avatar`: Đưa đường dẫn file ảnh influencer vào `#avatarUploader` và kích hoạt nút `#ctlBtn` để upload lên server ERP.
4.  **Điền Social Information:**
    *   Nhấn nút `Add social information` (`#addCelebritySocial`).
    *   Điền Platform, Social ID, Link và Follower vào các ô có cấu trúc mảng (ví dụ: `socialList[0].socialFans`).
5.  **Điền Delivery Information:**
    *   Tên: `#consignee`.
    *   SDT: `#phone`.
    *   Quốc gia: Dropdown `#country` (Tự động map US, CA, GB, VN...).
    *   Địa chỉ: Điền Bang/Tỉnh, Thành phố và địa chỉ chi tiết vào các ô tương ứng.
6.  **Điền Product Information:**
    *   Link: `#goodsUrl`.
    *   Tên: `#goodsName`.
    *   Hãng: `#goodsBrand`.
    *   Phân loại: Dropdown `#goodsType`.
    *   SKU/Size: `#goodsSku`.
    *   **Upload Ảnh SP:** Đưa ảnh chính vào `#goodsPosterUploader`, đưa 3 ảnh chi tiết vào `#goodsPictureUploader`. Bot đợi vài giây để hệ thống ERP xử lý ảnh xong.
7.  **Ghi chú:** Điền vào textarea `#effectNote`.
8.  **Hoàn tất:** Bot hiện thông báo bạn kiểm tra lại lần cuối và nhấn **SUBMIT** thủ công để đảm bảo tính an toàn.

---

## ⚠️ Các Lưu Ý Quan Trọng
- **Trạng thái mạng:** Nếu mạng chậm, bot đã được thiết lập các khoảng nghỉ `wait_for_timeout` từ 2-5 giây để đợi website ERP truyền tải dữ liệu.
- **Quyền truy cập GSheet:** Phải luôn đảm bảo bảng tính được để chế độ "Bất kỳ ai có đường liên kết đều có thể xem".
- **Tính năng vá lỗi:** Nếu một bước cào dữ liệu thất bại, bot sẽ bỏ qua bước đó và vẫn điền các phần khác thay vì dừng hẳn toàn bộ quy trình.
