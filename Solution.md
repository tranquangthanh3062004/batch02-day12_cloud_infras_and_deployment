# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Phân tích Anti-patterns (Các lỗi thiết kế)
Trong file `develop/app.py`, hệ thống tồn tại 5 anti-patterns nghiêm trọng khiến ứng dụng không thể triển khai lên môi trường Production một cách an toàn và bền vững:
1. **Hardcode API Key (Dòng 17):** Biến `AGENT_API_KEY = "my-secret-key-123"` bị viết cứng trực tiếp vào mã nguồn. Nếu đoạn code này được commit lên GitHub (đặc biệt là Public Repo), hacker có thể dùng tool dò quét tự động để đánh cắp key, dẫn đến thiệt hại nặng nề về tài chính hoặc bị xâm nhập hệ thống.
2. **Thiếu quản lý cấu hình tập trung (Dòng 21-22):** Các biến cấu hình hệ thống như `DEBUG = True` và `MAX_TOKENS = 100` bị "hardcode". Trên Production, ta không được phép bật chế độ Debug vì nó làm lộ Traceback code cho người dùng cuối (chứa thông tin nhạy cảm). Hơn nữa, mỗi khi cần đổi `MAX_TOKENS`, lập trình viên phải sửa code và deploy lại từ đầu thay vì chỉ đổi biến môi trường.
3. **Sử dụng lệnh `print()` để ghi Log (Dòng 33-34):** Việc dùng `print(f"User {user_id} asked: {question}")` là tối kỵ. Trên Production, logs sinh ra cực lớn và cần được đẩy về các hệ thống thu thập tập trung (như ELK Stack, Datadog). Lệnh `print` không có cấu trúc chuẩn, không phân loại được mức độ nghiêm trọng (INFO, WARNING, ERROR) và tệ nhất là in cả thông tin nhạy cảm của user ra màn hình console.
4. **Không có Health Check Endpoint (Dòng 42):** Ứng dụng thiếu endpoint `/health` hoặc `/ready`. Các hệ thống Orchestration (như Kubernetes, Docker Swarm) hay Load Balancer (Nginx, AWS ALB) dựa vào endpoint này để "bắt mạch" xem server còn sống không. Nếu app bị treo cứng (deadlock), do không có Health Check, Load Balancer không biết đường gỡ nó ra khỏi pool, dẫn đến user bị treo theo.
5. **Hardcode Host và Port (Dòng 51-52):** Buộc ứng dụng chạy ở `uvicorn.run(app, host="localhost", port=8000)`. Khi đưa lên Cloud (như Render, Heroku), Cloud Provider thường chỉ định một Port động ngẫu nhiên (thông qua biến môi trường `$PORT`). Việc fix cứng Port 8000 và host localhost khiến container không thể public ra bên ngoài Internet.

### Exercise 1.3: Bảng so sánh Kiến trúc
| Tiêu chí (Feature) | Basic (Develop) | Advanced (Production) | Tại sao quan trọng? (Why Important?) |
|---------|-------|----------|---------------------|
| **Cấu hình (Config)** | Hardcode thẳng trong source code. | Đọc từ Environment Variables (`.env` hoặc Config Server). | Tuân thủ tuyệt đối triết lý **12-Factor App** (Tách biệt cấu hình khỏi mã nguồn). Giúp dễ dàng luân chuyển ứng dụng qua các môi trường (Dev -> Staging -> Prod) mà không cần sửa code. |
| **Health Check** | Hoàn toàn không có. | Có endpoint `/health` (Liveness) và `/ready` (Readiness). | Cung cấp tín hiệu sinh tồn cho Cloud Platform/Load Balancer. Nếu app bị kẹt, hệ thống sẽ tự động kill container cũ và spawn container mới để tự phục hồi (Self-healing). |
| **Ghi nhật ký (Logging)** | Dùng lệnh `print()` tiêu chuẩn. | Dùng structured JSON format thông qua thư viện `logging`. | Log JSON có cấu trúc (Time, Level, Message, RequestID) giúp máy móc (Parser) dễ dàng bóc tách, lập bảng thống kê biểu đồ (Dashboard) và thiết lập cảnh báo tự động (Alerting). |
| **Tắt máy (Shutdown)** | Tắt đột ngột (Kill -9). | Graceful Shutdown (Bắt tín hiệu SIGTERM). | Đảm bảo các request của user đang xử lý dở dang (ví dụ: đang gọi API OpenAI mất 5 giây) sẽ được hoàn thành nốt, kết nối Database được đóng an toàn trước khi server thực sự ngừng hoạt động. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Phân tích Dockerfile
1. **Base image:** Sử dụng `python:3.11`. Tuy nhiên, đây là bản cài đặt đầy đủ (Full Debian-based) chứa rất nhiều công cụ OS không cần thiết, làm dung lượng file ảnh phình to (khoảng ~1GB).
2. **Working directory:** Thiết lập là `/app`. Đây là quy chuẩn chung giúp cô lập mã nguồn vào một thư mục chuyên biệt, tránh việc ghi đè vô ý lên hệ thống file của thư mục gốc root (`/`).
3. **Tại sao `COPY requirements.txt` trước khi `COPY . .`?** Việc này giúp tối ưu hóa Docker Layer Cache. Docker build từng dòng lệnh thành từng Layer. Quá trình `pip install` tốn nhiều thời gian nhất. Bằng cách copy file cấu hình thư viện riêng và install trước, nếu source code thay đổi nhưng thư viện (`requirements.txt`) không đổi, Docker sẽ lấy kết quả pip install từ cache cũ (Layer caching) thay vì tải lại từ đầu, giúp giảm thời gian build từ vài phút xuống còn vài giây.
4. **Sự khác biệt giữa CMD và ENTRYPOINT:** 
   - `CMD`: Cung cấp tham số mặc định để chạy container. Lệnh này rất dễ bị ghi đè khi user gõ lệnh ở cuối (VD: `docker run image bash` sẽ ghi đè CMD).
   - `ENTRYPOINT`: Cố định executable của container, biến container thành một file thực thi (Executable App). Các lệnh gõ thêm chỉ được xem là tham số (arguments) truyền vào ENTRYPOINT chứ không ghi đè nó.

