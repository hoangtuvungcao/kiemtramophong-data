# BÁO CÁO PHÂN TÍCH TOÀN DIỆN API & CƠ SỞ DỮ LIỆU KIEMTRAMOPHONG.COM

Hệ thống **kiemtramophong.com** là nền tảng quản lý thi và ôn tập 120 tình huống mô phỏng lái xe (theo chuẩn Tổng cục Đường bộ Việt Nam), tích hợp giao diện ôn tập 4 câu hỏi nhận biết & xử lý cho từng tình huống, hệ thống phân quyền quản trị trường thi và streaming video an toàn có chữ ký điện tử.

---

## 1. Kiến Trúc & Cơ Chế Xác Thực (Authentication)

Backend của hệ thống được xây dựng trên nền tảng **Laravel (PHP)** kết hợp với **Nginx**:
- **Cơ chế xác thực:** Quản trị và học viên sử dụng cookie phiên chuẩn của Laravel:
  - `kiem_tra_mo_phong_session`: Chứa session payload được mã hóa AES (thông tin user, quyền quản trị viên trung tâm đào tạo lái xe).
  - `remember_web_...`: Cookie "Ghi nhớ đăng nhập" giúp tự động tái xác thực phiên.
  - `XSRF-TOKEN`: Token bảo vệ chống tấn công CSRF.
- **Header bắt buộc:**
  ```http
  Accept: application/json
  User-Agent: Mozilla/5.0 ...
  Cookie: kiem_tra_mo_phong_session=...; remember_web_...=...
  ```

---

## 2. Danh Mục Các API Chính

### 2.1. API Lấy URL Video Có Chữ Ký (Play URL)
- **Endpoint:** `GET https://kiemtramophong.com/simulation/videos/{id}/play-url`
- **Mục đích:** Cấp phát đường dẫn phát video có thời hạn và chữ ký HMAC an toàn cho video tình huống tương ứng (`id` từ `1` đến `120`).
- **Response JSON:**
  ```json
  {
    "url": "https://kiemtramophong.com/simulation/videos/1/stream?expires=1792544085&user=11877&signature=bf1526f73ce01a00b0cf103db30e995bda2655b862038e75864c8fda85b07d62",
    "expires_in": 300
  }
  ```
- **Cơ chế bảo mật:**
  - `expires`: Thời gian hết hạn của link (mặc định 300 giây = 5 phút).
  - `user`: ID của người dùng gọi yêu cầu.
  - `signature`: Chữ ký số HMAC-SHA256 nhằm ngăn chặn chia sẻ link hoặc tải trái phép mà không có session hợp lệ.

### 2.2. API Truyền Tải Video (Stream Video MP4)
- **Endpoint:** `GET https://kiemtramophong.com/simulation/videos/{id}/stream?expires=...&user=...&signature=...`
- **Đặc điểm:**
  - `Content-Type`: `video/mp4`
  - Hỗ trợ Range Requests (`Accept-Ranges: bytes`, status 206 Partial Content) để tua video mượt mà.
  - Dung lượng mỗi video dao động từ 6MB đến 25MB.

### 2.3. API Duy Trì Kết Nối (Heartbeat / Keep-Alive)
- **Endpoint:** `POST https://kiemtramophong.com/online/heartbeat`
- **Payload:** `{"url": "https://kiemtramophong.com/simulation/practice"}`
- **Response:** `{"status": "ok"}`
- **Mục đích:** Gửi định kỳ (mỗi 30 - 60 giây) từ trình duyệt để thông báo học viên đang online và tránh bị timeout phiên làm việc.

### 2.4. Giao Diện & Dữ Liệu Ôn Tập (Practice Page)
- **Endpoint:** `GET https://kiemtramophong.com/simulation/practice`
- **Đặc điểm kiến trúc:**
  - Trang web render sẵn toàn bộ dữ liệu của **120 tình huống** chia theo 6 chương.
  - Mỗi tình huống bao gồm 4 câu hỏi trắc nghiệm:
    1. *Nhận biết tên tình huống*
    2. *Dấu hiệu nhận biết gián tiếp*
    3. *Dấu hiệu nhận biết trực tiếp*
    4. *Phương án xử lý tình huống*
  - Đáp án đúng được chỉ định thông qua thuộc tính HTML `data-correct="1"`, trong khi các đáp án gây nhiễu mang `data-correct="0"`.

