from newspaper import Article
import time

# Danh sách link các bộ luật quan trọng (Bạn tìm link trên thuvienphapluat hoặc vbpl rồi paste vào đây)
law_urls = [
    "https://thuvienphapluat.vn/van-ban/Bo-may-hanh-chinh/Luat-Cu-tru-2020-443243.aspx", # Luật cư trú
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Bo-luat-dan-su-2015-296215.aspx",   # Dân sự
    "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Luat-68-2020-QH14-cu-tru-435315.aspx",
    
    # ... Dán thêm link các luật khác vào đây
]

def crawl_laws():
    full_text = []
    
    print("Bắt đầu tải văn bản luật...")
    for url in law_urls:
        try:
            print(f"--> Đang xử lý: {url}")
            article = Article(url)
            article.download()
            article.parse()
            
            # Lấy nội dung text
            content = article.text
            
            # Xử lý sơ bộ: Xóa các dòng quá ngắn hoặc không có ý nghĩa
            lines = content.split('\n')
            clean_lines = [line.strip() for line in lines if len(line.strip()) > 20]
            
            full_text.extend(clean_lines)
            
            # Nghỉ 2s để không bị chặn IP
            time.sleep(2)
            
        except Exception as e:
            print(f"Lỗi link {url}: {e}")

    # Lưu nối tiếp vào file documents.txt cũ (mode 'a' = append)
    with open("data/documents.txt", "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(full_text))
    
    print(f"Đã thêm {len(full_text)} dòng luật vào documents.txt!")

if __name__ == "__main__":
    crawl_laws()