### Exercise 2.3: Multi-stage Build và Tối ưu dung lượng
- **Phiên bản Develop:** Nặng ~1.01 GB (vì chứa toàn bộ source code của OS, trình biên dịch C/C++ để compile thư viện Python).
- **Phiên bản Production:** Giảm xuống chỉ còn ~160 MB.
- **Giải thích cơ chế Multi-stage build:** Phiên bản Production chia Dockerfile làm 2 giai đoạn (Stages). 
  - **Stage 1 (Builder):** Dùng Image nặng, cài trình biên dịch `build-essential`, tiến hành tải và biên dịch toàn bộ các package (dependencies).
  - **Stage 2 (Runtime):** Dùng Image `3.11-slim` siêu nhẹ. Docker chỉ việc `COPY` các thư viện đã biên dịch xong xuôi từ Stage 1 sang Stage 2. Nhờ đó, toàn bộ trình biên dịch và file rác sinh ra trong lúc tải thư viện bị vứt bỏ hoàn toàn. Điều này không chỉ giúp container nhẹ hơn, boot nhanh hơn mà còn **tăng cường bảo mật** vì hacker không có công cụ biên dịch để khai thác lỗ hổng nếu xâm nhập được.

---

## Part 3: Cloud Deployment

### Deployment Strategy (GitOps vs CLI)
- **Phương pháp Deploy:** Thay vì gõ lệnh CLI thủ công trên máy tính dễ xảy ra sai sót, hệ thống được thiết kế hướng tới **GitOps**. Cụ thể, các file Infrastructure as Code (như `render.yaml` cho Render hoặc `railway.toml` cho Railway) được chuẩn bị sẵn.
- **Bản chất của GitOps:** Mã nguồn là chân lý (Single source of truth). Thay vì ta chủ động đẩy code lên mây, Máy chủ Cloud sẽ theo dõi nhánh `main` trên GitHub. Mỗi khi có code mới được commit, Cloud server sẽ tự động kích hoạt CI/CD pipeline: Kéo code về -> Dựng Docker Image -> Đổ biến môi trường (Secrets/Config) -> Bật container và điều hướng traffic (Zero-downtime deployment). Điều này loại bỏ hoàn toàn hiện tượng "Works on my machine".

---

## Part 4: API Security

### Exercise 4.1: API Key authentication
- **Kiểm tra ở đâu?** Thông qua cơ chế **Dependency Injection** của FastAPI (`Depends(verify_api_key)`). Nó đứng chắn ở cửa ngõ (Middleware) và bóc tách Header `X-API-Key` hoặc `Authorization` trước khi request chạm vào business logic.
- **Chuyện gì xảy ra nếu sai key?** Server chặn đứng và ném ra Exception `HTTP 401 Unauthorized` (Truy cập trái phép) hoặc `403 Forbidden`, ngăn chặn mọi tiêu hao tài nguyên.
- **Cách xoay vòng (Rotate) key:** Khi nghi ngờ lộ key, Admin chỉ cần lên Dashboard của nền tảng Cloud (Railway/Render) đổi giá trị của biến môi trường `AGENT_API_KEY` và ấn Restart. Hệ thống ngay lập tức cập nhật cấu hình mà không cần tốn thời gian sửa code, commit và build lại container.

