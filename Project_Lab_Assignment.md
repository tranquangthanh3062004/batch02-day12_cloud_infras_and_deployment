# Day 12 Project - Lab Assignment

## 1. Project Selection
Thực hiện yêu cầu ở Part 6, nhóm thực hành đã lựa chọn dự án **Day08_RAG_pipeline_cohort2** (Hệ thống RAG Trợ lý tra cứu Luật Phòng chống ma túy Việt Nam) để làm "chuột bạch" cho quá trình **Productionization**.

Dự án này ban đầu vốn là một nguyên mẫu (Prototype) thuần túy bằng Streamlit chạy trên máy tính cá nhân (Localhost). Nó tồn tại rất nhiều Anti-patterns của môi trường Development. Thông qua bài tập này, dự án đã được chuyển đổi, đóng gói Docker bảo mật, tái cấu trúc quản lý môi trường và triển khai thành công lên nền tảng đám mây (Railway).

## 2. Các bước Restructure & Productionization đã áp dụng

Bám sát theo Rubric của môn học, hệ thống đã được tái cấu trúc và áp dụng các tiêu chuẩn Production như sau:

### 2.1. Containerization (Đóng gói Docker) & Tối ưu dung lượng
- **Multi-stage Build:** Thay vì sử dụng Image mặc định siêu nặng, một `Dockerfile` chuẩn đã được thiết kế. Cụ thể, Image chia làm 2 phase (Builder và Runtime). Thư viện được tải và compile bằng base image đầy đủ, nhưng khi đóng gói chạy thật, nó được nhúng vào base image `python:3.11-slim`. Kích thước vùng chứa giảm mạnh, giúp khởi động nhanh chóng.
- **Phân quyền Security (Non-root user):** Một lỗ hổng kinh điển khi dùng Docker là chạy ứng dụng bằng quyền `root`. Chúng tôi đã chèn thêm script tạo nhóm `groupadd -r appuser` và cấp quyền giới hạn cho user ảo này. Dù Hacker đánh sập được ứng dụng, chúng cũng không thể thoát khỏi Container để chiếm quyền hệ điều hành Host.

### 2.2. Configuration Management (Chuẩn 12-Factor App)
- Quét sạch toàn bộ các Secret Key bị hardcode trong mã nguồn Day 08.
- Chuyển `OPENAI_API_KEY` ra quản lý độc lập thông qua Cơ chế Biến môi trường (Environment Variables). 
- Trên môi trường phát triển (Local), sử dụng `.env` để bảo vệ key cá nhân. Khi lên môi trường Production, biến này được thiết lập thủ công an toàn trên giao diện GUI của Railway Dashboard, cách ly hoàn toàn rủi ro lộ lọt key qua GitHub.

### 2.3. Sửa lỗi Dependency và Data Mapping (Bug Fixes for Production)
- Khắc phục sự cố xung đột thư viện `chromadb` thường gặp trên Docker bằng cách cố định version (Pin version) nghiêm ngặt trong file `requirements.txt`.
- Sửa lỗi Database "Tàng hình": Khi triển khai lên mây, ứng dụng liên tục báo lỗi `Collection [DrugLawDocs] does not exist`. Lý do là file `.gitignore` vô tình chặn thư mục cơ sở dữ liệu Vector Database không cho đẩy lên CI/CD. Đã cấu hình lại `.gitignore` (và `.dockerignore`) để cho phép Nixpacks/Docker engine bốc thư mục dữ liệu `data/chroma_db/` vào quá trình Build, giúp RAG AI có dữ liệu để chạy truy vấn.

### 2.4. Khái quát về Kiến trúc API & Reliability (Non-functional coverage)
Bên cạnh việc đưa UI lên sóng, kiến trúc nền tảng (phục vụ cho việc Restructure theo template REST API `06-lab-complete`) cũng được hoạch định rõ:
- **Rate Limiting & Cost Guard:** Sẵn sàng giới hạn 10 request/min và chi phí ngân sách $10/user/tháng nhằm chống DDOS và cạn kiệt tài khoản OpenAI.
- **Graceful Shutdown & Health Probes:** Đảm bảo khả năng sinh tồn tự động của Server (Restart khi deadlock và tắt an toàn không gây mất kết nối).
- **Stateless Design:** Các cơ chế lưu hội thoại đang được chuyển dịch từ việc phụ thuộc vào Server (Stateful) sang việc phân tán ngữ cảnh lưu trữ vào cụm Redis.

### 2.5. Tối ưu giao diện (UI/UX) cho bản Public
- Bản Deploy thực tế đã được can thiệp sâu vào file CSS nhúng của Streamlit. Thiết kế giao diện từ nền trắng mặc định đã được "bơm" thêm phong cách kính mờ (Glassmorphism), bóng đổ đa chiều, hiệu ứng micro-animations và chuyển tông màu chuyên nghiệp nhằm tạo ra cảm giác "Wow" cao cấp nhất cho end-user.

## 3. Deploy & API URL
Dự án đã được triển khai (Deploy) thành công và hoạt động trơn tru qua **Railway CLI**. Quá trình Pipeline bao gồm:
1. Xác thực tài khoản qua CLI (`railway login`).
2. Khởi tạo một Empty Project và Link với mã nguồn Localhost.
3. Thiết lập biến môi trường thông qua CLI (`railway variables set OPENAI_API_KEY=...`).
4. Kích hoạt lệnh đẩy lên mây thần thánh: `railway up`. Nixpacks tự động rà quét mã nguồn Python và thực hiện Zero-Config Deployment.

**🔗 Public Link của Trợ lý AI (Đã Live):**
> **[https://impartial-nourishment-production-3686.up.railway.app](https://impartial-nourishment-production-3686.up.railway.app)**

*(Lưu ý: Link có thể có tuổi thọ giới hạn do policy giới hạn Resource Free-tier của Railway).*
