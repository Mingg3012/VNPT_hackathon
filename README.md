# 🏆 VNPT Hackathon - AI Knowledge Base QA System

Hệ thống **RAG (Retrieval-Augmented Generation)** tự động trả lời câu hỏi trắc nghiệm đa lĩnh vực. Dự án kết hợp khả năng truy xuất kiến thức từ Vector Database (ChromaDB) và mô hình ngôn ngữ lớn (LLM) để giải quyết các bài toán từ đọc hiểu văn bản đến tính toán logic (STEM).

---

## 📂 Cấu trúc dự án

Dự án được chia thành các phân hệ chính để quản lý luồng dữ liệu hiệu quả:

### 1. Thu thập & Xử lý dữ liệu (Data Pipeline)
* **`crawl_wiki.py`**: Bot tự động thu thập dữ liệu từ Wikipedia theo danh sách chủ đề định sẵn (Lịch sử, Địa lý, Văn hóa, Chính trị...). Tự động lọc rác và định dạng lại văn bản.
* **`crawl_law.py`**: Module chuyên biệt sử dụng `BeautifulSoup` để cào dữ liệu sâu từ các trang cụ thể (Luật, Hóa học, Sinh học) nhằm bổ sung kiến thức chuyên sâu.
* **`extract_questions.py`**: Phân tích file đề thi (`val.json`, `test.json`) để trích xuất các từ khóa (keyword) quan trọng, giúp định hướng việc crawl dữ liệu bám sát nội dung câu hỏi.
* **`data/documents.txt`**: Kho dữ liệu thô (Knowledge Base) sau khi thu thập.

### 2. Xây dựng Vector Database
* **`build_db.py`**: 
  * Đọc dữ liệu từ `documents.txt`.
  * Làm sạch và cắt nhỏ văn bản (Chunking) để tối ưu cho Embedding.
  * Tạo vector embeddings và lưu trữ vào **ChromaDB**.
  * Hỗ trợ resume (chạy tiếp) và hiển thị tiến trình với `tqdm`.

### 3. Suy luận & Trả lời (Inference Engine)
* **`predict.py`** (Core):
  * **Phân loại câu hỏi:** Tự động nhận diện loại câu hỏi (STEM, Precision, Unsafe, Normal).
  * **Smart Routing:** Sử dụng prompt và model khác nhau cho từng loại câu hỏi (VD: Câu hỏi Toán/Lý sẽ dùng Prompt giải toán chặt chẽ, câu hỏi đọc hiểu dùng Prompt trích xuất).
  * **Retrieval:** Tìm kiếm ngữ cảnh liên quan nhất từ ChromaDB.
  * **Answer Extraction:** Sử dụng Regex để bắt chính xác đáp án (A, B, C, D) từ output của LLM.
* **`config.py`**: Quản lý toàn bộ cấu hình (API Keys, Endpoints, Hyperparameters).

### 4. Công cụ kiểm thử (Utilities)
* **`debug_db.py`**: Script kiểm tra trạng thái ChromaDB (đếm số lượng docs, test query) để đảm bảo dữ liệu đã được nạp thành công.
* **`debug_model.py`**: Chạy thử nghiệm trên một vài câu hỏi mẫu với log chi tiết (Context -> Prompt -> Raw Output) để debug logic mà không cần chạy toàn bộ tập dữ liệu.

---

## ⚙️ Cài đặt

### 1. Yêu cầu hệ thống
* Python 3.8+
* Các thư viện phụ thuộc:

```bash
pip install requests chromadb tqdm pandas wikipedia-api beautifulsoup4