### Exercise 4.2: Cơ chế JWT (JSON Web Token)
Khác với API Key (thường là một chuỗi vô nghĩa cấp vĩnh viễn), JWT hoạt động an toàn hơn:
1. Client gửi credentials (User/Pass) qua phương thức an toàn (POST) tới `/token`.
2. Server xác thực và cấp lại một chuỗi JWT. Chuỗi này chứa thông tin user (payload) và được **ký kỹ thuật số (Cryptographic Signature)**.
3. User kẹp Token này vào HTTP Header `Authorization: Bearer <Token>` để xài. 
4. Token có hạn sử dụng ngắn (TTL - Time to live). Khi hết hạn, token tự động vô hiệu, bắt buộc user phải xác thực lại, giảm rủi ro bị đánh cắp vĩnh viễn.

### Exercise 4.3: Rate Limiting (Giới hạn tốc độ)
- **Thuật toán:** Thường sử dụng thuật toán **Sliding Window** (Cửa sổ trượt) hoặc **Token Bucket** kết hợp với **Redis**. Redis được chọn vì nó là cơ sở dữ liệu In-memory, có độ trễ cực thấp (Sub-millisecond), đảm bảo việc trừ tiền/đếm request không làm chậm trải nghiệm của user.
- **Cơ chế Bypass cho Admin:** Rất đơn giản khi kết hợp với JWT. Token được giải mã ở Middleware sẽ bóc ra được `Role`. Nếu `Role == "Admin"`, hàm kiểm tra sẽ bỏ qua bước gõ cửa Redis và trả về `True` ngay lập tức, cho phép lượng truy cập không giới hạn.

### Exercise 4.4: Cost Guard (Bảo vệ ngân sách)
- **Giải pháp:** Khi dùng LLM (như OpenAI), mỗi truy vấn tiêu tốn số tiền khác nhau dựa trên số token. Sử dụng lệnh `incrbyfloat` của Redis để cộng dồn chi phí `cost` vào một key định danh theo người dùng và tháng (VD: `budget:user_A:2026_06`).
- **Ngưỡng chặn:** Trước khi gọi LLM, server check Redis. Nếu giá trị `budget > 10$`, lập tức chối từ phục vụ bằng mã `HTTP 402 Payment Required`.
- **Dọn rác tự động:** Gán TTL cho key Redis là 32 ngày (`r.expire`). Bước qua tháng mới, key tự xóa, budget quay về số 0 một cách tự động hoàn toàn.

---

## Part 5: Scaling & Reliability

### Exercise 5.1 & 5.2: Cơ chế sinh tồn của Server
- **`/health` (Liveness Probe):** Chức năng duy nhất là trả về HTTP 200. Các Load Balancer (LB) sẽ gọi endpoint này mỗi 10 giây. Nếu app treo không phản hồi, LB hiểu container đã "chết lâm sàng" và tự động kill nó để spawn container mới.
- **`/ready` (Readiness Probe):** Phức tạp hơn Liveness. Nó phải gọi thử xuống Database, ping thử Redis. Dù app vẫn chạy (Health OK) nhưng nếu đứt mạng với DB, Readiness sẽ trả về HTTP 503. Lúc này LB sẽ không kill container mà chỉ tạm thời không ném Traffic của user vào container này nữa, chờ đến khi mạng ổn định lại.
- **Graceful Shutdown:** Rất quan trọng khi nâng cấp phiên bản (Rolling Update). Khi container bị yêu cầu tắt, nó nhận tín hiệu `SIGTERM`. App sẽ từ chối các request mới, nhưng vẫn nỗ lực **giữ kết nối** với các request cũ đang chờ LLM trả lời. Sau khi trả lời xong, nó mới đóng kết nối Database và tự sát. Tránh việc user bị báo lỗi "Connection Reset" ngang xương.

### Exercise 5.3 & 5.4: Scaling và Stateless Design
- **Vấn đề Stateful (Anti-pattern):** Trong ứng dụng RAG/Chat, nếu ta lưu lịch sử chat vào bộ nhớ RAM của code Python (`dict`), ứng dụng được gọi là Stateful. Khi hệ thống quá tải, ta nhân bản (Scale) lên 3 Server (A, B, C). Lần 1 user chat trúng Server A, lần 2 Load Balancer điều hướng user sang Server B. Do Server B không có RAM của Server A, con AI trên Server B hoàn toàn mất trí nhớ về câu hỏi trước đó.
- **Giải pháp Stateless:** Mọi lịch sử hội thoại, phiên làm việc, budget đều phải tống xuất khỏi RAM Python và dồn về lưu tại một **cụm Redis trung tâm**. Dù user bị điều hướng đi bất kỳ Server nào trong số 3 Server kia, Server đó cũng chỉ cần chọc xuống Redis là lấy lại được y nguyên ký ức (History context).
- **Load Balancing (Nginx):** Đứng ngoài cùng làm trạm kiểm soát (Reverse Proxy). Nó giấu đi danh tính thực của 3 con Server bên trong và phân phát đồng đều các luồng traffic khổng lồ (bằng thuật toán Round Robin) để không con Server nào bị "chết chìm" vì quá tải cục bộ.
