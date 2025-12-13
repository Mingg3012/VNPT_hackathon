import wikipediaapi
import os
import re # Cần thêm thư viện Regex
from tqdm import tqdm

# --- CẤU HÌNH ---
OUTPUT_FILE = "data/documents.txt"
LANG = "vi"

# Danh sách từ khóa (Đã được giữ nguyên và là danh sách tốt)
TOPICS = [
    # --- 1. NHÂN VẬT LỊCH SỬ & CHÍNH TRỊ (Từ danh sách của bạn) ---
    "Hồ Chí Minh", "Võ Nguyên Giáp", "Trần Hưng Đạo", "Quang Trung", "Nguyễn Huệ",
    "Trần Nhân Tông", "Trần Thánh Tông", "Khâm Từ Hoàng", "Mạc Đăng Dung", "Mạc Đĩnh Chi",
    "Lê Chiêu Thống", "Nguyễn Hữu Chỉnh", "Trịnh Bồng", "Nguyễn Thái Học", # VNQDĐ
    "Tưởng Giới Thạch", "Hốt Tất Liệt", "Thành Cát Tư Hãn", "Tần Thủy Hoàng", "Càn Long",
    "François Mitterrand", "Saddam Hussein", "Gioan Phaolô II", "Friedrich Wilhelm", 
    "Augustine xứ Hippo", "Jacques Lacan",

    # --- 2. SỰ KIỆN & TỔ CHỨC (Quan trọng) ---
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

    # --- 5. SINH HỌC & Y HỌC (Cực kỳ quan trọng để sửa lỗi Safety) ---
    "Khỉ thí nghiệm", "Khỉ vàng", "Khỉ đuôi dài", "Vắc-xin bại liệt", 
    "Trầm cảm", "Setter Anh Quốc", "Táo Granny Smith", "Sâm Ngọc Linh",
    "Vũ khí sinh học", "Vũ khí hóa học", "Vũ khí hủy diệt hàng loạt",

    # --- 6. BỔ SUNG: KINH TẾ & TOÁN LÝ (Tool extract bị sót, BẮT BUỘC THÊM) ---
    "Tổng sản phẩm nội địa", "Lạm phát", "Lãi suất thực", "Khấu hao", 
    "Khuynh hướng tiêu dùng biên", "Độ co giãn của cầu", 
    "Sóng cơ", "Sóng dọc", "Sóng ngang", "Điện trở", "Định luật Ohm",
    "Lượng giác", "Hệ hai mức năng lượng", "Thuyết tương đối hẹp"
]

def clean_wiki_content(content):
    """
    Hàm làm sạch nội dung Wikipedia: 
    1. Loại bỏ các phần thừa (Tham khảo, Xem thêm).
    2. Loại bỏ các ký tự markup còn sót lại.
    3. Chuẩn hóa khoảng trắng.
    """
    # 1. Loại bỏ các phần không cần thiết (Tham khảo, Chú thích, v.v.)
    # Dùng re.DOTALL để khớp với nội dung nhiều dòng
    content = re.sub(r'==\s*(Xem thêm|Tham khảo|Chú thích|Liên kết ngoài|Đọc thêm)\s*==.*', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Xóa các ký tự markup Wikipedia còn sót lại (như '=== Tiêu đề ===')
    content = re.sub(r'={2,}', '', content)
    
    # 3. Thay thế nhiều dòng trống bằng 2 dòng trống (chuẩn hóa chunking)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

def crawl_wiki():
    # Cấu hình User Agent (Bắt buộc)
    wiki = wikipediaapi.Wikipedia(
        user_agent='VNPT_Hackathon_Bot/1.0 (test@example.com)',
        language=LANG,
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )

    print(f"🕷️ Đang bắt đầu cào dữ liệu cho {len(TOPICS)} chủ đề...")
    
    # Mở file để ghi nối (append mode 'a')
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        
        # Thêm dòng phân cách
        f.write("\n\n" + "="*50 + "\nDATA FROM WIKIPEDIA CRAWLER\n" + "="*50 + "\n\n")

        for topic in tqdm(TOPICS):
            page = wiki.page(topic)

            if page.exists():
                title = page.title
                # LÀM SẠCH NỘI DUNG TẠI ĐÂY
                content = clean_wiki_content(page.text)
                
                # Bỏ qua nếu nội dung sau khi làm sạch quá ngắn
                if len(content) < 100: continue 

                # 1. Thêm tiêu đề rõ ràng
                entry = f"Chủ đề: {title}\n"
                entry += f"{content}\n"
                entry += "\n" + "-"*30 + "\n\n" # Dấu ngăn cách giữa các bài
                
                # Ghi vào file
                f.write(entry)
            else:
                print(f"⚠️ Không tìm thấy bài viết: {topic}")

    print(f"✅ Đã cào xong! Dữ liệu được thêm vào: {OUTPUT_FILE}")

if __name__ == "__main__":
    # Kiểm tra thư mục data
    if not os.path.exists("data"):
        os.makedirs("data")
        
    crawl_wiki()