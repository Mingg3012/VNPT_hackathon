import requests
from bs4 import BeautifulSoup
import re
import os
import time

# --- CẤU HÌNH ---
FILE_PATH = "data/documents.txt"

wiki_urls = [
    "https://vi.wikipedia.org/wiki/Hóa_học",
    "https://vi.wikipedia.org/wiki/Bảng_tuần_hoàn",
    "https://vi.wikipedia.org/wiki/Phản_ứng_hóa_học",
    "https://vi.wikipedia.org/wiki/Hóa_học_hữu_cơ",
    "https://vi.wikipedia.org/wiki/Sinh_học",
    "https://vi.wikipedia.org/wiki/Di_truyền_học",
    "https://vi.wikipedia.org/wiki/Tế_bào",
    "https://vi.wikipedia.org/wiki/Tiến_hóa",
    "https://vi.wikipedia.org/wiki/Lịch_sử_thế_giới",
    "https://vi.wikipedia.org/wiki/Chiến_tranh_thế_giới_thứ_hai",
    "https://vi.wikipedia.org/wiki/Địa_lý",
    "https://vi.wikipedia.org/wiki/Công_nghệ_thông_tin",
    "https://vi.wikipedia.org/wiki/Trí_tuệ_nhân_tạo",
    "https://vi.wikipedia.org/wiki/Văn_học"
]

def get_start_id(file_path):
    if not os.path.exists(file_path):
        return 1
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            matches = re.findall(r"\.", content)
            if matches:
                return int(max(map(int, matches))) + 1
    except Exception:
        pass
    return 1

def clean_wiki_text(text):
    """Làm sạch văn bản Wikipedia"""
    # Xóa các tham chiếu và ký tự thừa
    text = re.sub(r'\[\d+\]', '', text) 
    text = re.sub(r'\[cần dẫn nguồn\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def crawl_wiki_topics():
    current_id = get_start_id(FILE_PATH)
    print(f"🚀 Bắt đầu crawl Hóa/Sinh. ID tiếp theo: ")
    
    new_content = ""
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in wiki_urls:
        print(f"--> Đang tải: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"❌ Lỗi tải trang: {url}")
                continue

            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 1. Lấy tiêu đề
            title = soup.find('h1', {'id': 'firstHeading'}).text
            new_content += f"CHỦ ĐỀ: {title}\n"
            current_id += 1
            new_content += f"Link: {url}\n"
            current_id += 1

            # 2. Lấy nội dung chính (div class="mw-parser-output")
            content_div = soup.find('div', {'class': 'mw-parser-output'})
            if content_div:
                
                # --- PHƯƠNG PHÁP MỚI: Lấy tất cả text và split theo dòng ---
                
                # Loại bỏ các box bên phải (infobox) và các mục lục (toc) để giảm rác
                for junk in content_div.find_all(['table', 'div', 'ul'], class_=['infobox', 'toc', 'navbox']):
                    junk.decompose()
                
                # Lấy text thô, dùng '\n' làm dấu phân cách giữa các block
                full_text = content_div.get_text(separator="\n\n")

                # Tách thành các đoạn văn
                paragraphs = full_text.split('\n\n')

                count = 0
                for p_raw in paragraphs:
                    text = clean_wiki_text(p_raw)
                    
                    # Lọc mạnh mẽ hơn: Chỉ lấy đoạn văn có nội dung > 150 ký tự
                    # và không phải là các mục (vì đã loại h2, ul thô ở trên)
                    if len(text) > 150 and not text.endswith('Mục lục'):
                        new_content += f"{text}\n"
                        current_id += 1
                        count += 1
                    
                    # Giới hạn lấy 15 đoạn văn chất lượng cao mỗi bài
                    if count >= 15:
                        break
                
                print(f"✅ Đã thêm {count} đoạn văn về {title}.")
            
            time.sleep(1) 

        except Exception as e:
            print(f"❌ Lỗi ngoại lệ: {e}")

    # Ghi vào file
    if new_content:
        with open(FILE_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + new_content)
        print(f"\n🎉 Thành công! Đã cập nhật kiến thức mới vào '{FILE_PATH}'")
    else:
        print("\n⚠️ Không tải được nội dung nào.")

if __name__ == "__main__":
    crawl_wiki_topics()