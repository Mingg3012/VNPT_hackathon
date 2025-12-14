import wikipediaapi
import os
import re
from tqdm import tqdm


# --- CẤU HÌNH ---
OUTPUT_FILE = "data/documents.txt"
LANG = "vi"


# Danh sách từ khóa
TOPICS = [
    # --- 1. NHÂN VẬT LỊCH SỬ & CHÍNH TRỊ ---
    "Hồ Chí Minh", "Võ Nguyên Giáp", "Trần Hưng Đạo", "Quang Trung", "Nguyễn Huệ",
    "Trần Nhân Tông", "Trần Thánh Tông", "Khâm Từ Hoàng", "Mạc Đăng Dung", "Mạc Đĩnh Chi",
    "Lê Chiêu Thống", "Nguyễn Hữu Chỉnh", "Trịnh Bồng", "Nguyễn Thái Học",
    "Tưởng Giới Thạch", "Hốt Tất Liệt", "Thành Cát Tư Hãn", "Tần Thủy Hoàng", "Càn Long",
    "François Mitterrand", "Saddam Hussein", "Gioan Phaolô II", "Friedrich Wilhelm",
    "Augustine xứ Hippo", "Jacques Lacan",


    # --- 2. SỰ KIỆN & TỔ CHỨC ---
    "Việt Nam Quốc dân Đảng", "Khởi nghĩa Yên Bái", "Nhà tù Hỏa Lò",
    "Chiến dịch Điện Biên Phủ", "Chiến tranh thế giới thứ hai", "Khối Warszawa",
    "Đảng Cộng sản Việt Nam", "Đảng Lao động Việt Nam", "Trung ương Cục miền Nam",
    "Đại Việt", "Đại Nguyên", "Hậu Lê", "Tây Sơn",


    # --- 3. ĐỊA DANH & QUỐC GIA ---
    "Việt Nam", "Trung Quốc", "Hoa Kỳ", "Liên Xô", "Ấn Độ", "Nhật Bản", "Hàn Quốc",
    "Hà Nội", "Sài Gòn", "Đà Nẵng", "Hải Phòng", "Quảng Ninh", "Thanh Hóa", "Nghệ An",
    "Yên Bái", "Lạng Sơn", "Thường Xuân", "Hòa Phong", "Đảo Jaffna", "Palm Jumeirah",
    "Ba Lan", "Estonia", "Hy Lạp", "Thổ Nhĩ Kỳ", "Ai Cập", "Nam Tư", "Tây Tạng",
    "Hồng Kông", "Đài Loan", "Ann Arbor", "New York",


    # --- 4. VĂN HÓA, NGHỆ THUẬT & GIẢI TRÍ ---
    "Lê Minh Sơn", "Thanh Lam", "Hà Trần", "Trần Tiến", "Nguyễn Văn Bình",
    "Cổ Thiên Lạc", "Trương Quốc Vinh", "Vương Gia Vệ", "Diệp Vấn", "Cung Nhị", "Mã Tam",
    "Major Lazer", "DJ Snake", "Lean On", "Assume Form",
    "Phật giáo Việt Nam", "Chùa Quang Hoa", "Chùa Thiền Quang", "Chùa Báo Ân", "Chùa Ba La Mật",


    # --- 5. SINH HỌC & Y HỌC ---
    "Khỉ thí nghiệm", "Khỉ vàng", "Khỉ đuôi dài", "Vắc-xin bại liệt",
    "Trầm cảm", "Setter Anh Quốc", "Táo Granny Smith", "Sâm Ngọc Linh",
    "Vũ khí sinh học", "Vũ khí hóa học", "Vũ khí hủy diệt hàng loạt",


    # --- 6. KINH TẾ & TOÁN LÝ ---
    "Tổng sản phẩm nội địa", "Lạm phát", "Lãi suất thực", "Khấu hao",
    "Khuynh hướng tiêu dùng biên", "Độ co giãn của cầu",
    "Sóng cơ", "Sóng dọc", "Sóng ngang", "Điện trở", "Định luật Ohm",
    "Lượng giác", "Hệ hai mức năng lượng", "Thuyết tương đối hẹp"
]


def clean_wiki_content(content):
    """Làm sạch nội dung Wikipedia."""
    content = re.sub(r'==\s*(Xem thêm|Tham khảo|Chú thích|Liên kết ngoài|Đọc thêm)\s*==.*', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'={2,}', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def get_existing_titles(file_path):
    """Đọc file hiện tại để lấy danh sách các tiêu đề đã có."""
    existing_titles = set()
    if not os.path.exists(file_path):
        return existing_titles
   
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Kiểm tra dòng bắt đầu bằng format tiêu đề mình quy định
                if line.startswith("Chủ đề: "):
                    # Lấy phần tên sau dấu hai chấm và xóa khoảng trắng thừa
                    title = line.replace("Chủ đề: ", "").strip()
                    existing_titles.add(title)
    except Exception as e:
        print(f"⚠️ Cảnh báo: Không thể đọc file cũ ({e}). Sẽ tạo file mới hoặc ghi đè.")
   
    return existing_titles


def crawl_wiki():
    wiki = wikipediaapi.Wikipedia(
        user_agent='VNPT_Hackathon_Bot/1.0 (test@example.com)',
        language=LANG,
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )


    # 1. Lấy danh sách bài đã có để tránh trùng lặp
    existing_titles = get_existing_titles(OUTPUT_FILE)
    print(f"📂 Đã tìm thấy {len(existing_titles)} bài viết có sẵn trong dữ liệu.")


    print(f"🕷️ Đang bắt đầu xử lý {len(TOPICS)} chủ đề...")
   
    new_articles_count = 0


    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        # Nếu file chưa có dữ liệu hoặc mới tạo, thêm header
        if os.path.getsize(OUTPUT_FILE) == 0:
            f.write("\n" + "="*50 + "\nDATA FROM WIKIPEDIA CRAWLER\n" + "="*50 + "\n\n")


        for topic in tqdm(TOPICS):
            page = wiki.page(topic)


            if page.exists():
                title = page.title.strip()


                # --- KIỂM TRA TRÙNG LẶP ---
                if title in existing_titles:
                    # Bỏ qua nếu đã có
                    continue


                # LÀM SẠCH NỘI DUNG
                content = clean_wiki_content(page.text)
               
                if len(content) < 100: continue


                # Ghi vào file
                entry = f"Chủ đề: {title}\n"
                entry += f"{content}\n"
                entry += "\n" + "-"*30 + "\n\n"
               
                f.write(entry)
               
                # Cập nhật danh sách đã có (để tránh trùng lặp ngay trong chính danh sách TOPICS đầu vào)
                existing_titles.add(title)
                new_articles_count += 1
            else:
                # Chỉ in lỗi nếu bài thực sự không tồn tại trên Wiki
                # print(f"⚠️ Không tìm thấy trên Wiki: {topic}")
                pass


    print(f"✅ Hoàn tất! Đã thêm mới {new_articles_count} bài viết vào {OUTPUT_FILE}.")


if __name__ == "__main__":
    if not os.path.exists("data"):
        os.makedirs("data")
       
    crawl_wiki()

