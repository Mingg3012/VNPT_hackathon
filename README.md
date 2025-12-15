# 🏆 VNPT Hackathon 2025 - AI Knowledge Base QA System

Dự án xây dựng hệ thống **RAG (Retrieval-Augmented Generation)** tham gia cuộc thi VNPT Hackathon. Hệ thống có khả năng tự động trả lời câu hỏi trắc nghiệm đa lĩnh vực (Lịch sử, Địa lý, Khoa học, Luật...) bằng cách kết hợp truy xuất kiến thức từ Vector Database (ChromaDB) và khả năng suy luận của VNPT LLM.

---

## 📂 Cấu trúc dự án

Hệ thống được chia thành 4 module chính:

### 1. Thu thập dữ liệu (Data Crawling)
* **`crawl_wiki.py`**: Bot tự động thu thập dữ liệu từ Wikipedia theo danh sách chủ đề. Hỗ trợ lọc rác, format lại văn bản và tránh trùng lặp.
* **`crawl_law.py`**: Module sử dụng `BeautifulSoup` để cào dữ liệu chuyên sâu (Luật, Hóa học, Sinh học...) từ các URL cụ thể, bổ sung cho các mảng kiến thức mà Wiki API bị thiếu.
* **`extract_questions.py`**: Phân tích file đề thi (`val.json`, `test.json`) để tìm ra các từ khóa (keyword) xuất hiện nhiều nhất. Giúp định hướng việc crawl dữ liệu sát với đề thi.
* **`data/documents.txt`**: Kho dữ liệu thô (Knowledge Base) tập trung.

### 2. Xây dựng Database (Ingestion)
* **`build_db.py`**: 
  * Đọc dữ liệu từ `documents.txt`.
  * Làm sạch và chia nhỏ văn bản (Chunking ~1200 ký tự).
  * Gọi API Embedding để vector hóa dữ liệu.
  * Lưu trữ vào **ChromaDB** (`./vector_db`).

### 3. Suy luận & Trả lời (Inference Core)
* **`predict.py`** (Main Script):
  * **Phân loại câu hỏi:** Tự động nhận diện loại câu hỏi (STEM, Precision, Unsafe, Normal).
  * **Smart Routing:** Chuyển câu hỏi STEM (Toán/Lý/Hóa) sang Prompt giải toán chuyên biệt và Model Large; câu hỏi thường dùng Prompt đọc hiểu.
  * **Retrieval:** Tìm kiếm 5 đoạn ngữ cảnh liên quan nhất từ ChromaDB.
  * **Post-processing:** Dùng Regex trích xuất đáp án (A, B, C, D) chuẩn xác.
* **`config.py`**: Quản lý cấu hình API và các hằng số hệ thống.

### 4. Công cụ kiểm thử (Utilities)
* **`debug_db.py`**: Kiểm tra trạng thái DB (số lượng docs, test query).
* **`debug_model.py`**: Chạy thử nghiệm visual trên một vài câu hỏi mẫu để soi luồng dữ liệu (Context -> Prompt -> Output).

---

## ⚙️ Cài đặt môi trường

### 1. Yêu cầu hệ thống
* Python 3.8 trở lên.
* Các thư viện phụ thuộc:


2. Cấu hình API Key
Tạo file api_keys.json tại thư mục gốc của dự án với cấu trúc sau (thay thế bằng Key của BTC cấp):

JSON

[
  {
    "llmApiName": "LLM small",
    "authorization": "Bearer YOUR_TOKEN",
    "tokenId": "YOUR_TOKEN_ID",
    "tokenKey": "YOUR_TOKEN_KEY"
  },
  {
    "llmApiName": "vnptai-hackathon-embedding",
    "authorization": "Bearer YOUR_TOKEN",
    "tokenId": "YOUR_TOKEN_ID",
    "tokenKey": "YOUR_TOKEN_KEY"
  }
]
🚀 Hướng dẫn sử dụng (Workflow)
Bước 1: Chuẩn bị dữ liệu (Data Pipeline)
Nếu bạn mới clone dự án về, bạn cần tạo dữ liệu text trước.

Lưu ý: Hãy đảm bảo file data/val.json (hoặc file đề thi mẫu) đã có trong thư mục data/.

Bash

# 1. (Optional) Phân tích đề để lấy từ khóa gợi ý
python extract_questions.py
# -> COPY các từ khóa in ra màn hình và paste vào biến TOPICS trong file crawl_wiki.py

# 2. Chạy Crawler để tải dữ liệu
python crawl_wiki.py
python crawl_law.py
Kết quả: File data/documents.txt sẽ chứa đầy đủ kiến thức.

Bước 2: Xây dựng Vector Database
Chạy lệnh sau để biến dữ liệu text thành vector (Bắt buộc chạy lần đầu hoặc khi documents.txt thay đổi):

Bash

python build_db.py
Kết quả: Thư mục vector_db sẽ được tạo ra.

Bước 3: Kiểm tra hệ thống (Debug)
Trước khi submit, hãy kiểm tra xem DB và Model hoạt động đúng không:

Bash

# Kiểm tra DB đã nạp được bao nhiêu docs
python debug_db.py

# Chạy thử mô phỏng 3 câu hỏi đầu tiên
python debug_model.py
Bước 4: Chạy dự đoán (Inference)
Chế độ Local (Test trên val.json):

Bash

python predict.py
Kết quả lưu tại: submission_local.csv.

Các câu sai sẽ được log vào: wrong_answers.csv (Rất hữu ích để tinh chỉnh Prompt).

Chế độ Docker (Dùng cho Submission):

Bash

python predict.py docker
Hệ thống sẽ đọc private_test.json và xuất ra submission.csv.

💡 Tính năng nổi bật
Hybrid Retrieval Strategy: Kết hợp kiến thức bách khoa từ Wikipedia API và kiến thức chuyên sâu (Luật, Y học) từ Custom Crawler.

Dynamic Prompt Engineering: Không dùng chung một Prompt. Hệ thống tự động phát hiện câu hỏi tính toán (STEM) để kích hoạt chế độ "Chain-of-Thought" giải toán, trong khi câu hỏi sự kiện sẽ dùng chế độ "Reading Comprehension".

Safety & Robustness:

Tự động lọc các câu hỏi nhạy cảm (Unsafe).

Cơ chế Retry thông minh khi API gặp lỗi 429 (Rate Limit) hoặc timeout.

Xử lý lỗi sqlite3 tự động cho môi trường Docker.

📝 Ghi chú quan trọng
Dữ liệu: File data/documents.txt là nguồn chân lý (Source of Truth).

Vector DB: Thư mục vector_db/ chứa dữ liệu đã embedded. Không xóa thư mục này trừ khi bạn muốn build lại từ đầu.

Logs: Nếu chạy bằng VS Code, hãy tích hợp Run in Terminal để thanh tiến trình tqdm hiển thị đẹp không bị vỡ dòng.

Developed for VNPT Hackathon 2025.
