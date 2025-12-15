VNPT Hackathon - AI Knowledge Base QA System
Dự án này là một hệ thống RAG (Retrieval-Augmented Generation) được xây dựng để tham gia cuộc thi VNPT Hackathon. Hệ thống có khả năng tự động trả lời các câu hỏi trắc nghiệm đa lĩnh vực bằng cách kết hợp truy xuất kiến thức từ Vector Database và khả năng suy luận của LLM (Large Language Model).

📂 Cấu trúc dự án
Dựa trên các file mã nguồn, dự án được chia thành 4 phân hệ chính:

1. Thu thập dữ liệu (Data Crawling)
Các script này chịu trách nhiệm làm giàu dữ liệu cho Knowledge Base.

crawl_wiki.py: Sử dụng thư viện wikipedia-api để tải nội dung từ danh sách các chủ đề định sẵn (Lịch sử, Địa lý, Văn hóa, Kinh tế...). Tự động làm sạch và lưu vào data/documents.txt.

crawl_law.py: Sử dụng BeautifulSoup để cào dữ liệu từ các trang Wiki đặc thù (Hóa học, Sinh học, Luật...) theo URL cụ thể. Hỗ trợ lọc rác HTML và nối tiếp vào file dữ liệu chung.

extract_questions.py: Phân tích file câu hỏi (val.json, test.json) để trích xuất các từ khóa (keyword) xuất hiện nhiều nhất. Kết quả dùng để cập nhật danh sách chủ đề cần crawl, đảm bảo Knowledge Base bao phủ đúng trọng tâm câu hỏi.

2. Xây dựng Database (Ingestion)
build_db.py:

Đọc dữ liệu thô từ data/documents.txt.

Làm sạch văn bản (clean_text) và chia nhỏ (chunking) thành các đoạn văn < 1200 ký tự.

Gọi API Embedding của VNPT để chuyển văn bản thành vector.

Lưu trữ vector và metadata vào ChromaDB (./vector_db).

Lưu ý: Có sử dụng tqdm để hiện thanh tiến trình xử lý.

3. Suy luận & Trả lời (Inference)
predict.py (Main Script):

Phân loại câu hỏi: Tự động phát hiện loại câu hỏi (STEM, PRECISION, UNSAFE, NORMAL) dựa trên từ khóa.

Search/Retrieval: Tìm kiếm 5 đoạn văn bản liên quan nhất từ ChromaDB dựa trên câu hỏi.

Prompt Engineering: Tạo prompt động. Nếu là câu hỏi STEM, dùng prompt chuyên về tính toán/logic. Nếu là câu hỏi đọc hiểu, dùng prompt bám sát ngữ cảnh.

LLM Integration: Gọi API vnptai-hackathon-small hoặc large tùy độ khó.

Post-processing: Dùng Regex để trích xuất đáp án (A, B, C, D) từ câu trả lời của model.

config.py: Quản lý cấu hình tập trung. Chứa URL API, đường dẫn file, và logic load api_keys.json để lấy Token/Authentication headers.

4. Công cụ kiểm thử (Debugging)
debug_db.py: Script kiểm tra nhanh tình trạng ChromaDB (đếm số lượng documents, peek dữ liệu, test thử query embedding) để đảm bảo DB không bị rỗng.

debug_model.py: Chạy test trên một vài câu hỏi mẫu từ val.json. In ra log chi tiết từng bước (Embedding -> Context tìm thấy -> Prompt -> LLM Response -> Regex Match) để debug logic mà không cần chạy toàn bộ tập dữ liệu.
