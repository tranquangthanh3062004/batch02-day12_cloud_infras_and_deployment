# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
Trong file `develop/app.py`, có các anti-pattern (lỗi thiết kế) sau đây khiến ứng dụng không thể đưa lên production:
1. **Hardcode API Key (Dòng 17):** Lưu trực tiếp secret key trong source code. Nếu push lên GitHub, hacker có thể tìm thấy và đánh cắp tài khoản.
2. **Thiếu quản lý cấu hình tập trung (Dòng 21-22):** Các biến cấu hình (`DEBUG`, `MAX_TOKENS`) bị code cứng. 
3. **Sử dụng lệnh `print()` để log (Dòng 33-34):** In log bằng `print` rất khó để các hệ thống (ELK, Datadog) phân tích. Tệ hơn nữa là in ra cả secret.
4. **Không có Health Check Endpoint (Dòng 42):** Các nền tảng cloud cần endpoint này để ping xem app có bị treo không.
5. **Hardcode Host và Port (Dòng 51-52):** Buộc ứng dụng chạy ở `localhost:8000`, không thể tương thích với môi trường Cloud cấp port động.

### Exercise 1.3: Comparison table
| Feature | Basic (Develop) | Advanced (Production) | Tại sao quan trọng? (Why Important?) |
|---------|-------|----------|---------------------|
| **Config** | Hardcode thẳng trong code | Đọc từ Environment Variables (`.env`) | Tách biệt cấu hình khỏi code (chuẩn 12-factor). Dễ đổi cấu hình giữa các môi trường. |
| **Health check** | Không có | Có `/health` và `/ready` | Giúp Cloud Platform/Load Balancer biết ứng dụng còn sống hay không để tự động restart. |
| **Logging** | Dùng `print()` | Dùng structured JSON format | Log có cấu trúc (JSON) giúp máy móc (ELK) dễ dàng parse, lập bảng thống kê và cảnh báo. |
| **Shutdown** | Đột ngột (Kill ngay) | Graceful Shutdown (Bắt tín hiệu SIGTERM) | Đảm bảo các request của user đang xử lý dở dang sẽ được hoàn thành trước khi tắt server. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile questions
1. **Base image:** `python:3.11` (Bản đầy đủ, nặng ~1GB).
2. **Working directory:** `/app`.
3. **Tại sao COPY requirements.txt trước?** Để tận dụng Docker Layer Cache. Nếu code thay đổi mà thư viện không đổi, Docker bỏ qua việc tải lại pip install, giúp build siêu tốc.
4. **CMD vs ENTRYPOINT:** `CMD` dễ dàng bị ghi đè khi gọi lệnh `docker run`, còn `ENTRYPOINT` biến container thành một app cố định, khó bị ghi đè hơn.

### Exercise 2.3: Image size comparison
- Develop: ~1.01 GB
- Production: ~160 MB
- Difference: Tiết kiệm được ~85% dung lượng. Do bản Production dùng **Multi-stage build**: vứt bỏ các công cụ compile C/C++ ở stage 1 và chỉ giữ lại thư viện đã compile xong ở runtime stage siêu nhẹ.

---

## Part 3: Cloud Deployment

### Exercise 3.1 & 3.2: Cloud Deploy
*Thay vì dùng Railway CLI, hệ thống được triển khai bằng **GitOps** qua nền tảng Render. Mã nguồn được đẩy lên GitHub và Render sẽ tự động kéo về, cấp biến môi trường (PORT, API_KEY) và build container tự động.*
- **URL Public:** *(Sẽ được cập nhật sau khi hoàn tất Part 6).*
- Khái niệm **GitOps** rất an toàn vì chúng ta không cần cài Docker hay bất kỳ tool CLI nào trên máy tính, mọi thao tác build/deploy đều diễn ra khép kín trên server của Render.

---

## Part 4: API Security

### Exercise 4.1: API Key authentication
- **Kiểm tra ở đâu?** Thường được kiểm tra ở một hàm Middleware hoặc qua `Depends()` của FastAPI bằng cách đọc header `X-API-Key` hoặc `Authorization`.
- **Chuyện gì xảy ra nếu sai key?** Trả về mã lỗi HTTP `401 Unauthorized`.
- **Cách xoay vòng (Rotate) key:** Cập nhật biến môi trường `AGENT_API_KEY` trên Dashboard của Cloud Platform (Render/Railway) và restart container. Không cần sửa một dòng code nào.

### Exercise 4.2: JWT Flow
Luồng hoạt động chuẩn: User gửi username/password đến endpoint `/token` qua phương thức POST -> Server cấp lại một chuỗi mã hóa (JWT Token) -> User gắn token này vào header `Authorization: Bearer <token>` để gọi các API khác.

### Exercise 4.3: Rate Limiting
- Thuật toán thường dùng là **Sliding Window** hoặc **Token Bucket** áp dụng cùng với Redis (do Redis có tốc độ đọc/ghi in-memory siêu nhanh).
- Để bypass (vượt qua) limit cho admin: Chỉ cần thêm logic đọc role của user từ JWT Token, nếu role là 'admin' thì return `True` (bỏ qua bước đếm trong Redis).

### Exercise 4.4: Cost Guard
- **Giải pháp:** Sử dụng Redis `incrbyfloat` để cộng dồn chi phí của từng user theo tháng (ví dụ key: `budget:userA:2026-06`).
- Nếu `current_spend + cost > 10$`, server từ chối request bằng HTTP `402 Payment Required`. Cài đặt TTL (thời gian sống) cho key trong Redis là 32 ngày để tự động dọn rác qua tháng mới.

---

## Part 5: Scaling & Reliability

### Exercise 5.1 & 5.2: Health Checks & Graceful Shutdown
- **`/health` (Liveness):** Kiểm tra xem tiến trình Python có đang chạy không.
- **`/ready` (Readiness):** Thử ping đến Redis hoặc Database xem có kết nối được không.
- **Graceful Shutdown:** Bắt tín hiệu `SIGTERM` từ Docker/Kubernetes. Ngưng nhận request mới, đợi các request cũ chạy xong (ví dụ LLM đang gen dở) rồi mới tắt connection và thoát chương trình.

### Exercise 5.3 & 5.4: Stateless Design & Load Balancing
- **Vấn đề Stateful:** Nếu lưu lịch sử chat vào biến dict `{}` của Python (Memory), khi scale lên 3 server, request thứ 1 chạy vào server A, request thứ 2 chạy vào server B thì server B sẽ không biết user đã nói gì trước đó.
- **Giải pháp Stateless:** Đẩy hoàn toàn lịch sử hội thoại lưu vào **Redis**. Mọi server khi nhận request đều phải truy vấn Redis để lấy ngữ cảnh.
- **Load Balancing:** Nginx sẽ đứng ra làm cửa ngõ (Reverse Proxy), dùng thuật toán Round-Robin chia đều request của người dùng cho 3 instances Agent đang chạy ngầm bên dưới, đảm bảo hệ thống không bị quá tải cục bộ.