### 2.5. API & Quản Lý Đáp Án Tùy Chỉnh (Customer Answers)
- **Danh sách tình huống:** `GET https://kiemtramophong.com/admin/simulation/customer-answers`
- **Form chỉnh sửa:** `GET https://kiemtramophong.com/admin/simulation/customer-answers/{id}/edit`
- **API cập nhật đáp án:** `POST https://kiemtramophong.com/admin/simulation/customer-answers/{id}/update`
  - Dữ liệu form:
    - `parts[1][correct_answer]`, `parts[1][wrong_answer]`, `parts[1][wrong_answer_2]`, `parts[1][wrong_answer_3]`
    - `parts[2]...`, `parts[3]...`, `parts[4]...`

---

## 3. Cơ Chế Giới Hạn Tần Suất (Rate Limiting)

Server Nginx + Laravel trang bị cơ chế giới hạn tốc độ truy cập:
- **`GET /simulation/videos/{id}/play-url`:**
  - Giới hạn: **60 requests/phút** (`X-RateLimit-Limit: 60`).
  - Nếu gọi liên tục không độ trễ, sau 60 request sẽ trả về HTTP `429 Too Many Requests`.
- **`GET /simulation/videos/{id}/stream`:**
  - Giới hạn: **120 requests/phút** (`X-RateLimit-Limit: 120`).

> [!IMPORTANT]
> Bộ công cụ tải video `download_videos.py` đã được tích hợp cơ chế theo dõi header `X-RateLimit-Remaining` và giãn cách tự động (delay 1.0 giây giữa mỗi request) để tải trơn tru toàn bộ 120 video mà không bao giờ bị khóa IP hoặc dính lỗi 429.

---

## 4. Cấu Trúc Thư Mục Dữ Liệu Đã Tổ Chức

Toàn bộ dữ liệu được lưu trữ chuẩn hóa tại:
`[kiemtramophong_data](file:///home/vantrong/Documents/kiemtramophong_data)`
*(đồng thời liên kết trực tiếp tại `[scratch/kiemtramophong_data](file:///home/vantrong/.gemini/antigravity-ide/scratch/kiemtramophong_data)`)*.

```text
kiemtramophong_data/
├── Chuong_01_Do_thi_va_khu_dong_dan_cu/       (29 tình huống: TH001 -> TH029)
│   ├── TH001_Nguoi_di_bo_sau_xe_tai/
│   │   ├── info.json                         (Dữ liệu JSON chuẩn API)
│   │   ├── cau_hoi_va_dap_an.md              (Văn bản câu hỏi, lựa chọn & tích chọn đáp án đúng)
│   │   └── video.mp4                         (Video tình huống chất lượng gốc)
│   └── ...
├── Chuong_02_Duong_nong_thon/                (14 tình huống: TH030 -> TH043)
├── Chuong_03_Duong_cao_toc/                  (20 tình huống: TH044 -> TH063)
├── Chuong_04_Duong_nui/                      (10 tình huống: TH064 -> TH073)
├── Chuong_05_Duong_quoc_lo/                  (17 tình huống: TH074 -> TH090)
├── Chuong_06_Tai_nan_giao_thong_thuc_te/     (30 tình huống: TH091 -> TH120)
│
├── tat_ca_cau_hoi.json                       (Master JSON chứa toàn bộ 120 tình huống và 480 câu hỏi)
├── tat_ca_cau_hoi.csv                        (Bảng tính Excel/CSV đầy đủ cột câu hỏi và đáp án đúng/sai)
├── export_and_organize.py                    (Script trích xuất & tổ chức dữ liệu tự động)
└── download_videos.py                        (Tool tải video tự động có rate limit & resume)
```

---

## 5. Hướng Dẫn Sử Dụng Bộ Công Cụ

### 5.1. Cập nhật hoặc xuất lại câu hỏi & đáp án
```bash
python3 /home/vantrong/Documents/kiemtramophong_data/export_and_organize.py
```

### 5.2. Tải thêm video vào từng thư mục
Tool `download_videos.py` tự động phát hiện các file video đã tải xong để bỏ qua (resumable) và tự động ghi vào đúng thư mục tình huống:
```bash
# Tải theo số chương cụ thể (ví dụ chương 1)
python3 download_videos.py --chapter 1

# Tải theo dải tình huống (ví dụ từ tình huống 4 đến 10)
python3 download_videos.py --range 4 10

# Tải 1 tình huống cụ thể (ví dụ tình huống 15)
python3 download_videos.py --stt 15

# Tải toàn bộ 120 video (tự động điều tiết tốc độ an toàn)
python3 download_videos.py --all
```
