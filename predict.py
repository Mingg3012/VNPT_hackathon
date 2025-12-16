import json
import re
import time
import requests
import chromadb
from tqdm import tqdm
import config # File config của bạn
import sys
import pandas as pd

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# --- CẤU HÌNH ---
BLACKLIST_KEYWORDS = [

    # 1. Tình dục – khiêu dâm
    "sex", "tình dục", "khiêu dâm", "khiêu dâm trẻ em", "dâm ô",
    "hiếp dâm", "cưỡng hiếp", "quan hệ tình dục", "mại dâm",
    "kích dục", "ảnh nóng", "clip nóng", "porn", "xxx",
    "thủ dâm", "loạn luân", "mua dâm", "bán dâm",

    # 2. Ma túy – chất cấm
    "ma túy", "heroin", "cocaine", "cần sa", "thuốc lắc", "meth",
    "buôn bán ma túy", "sử dụng ma túy", "chất gây nghiện",
    "chích ma túy", "trồng cần sa", "pha chế ma túy",

    # 3. Cờ bạc – cá độ
    "cờ bạc", "đánh bạc", "cá độ", "lô đề", "xổ số lậu",
    "casino", "đánh bài ăn tiền", "đánh bạc online",
    "cá cược", "nhà cái", "1xbet", "fun88", "m88", "w88", "fb88", "8xbet", "bet365", "onbet", "letou", "melbet", "men88",

    # 4. Bạo lực – giết chóc – khủng bố
    "khủng bố", "đánh bom", "ám sát", "giết người",
    "thảm sát", "chặt đầu", "xả súng",
    "bom", "mìn", "súng", "tấn công vũ trang",
    "chế tạo bom", "chế tạo vũ khí",

    # 5. Vũ khí & chiến tranh (phi học thuật)
    "vũ khí sinh học", "vũ khí hóa học", "vũ khí hạt nhân",
    "chế tạo vũ khí", "mua bán vũ khí",
    "sử dụng vũ khí", "buôn lậu vũ khí",

    # 6. Tự tử – tự hại – rối loạn tâm lý nguy cấp
    "tự tử", "tự sát", "tự hại", "muốn chết",
    "kết liễu bản thân", "uống thuốc tự tử",
    "nhảy lầu", "cắt cổ tay",

    # 7. Hacking – an ninh mạng – xâm nhập trái phép
    "hacking", "hack", "bẻ khóa", "crack",
    "xâm nhập trái phép", "đánh cắp dữ liệu",
    "tấn công mạng", "ddos", "phishing",
    "keylogger", "malware", "virus máy tính",
    "chiếm quyền điều khiển",

    # 8. Lừa đảo – tội phạm kinh tế – tài chính
    "lừa đảo", "chiếm đoạt tài sản", "đa cấp",
    "rửa tiền", "tham nhũng", "hối lộ",
    "trốn thuế", "làm giả giấy tờ",
    "lừa đảo trực tuyến", "lừa đảo chiếm đoạt",
    "gian lận tài chính",

    # 9. Thù hận – xúc phạm – phân biệt
    "phân biệt chủng tộc", "kỳ thị", "thù hằn",
    "xúc phạm", "lăng mạ", "miệt thị",
    "chửi bới", "bôi nhọ", "vu khống",
    "kích động thù ghét",

    # 10. Chính trị cực đoan / chống phá (ngoài học thuật)
    "lật đổ", "chống phá nhà nước",
    "biểu tình bạo loạn", "bạo loạn",
    "ly khai", "khai quốc riêng",
    "tuyên truyền phản động",
    "chủ nghĩa cực đoan",

    # 11. Tội phạm con người & gia đình
    "mua bán người", "buôn người",
    "xâm hại trẻ em", "bạo hành gia đình",
    "bắt cóc", "tra tấn", "ngược đãi",

    # 12. Hành vi trái pháp luật khác
    "vi phạm pháp luật", "hành vi phạm tội",
    "che giấu tội phạm", "tiêu thụ tài sản phạm pháp",
    "đường dây tội phạm",

    # 13. Xâm phạm quyền riêng tư & Doxing (Đánh cắp danh tính)
    "lộ thông tin", "doxing", "tìm info", "tra cứu thông tin cá nhân",
    "số cccd", "số chứng minh thư", "lộ clip riêng tư", "xin link",
    "quay lén", "camera quay lén", "theo dõi vị trí",
    "ăn cắp danh tính", "giả mạo danh tính",

    # 14. Tin giả, Deepfake & Thao túng thông tin
    "deepfake", "ghép mặt", "giả giọng nói", "fake news",
    "tin giả", "tung tin đồn thất thiệt", "thuyết âm mưu",
    "chỉnh sửa ảnh nhạy cảm", "ghép ảnh nóng",

    # 15. Hàng cấm & Động vật hoang dã (Ngoài vũ khí/ma túy)
    "ngà voi", "sừng tê giác", "mật gấu", "vảy tê tê",
    "động vật sách đỏ", "buôn lậu động vật",
    "tiền giả", "in tiền giả", "tiền âm phủ (lừa đảo)",
    "làm bằng giả", "làm giấy tờ giả", "bằng lái xe giả",

    # 16. Bắt nạt qua mạng (Cyberbullying) & Quấy rối
    "bóc phốt", "tẩy chay", "dìm hàng", "ném đá hội đồng",
    "body shaming", "miệt thị ngoại hình", "công kích cá nhân",
    "stalking", "bám đuôi", "quấy rối tin nhắn", "đe dọa tung ảnh",

    # 17. Tệ nạn xã hội & Dịch vụ phi pháp khác
    "đòi nợ thuê", "siết nợ", "tín dụng đen", "vay nặng lãi",
    "bốc bát họ", "cho vay lãi cắt cổ",
    "mang thai hộ (thương mại)", "đẻ thuê", "bán thận", "bán nội tạng",
    "kết hôn giả", "vượt biên trái phép",

    # 18. Từ lóng/Viết tắt thường dùng để lách luật (Cần cập nhật liên tục)
    "kẹo ke" , "bay lắc", "xào ke", "hàng trắng", "đá", "ma túy đá",
    "bánh" , "heroin", "gà móng đỏ" , "mại dâm", "checker" , "người mua dâm check hàng",
    "sugar baby", "sugar daddy" , "biến tướng mại dâm",
    "fwd" , "chuyển tiếp tin nhắn nhạy cảm",
    "child porn",  "ấu dâm",

    # 19. Vi phạm bản quyền & Phần mềm lậu (Piracy & Warez)
    "crack win", "crack office", "bẻ khóa phần mềm",
    "xem phim lậu", "web phim lậu", "tải game crack",
    "torrent", "warez", 
    "phần mềm gián điệp", "tool hack game",

    # 20. Gian lận thi cử & Học thuật (Academic Dishonesty)
    # (Đặc biệt lưu ý vì bạn là giảng viên)
    "thi hộ", "học hộ", "làm bài thuê", "viết luận văn thuê",
    "mua bằng đại học", "làm giả bằng cấp", "chạy điểm",
    "phao thi", "tai nghe siêu nhỏ", "camera cúc áo",
    "mua đề thi", "lộ đề thi",
    "bán bài giải", "chia sẻ đáp án thi",
    "ghostwriter", "dịch vụ viết thuê",
    "mua code mẫu", "bán code mẫu",

    # 21. Y tế sai lệch & Sức khỏe độc hại (Misinformation)
    "anti-vax", "tẩy chay vắc xin", "chữa ung thư bằng thực dưỡng",
    "thực phẩm chức năng giả", "thuốc tiên", "chữa bách bệnh",
    "thuốc kích dục nữ", "thuốc mê", "bán thuốc phá thai",
    "pro-ana", "móc họng giảm cân",

    # 22. Lừa đảo tuyển dụng & Việc làm (Job Scams)
    "việc nhẹ lương cao", "ngồi nhà kiếm tiền", "cộng tác viên shopee",
    "chốt đơn nhận hoa hồng", "làm nhiệm vụ like tiktok",
    "nạp tiền nhận thưởng", "đầu tư sinh lời 100%",
    "xuất khẩu lao động chui", "vượt biên đi làm",

    # 23. Phân biệt vùng miền (Regional Discrimination - Rất gắt ở VN)
    
    "parky", "nam cầy", "tộc cối",
    "phân biệt vùng miền", "pbvm",

    # 24. Tôn giáo mê tín & Tà giáo (Cults & Superstition)
    "bùa ngải", "yểm bùa", "nuôi kumanthong", "chơi ngải",
    "hội thánh đức chúa trời", "tà đạo", "truyền đạo trái phép",
    "lên đồng lừa đảo", "trục vong thu tiền",

    # 25. Từ khóa lóng/Code mới của giới trẻ (Gen Z Slang - Cập nhật)
     "ons", "fwb" ,
    "trà xanh" , "tiểu tam",
    "xếp hình" , "chịch", "xoạc",
    "nứng", "hứng", "buscu", "vét máng", # Từ lóng thô tục

    # 26. Các loại bom/vũ khí tự chế (Improvised Weapons)
    "bom xăng", "bom khói", "chế pháo", "thuốc pháo",
    "dao phóng lợn", "mã tấu", "kiếm nhật",
    "súng cồn", "súng bắn bi", "ná thun sát thương",

    # 27. Khai thác trẻ vị thành niên & grooming
"grooming", "dụ dỗ trẻ em", "chat sex với trẻ em",
"kết bạn trẻ em", "rủ trẻ em đi chơi",
"quan hệ với trẻ vị thành niên",

# 28. Tấn công sinh học – hóa học (chi tiết nguy hiểm)
"nuôi vi khuẩn", "tạo virus", "phát tán dịch bệnh",
"chế tạo chất độc", "phát tán khí độc",
"vũ khí sinh học tự chế",

# 29. Hướng dẫn phạm tội (HOW-TO)
"cách giết người", "cách trốn công an",
"cách phi tang xác", "cách rửa tiền",
"cách lừa đảo", "cách hack",
"cách tẩu thoát", "hướng dẫn phạm tội",

# 30. Trốn tránh pháp luật & kỹ thuật né kiểm soát
"né thuế", "lách luật", "chuyển tiền bất hợp pháp",
"tẩu tán tài sản", "né kiểm tra",
"đối phó công an", "đối phó thanh tra",

# 31. Thao túng tâm lý & ép buộc
"tẩy não", "thao túng tâm lý",
"ép buộc quan hệ", "khống chế tinh thần",
"đe dọa tinh thần",

# 32. Nội dung khiêu khích – kích động tập thể
"kêu gọi đánh", "kêu gọi giết",
"kích động đám đông", "kích động bạo lực",
"kêu gọi trả thù",

# 33. Xâm phạm an ninh – cơ sở hạ tầng
"phá hoại hệ thống", "tấn công hạ tầng",
"phá hoại điện lưới", "phá hoại mạng",
"đánh sập hệ thống",

# 34. Mua bán – trao đổi dịch vụ bất hợp pháp
"mua bán dữ liệu", "mua bán thông tin cá nhân",
"mua tài khoản ngân hàng",
"bán sim rác", "thuê tài khoản ngân hàng",
"thuê đứng tên công ty",

# 35. Nội dung kích động thù ghét theo giới tính/xu hướng
"kỳ thị giới tính", "ghét người đồng tính",
"chống lgbt", "kỳ thị lgbt",
"miệt thị giới",

# 36. Nội dung xuyên tạc lịch sử – phủ nhận tội ác
"phủ nhận holocaust", "xuyên tạc lịch sử",
"bịa đặt lịch sử", "chối bỏ tội ác chiến tranh",

# 37. Gian lận thương mại & tiêu dùng
"bán hàng giả", "hàng fake",
"làm giả nhãn hiệu", "bán thuốc giả",
"quảng cáo sai sự thật",

# 38. Nội dung lợi dụng thiên tai – dịch bệnh
"lợi dụng dịch bệnh", "trục lợi cứu trợ",
"lừa đảo cứu trợ", "bán thuốc giả mùa dịch",

# 39. Nội dung thao túng truyền thông – dư luận
"seeding bẩn", "thao túng dư luận",
"định hướng dư luận", "dẫn dắt dư luận",
"bơm tin giả",

# 40. Nội dung gây hoảng loạn xã hội
"gây hoang mang", "lan truyền hoảng loạn",
"kích động sợ hãi", "đe dọa đánh bom",

# 41. Lạm dụng AI & deepfake nâng cao
"giả mạo bằng ai", "deepfake chính trị",
"giả giọng lãnh đạo", "tạo video giả",
"mạo danh bằng ai",

# 42. Nội dung phá hoại đạo đức học đường
"bắt nạt học sinh", "đánh học sinh",
"làm nhục học sinh", "quay clip đánh bạn",

# 43. Giao dịch tiền điện tử bất hợp pháp
"rửa tiền crypto", "trộn tiền",
"mixer crypto", "ẩn danh tiền điện tử",
"lừa đảo tiền ảo",

# 44. Nội dung kích dục trá hình
"phim 18+", "truyện 18+",
"chat 18+", "video nóng",
"ảnh nhạy cảm",

# 45. Từ khóa lách kiểm duyệt (pattern nguy hiểm)
"s e x", "p*rn", "p0rn", "s3x",
"h@ck", "cr@ck", "m@ túy",
"b0m", "v!rus", "ph!shing",
# --- Sex / Porn ---
    "s e x", "s.e.x", "s-e-x", "s_e_x", "s  e  x",
    "se x", "sx", "s3x", "s€x", "s*x", "s^x", "5ex",
    "p o r n", "p.o.r.n", "p-o-r-n", "p_o_r_n",
    "porn0", "p0rn", "pörn", "p*rn", "pr0n", "p0rno",
    "xxx", "x x x", "x.x.x", "x-x-x",
    "hentai", "h e n t a i", "h3ntai",
    "jav", "j a v", "j4v",
    "nude", "n u d e", "n00d", "n00ds", "nudes",
    "nsfw", "n s f w",
    "18+", "1 8 +", "18plus", "18 plus",
    "onlyfans", "0nlyfans", "only f@ns",

    # --- Drugs ---
    "m a t u y", "m.a.t.u.y", "m-a-t-u-y", "m_a_t_u_y",
    "m@ tuy", "m@ túy", "m@tuy", "m@túy",
    "ma tuy", "ma tuý", "ma tuý", "ma túy",
    "hàng trắng", "h@ng tr@ng", "hang trang",
    "kẹo", "k e o", "k3o", "kẹo ke", "k€o",
    "đá", "d a", "d@", "da", "m@ túy đá", "matuyda",
    "cần sa", "c@n s@", "can sa", "c4n s4",
    "weed", "w e e d", "w33d",
    "meth", "m e t h", "m3th",
    "heroin", "h e r o i n", "h3roin",
    "cocaine", "c0caine", "coca1ne",

    # --- Gambling / betting ---
    "c o b a c", "cờ b@c", "co bac", "c0 bac",
    "đánh bạc", "d@nh b@c", "danh bac",
    "cá độ", "c@ d0", "ca do", "c4 d0",
    "lô đề", "lo de", "l0 de", "l* de",
    "nhà cái", "nh@ c@i", "nha cai",
    "bet", "b e t", "b3t",
    "1x b e t", "1xbet", "1 x b e t",
    "fun88", "f u n 8 8", "fún88",
    "w88", "w 8 8", "fb88", "8xbet", "bet365",

    # --- Hacking / cybercrime ---
    "h a c k", "h.a.c.k", "h-a-c-k", "h_a_c_k",
    "h@ck", "h4ck", "ha ck",
    "crack", "cr@ck", "cr4ck", "c r a c k",
    "bẻ khóa", "b3 kh0a", "be khoa",
    "phishing", "ph!shing", "ph1shing", "p h i s h i n g",
    "ddos", "d d o s", "d-d-o-s", "d0s",
    "keylogger", "k e y l o g g e r", "k3ylogger",
    "malware", "m a l w a r e", "m@lware",
    "trojan", "tr0jan", "t r o j a n",

    # --- Weapons / bomb ---
    "b o m", "b.o.m", "b-o-m", "b_0_m",
    "b0m", "b@m", "bom xăng", "bom xang",
    "mìn", "m i n", "m1n",
    "súng", "s u n g", "sú ng", "súng tự chế",
    "đạn", "d a n", "d@n",
    "chế pháo", "che phao", "ch3 phao",

    # --- Suicide / self-harm ---
    "t u tu", "tự t.ử", "tự tủ", "t.u.t.u",
    "tu tu", "tự sát", "t u s a t",
    "cắt cổ tay", "cat co tay", "c@t co t@y",
    "uống thuốc", "uong thuoc", "u0ng thu0c",

    # --- Hate / slurs (VN obfuscations) ---
    "p a r k y", "p@rky", "par-ky",
    "n a m c a y", "n@m c@y", "nam-cay",
    "t o c c o i", "t0c c0i", "tộc cối", "t0c c0i"

]

SAFE_ANSWER_DEFAULT = "A" # Mặc định trả về A (chữ cái)
PARSE_FAIL_FLAG = "X"

# =========================================================
# KẾT NỐI VECTOR DB
# =========================================================

try:
    client = chromadb.PersistentClient(path="./vector_db")
    collection = client.get_or_create_collection(name="vnpt_knowledge")
except Exception:
    collection = None


# =========================================================
# EMBEDDING
# =========================================================

def get_embedding_for_search(text):
    payload = {
        "model": "vnptai_hackathon_embedding",
        "input": text,
        "encoding_format": "float",
    }

    for _ in range(3):
        try:
            resp = requests.post(
                config.URL_EMBEDDING,
                headers=config.HEADERS_EMBED,
                json=payload,
                timeout=5,
            )
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
        except Exception:
            time.sleep(0.5)

    return None


# =========================================================
# PHÂN LOẠI CÂU HỎI & AN TOÀN
# =========================================================

def detect_question_type_and_safety(question):
    q_lower = question.lower()

    for bad_word in BLACKLIST_KEYWORDS:
        if bad_word in q_lower:
            return "UNSAFE"

    stem_keywords = [
        "tính", "giá trị", "phương trình", "hàm số", "biểu thức",
        "xác suất", "thống kê", "log", "sin", "cos", "tan", "cot",
        "đạo hàm", "tích phân", "nguyên hàm", "vector", "ma trận",
        "vận tốc", "gia tốc", "lực", "điện trở", "năng lượng", "công suất",
        "lãi suất", "gdp", "lạm phát", "cung cầu", "độ co giãn",
        "mol", "phản ứng", "cân bằng", "khối lượng", "latex", "$", "\\frac" 
        ]

    if any(k in q_lower for k in stem_keywords):
        return "STEM"

    precision_keywords = [
        "năm nào", "ngày nào", "ai là", "người nào", "ở đâu",
        "bao nhiêu", "số lượng", "thời gian nào",
        "nghị định", "luật", "thông tư", "điều khoản", "hiến pháp",
        "thủ đô", "di tích", "chiến dịch", "hiệp định",
    ]

    if any(k in q_lower for k in precision_keywords):
        return "PRECISION"

    return "NORMAL"


def clean_output(ans_text):
    # 1. Xử lý trường hợp ans_text là None (Lỗi Server/Key/429/Timeout)
    if ans_text is None:
        # Trả về None: Dùng để kích hoạt Fallback trong solve_question
        return None 

    # 2. Xử lý trường hợp ans_text là chuỗi rỗng "" (Lỗi 400 Content Filter)
    if ans_text == "":
        # Trả về "Z": Dùng để báo hiệu CẤM TRẢ LỜI trong solve_question
        return "Z"
    
    # Kể từ đây, ans_text là một chuỗi không rỗng
    if not isinstance(ans_text, str):
        # Trường hợp input không phải chuỗi, coi là lỗi Parsing/format
        return PARSE_FAIL_FLAG # Trả về "X"

    ans_text = ans_text.strip()

    # ... (các bước parsing bằng regex) ...

    tag_match = re.search(
        r"<ans>\s*([A-Ja-j])\s*</ans>",
        ans_text,
        re.IGNORECASE
    )
    if tag_match:
        return tag_match.group(1).upper()

    mid_match = re.search(
        r"(đáp án|answer|ans)\s*[:\-]?\s*\(?([A-Ja-j])\)?",
        ans_text,
        re.IGNORECASE
    )
    if mid_match:
        return mid_match.group(2).upper()

    last_match = re.search(
        r"\b([A-Ja-j])\s*[\.\)\]]*\s*$",
        ans_text,
        re.IGNORECASE
    )
    if last_match:
        return last_match.group(1).upper()

    # 3. Fallback cuối cùng nếu parsing thất bại (ĐÃ SỬA)
    # Trả về cờ "X" để Fallback logic trong solve_question biết đây là lỗi Parse
    return PARSE_FAIL_FLAG


# =========================================================
# GỌI LLM
# =========================================================

def call_vnpt_llm(prompt, model_type="small", temperature=0.0):
    # ... (Phần xác định url, headers, và payload giữ nguyên) ...
    if model_type == "large":
        url = config.URL_LLM_LARGE
        headers = config.HEADERS_LARGE
        model_name = "vnptai_hackathon_large"
    else:
        url = config.URL_LLM_SMALL
        headers = config.HEADERS_SMALL
        model_name = "vnptai_hackathon_small"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_completion_tokens": 20,
        "stop": ["</ans>", "\n"]
    }
    
    # Thực hiện request 1 LẦN duy nhất
    try:
        r = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        if r.status_code == 200:
            try:
                data = r.json() 
            except Exception as e:
                print(f"❌ {model_type.upper()} Lỗi parse JSON: {e}")
                return None
            
            # ✅ KIỂM TRA LỖI NỘI DUNG 400 TRONG PHẢN HỒI 200 OK
            if "error" in data and data["error"].get("code") == 400:
                print(f"❌ {model_type.upper()} Content Filter trả về lỗi 400 trong payload 200.")
                return "" 
            
            # --- XỬ LÝ PHẢN HỒI THÀNH CÔNG ---
            if "choices" not in data:
                print(f"⚠️ {model_type.upper()} response thiếu key 'choices'. Phản hồi đầy đủ:", data)
                return None 
            
            # ... (thêm các kiểm tra an toàn khác nếu cần) ...

            return data["choices"][0]["message"]["content"]


        if r.status_code == 401:
            print(f"❌ {model_type.upper()} 401 – Hết quota / quyền")
            return None

        # ❌ BỎ QUA LOGIC RETRY CHO 429 (Chỉ xử lý 1 lần)
        if r.status_code == 429:
            print(f"❌ {model_type.upper()} rate limit (429) → Dừng lại.")
            return None
            
        if r.status_code == 400:
             # Lỗi 400 Content Filter
             print(f"❌ {model_type.upper()} 400 – Lỗi Content Filter.")
             return ""

        print(f"⚠️ {model_type.upper()} HTTP {r.status_code}: {r.text}")
        # Nếu là lỗi HTTP khác (5xx, v.v.), chỉ cần dừng lại và trả về None
        return None 

    except requests.exceptions.ReadTimeout:
        # ❌ BỎ QUA LOGIC RETRY CHO TIMEOUT (Chỉ xử lý 1 lần)
        print(f"❌ {model_type.upper()} timeout → Dừng lại.")
        return None
        
    except Exception as e:
        print(f"❌ {model_type.upper()} Lỗi không xác định: {e}")
        return None




# =========================================================
# GIẢI CÂU HỎI
# =========================================================

def solve_question(item):
    question = item["question"]
    choices = item["choices"]

    q_type = detect_question_type_and_safety(question)

    if q_type == "UNSAFE":
        return SAFE_ANSWER_DEFAULT, "N/A (UNSAFE QUESTION/FILTERED)"

    context_text = ""
    real_question = question
    is_reading_comprehension = "Đoạn thông tin:" in question

    if is_reading_comprehension:
        parts = question.split("Câu hỏi:")
        context_text = parts[0].strip()
        real_question = parts[1].strip() if len(parts) > 1 else question
    elif collection:
        query_vec = get_embedding_for_search(real_question)
        if query_vec:
            results = collection.query(
                query_embeddings=[query_vec],
                n_results=5,
            )
            if results["documents"]:
                docs = results["documents"][0]
                context_text = "\n---\n".join(docs)

    # --- GIỮ NGUYÊN format choices (0. ..., 1. ...) cho đỡ mất công ---
    choices_str = (
        "\n. ".join([f"{i}. {v}" for i, v in enumerate(choices)])
        if isinstance(choices, list)
        else str(choices)
    )

    # --- Prompt chỉ thị LLM trả về chữ cái tương ứng ---
    instruction_text = "Hãy chọn đáp án đúng (tương ứng 0->A, 1->B, 2->C, 3->D, 4->E, 5->F, 6->G, 7->H, 8->I, 9->J) và chỉ trả về chữ cái (A, B, C, D, E, F, G, H, I, J). BẮT BUỘC: Đáp án cuối cùng phải nằm trong thẻ <ans>, ví dụ: <ans>A</ans>."

    if q_type == "STEM":
        prompt = f"""
        Bạn là Giáo sư Khoa học Tự nhiên. Nhiệm vụ: Giải bài tập một cách CHÍNH XÁC TUYỆT ĐỐI.
        Không được đoán. Không được suy diễn ngoài dữ kiện.



        --- CÔNG THỨC & KIẾN THỨC BỔ TRỢ (CONTEXT) ---

        CHỈ được sử dụng công thức và kiến thức xuất hiện trong CONTEXT dưới đây.
        Nếu không có công thức phù hợp trong CONTEXT → không được tự suy ra công thức khác.

        {context_text}



        --- BÀI TOÁN ---

        Câu hỏi: {real_question}

        Các lựa chọn (Index từ 0):
        {choices_str}



        --- QUY TRÌNH GIẢI (BẮT BUỘC TUÂN THEO) ---

        1. Xác định DUY NHẤT công thức/định lý cần dùng từ CONTEXT.
        2. Trích xuất CHÍNH XÁC tất cả các giá trị số và đơn vị trong đề bài.
        3. Thực hiện tính toán nội bộ.
        4. ĐỐI CHIẾU kết quả tính được với TỪNG lựa chọn:
        - Loại bỏ các đáp án sai đơn vị.
        - Loại bỏ các đáp án không khớp giá trị.
        5. Chỉ chọn đáp án khớp CHÍNH XÁC nhất với kết quả tính toán.
        6. Nếu không có đáp án nào khớp chính xác → chọn đáp án KHỚP NHẤT VỀ GIÁ TRỊ VÀ ĐƠN VỊ
            nhưng CHỈ khi sai số nhỏ và có thể do làm tròn số.
            Nếu không → vẫn chọn đáp án khớp nhất về ĐƠN VỊ.




        --- KIỂM TRA LẠI (SELF-CHECK) ---

        Trước khi trả lời:
        - Tự kiểm tra lại phép tính một lần.
        - Đảm bảo index được chọn đúng với nội dung đáp án.



        --- YÊU CẦU ĐẦU RA (BẮT BUỘC) ---

        - KHÔNG trình bày lời giải.
        - KHÔNG giải thích.
        - Đáp án trả về dựa trên hướng dẫn sau: {instruction_text}
        """

    else:

        prompt = f"""
        Bạn là chuyên gia phân tích thông tin. Nhiệm vụ: trả lời câu hỏi
        CHỈ dựa trên văn bản được cung cấp. Không dùng kiến thức bên ngoài.



        --- VĂN BẢN THAM KHẢO (CONTEXT) ---

        {context_text}



        --- CÂU HỎI ---

        {real_question}



        --- CÁC LỰA CHỌN ---

        {choices_str}



        --- BƯỚC 1: PHÂN LOẠI CÂU HỎI (THỰC HIỆN NỘI BỘ) ---

        Xác định câu hỏi thuộc loại nào:
        A. Truy xuất thông tin trực tiếp
        (ai, khi nào, ở đâu, sự kiện gì, nhân vật nào...)
        B. Nhận định / đánh giá / theo ngữ cảnh
        (vai trò, ý nghĩa, nhận xét, đánh giá, nguyên nhân...)



        --- BƯỚC 2: CHIẾN LƯỢC THEO LOẠI ---

        [TRƯỜNG HỢP A – TRUY XUẤT THÔNG TIN]

        - Chỉ chọn thông tin được nêu TRỰC TIẾP trong CONTEXT.
        - Nếu CONTEXT có câu trả lời trùng khớp rõ ràng với câu hỏi → PHẢI chọn đáp án đó.
        - KHÔNG:
        + suy luận
        + chọn người/sự kiện cùng nhóm
        + chọn thông tin liên quan gián tiếp

        Ví dụ cấm:
        - Câu hỏi hỏi 1 nhân vật → không chọn nhân vật khác trong cùng danh sách.



        [TRƯỜNG HỢP B – NHẬN ĐỊNH / THEO NGỮ CẢNH]

        - Đọc TOÀN BỘ đoạn liên quan.
        - Xác định các LUỒNG QUAN ĐIỂM nếu có (ủng hộ / phản đối).
        - Ưu tiên đáp án phản ánh ĐẦY ĐỦ ngữ cảnh.
        - Không chọn đáp án:
        + chỉ đúng một phía
        + hoặc không được CONTEXT hỗ trợ rõ ràng.



        --- BƯỚC 3: KIỂM TRA CUỐI (BẮT BUỘC) ---

        Trước khi trả lời, tự kiểm tra:
        - Đáp án có được nêu trực tiếp hoặc suy ra rõ ràng từ CONTEXT không?
        - Có đáp án nào khớp TRỰC TIẾP hơn không?
        - Có chọn nhầm người/sự kiện cùng nhóm không?



        --- YÊU CẦU ĐẦU RA (BẮT BUỘC) ---

        - KHÔNG giải thích.
        - Đáp án trả về dựa trên hướng dẫn sau: {instruction_text}
        """

    # ================================
    # 1️⃣ LUÔN GỌI SMALL TRƯỚC
    # ================================
    ans_small = call_vnpt_llm(prompt, model_type="small", temperature=0.0)
    final_choice = clean_output(ans_small) # final_choice là A-J, None, Z, hoặc X

    # --- KIỂM TRA LỖI 400 NGAY LẬP TỨC (Dấu hiệu: Z) ---
    if final_choice == "Z":
        print("🛑 Small LLM bị Content Filter. Trả về rỗng theo yêu cầu.")
        return "", context_text # Trả về chuỗi rỗng ""

    # ================================
    # 2️⃣ FALLBACK LARGE (SỬA LỖI LOGIC)
    # ================================
    # Kích hoạt Fallback nếu: 
    # A. Lỗi Server/Key/Timeout (final_choice == None)
    # HOẶC
    # B. Lỗi Parsing/Vô nghĩa (final_choice == PARSE_FAIL_FLAG "X")
    
    if final_choice is None or final_choice == PARSE_FAIL_FLAG: 
        
        print(f"🔄 Fallback SMALL → LARGE (Nguyên nhân: {'Lỗi Server/Key' if final_choice is None else 'Lỗi Format'})")
        
        ans_large = call_vnpt_llm(prompt, model_type="large", temperature=0.0)
        large_choice = clean_output(ans_large)

        # --- KIỂM TRA LỖI 400 CỦA LARGE ---
        if large_choice == "Z":
            print("🛑 Large LLM bị Content Filter. Trả về rỗng theo yêu cầu.")
            return "", context_text 

        # --- GÁN KẾT QUẢ LARGE HOẶC GÁN MẶC ĐỊNH ---
        # Nếu Large trả lời thành công (không phải None, không phải X), dùng kết quả Large
        if large_choice is not None and large_choice != PARSE_FAIL_FLAG:
             final_choice = large_choice # Cập nhật kết quả (A-J)
        else:
             # Nếu Large cũng thất bại, trả về đáp án mặc định an toàn
             final_choice = SAFE_ANSWER_DEFAULT
    
    # --- BƯỚC CUỐI CÙNG: ĐẢM BẢO LUÔN CÓ KẾT QUẢ HỢP LỆ ---
    # Nếu Small thành công, nó sẽ nhảy qua Fallback và final_choice đã là A-J.
    # Nếu Fallback xảy ra, final_choice đã được gán A-J hoặc SAFE_ANSWER_DEFAULT.
    
    # Trường hợp duy nhất cần kiểm tra lại là nếu có lỗi logic không lường trước.
    if final_choice is None or final_choice == PARSE_FAIL_FLAG:
        final_choice = SAFE_ANSWER_DEFAULT
        
    return final_choice, context_text


# print("TEST SMALL:")
# print(call_vnpt_llm("Chỉ trả lời <ans>A</ans>", "small"))

# print("TEST LARGE:")
# print(call_vnpt_llm("Chỉ trả lời <ans>A</ans>", "large"))


if __name__ == "__main__":
    # --- 1. CẤU HÌNH ---
    MODE = "LOCAL"
    INPUT_FILE_PATH = "data/val.json" 
    OUTPUT_FILE_PATH = "submission_local.csv"
    MAX_QUESTIONS_TO_PROCESS = None 
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'docker':
            MODE = "DOCKER"
            INPUT_FILE_PATH = "/code/private_test.json" 
            OUTPUT_FILE_PATH = "submission.csv"
        
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
             MAX_QUESTIONS_TO_PROCESS = int(sys.argv[2])
        elif len(sys.argv) > 1 and sys.argv[1].isdigit():
            MAX_QUESTIONS_TO_PROCESS = int(sys.argv[1])
    
    print(f"🚀 Chế độ: {MODE} | Input: {INPUT_FILE_PATH}")
    
    try:
        # --- 2. ĐỌC DỮ LIỆU ---
        try:
            with open(INPUT_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) 
        except (json.JSONDecodeError, FileNotFoundError):
             df = pd.read_csv(INPUT_FILE_PATH)
             data = df.to_dict('records')
            
        total_data_length = len(data)
        data_to_process = data[:MAX_QUESTIONS_TO_PROCESS] if MAX_QUESTIONS_TO_PROCESS else data
        IS_FULL_RUN = len(data_to_process) == total_data_length
        IS_VAL_MODE = (MODE == "LOCAL" and "val.json" in INPUT_FILE_PATH)

        if MODE == "LOCAL" and not IS_FULL_RUN:
            print(f"⚠️ Debug: Đang chạy {len(data_to_process)}/{total_data_length} câu.")
        
        # --- 3. XỬ LÝ ---
        submission_results = []
        correct_count = 0
        wrong_cases = []
        
        print("🔄 Đang xử lý câu hỏi...")
        for item in tqdm(data_to_process):
            item_id = item.get("id", item.get("qid")) 

            # B1: Gọi hàm xử lý (LLM trả về A, B, C, D)
            pred_char, retrieved_context = solve_question(item)
            
            # B2: Lưu kết quả
            submission_results.append({
                "qid": item_id,
                "answer": pred_char
            })
            
            # B3: Tính điểm (So sánh trực tiếp, không map gì cả)
            if IS_VAL_MODE:
                # Đáp án thật trong file JSON đã là chữ cái (A, B, C...)
                true_char = str(item.get('answer', '?')).strip().upper()
                
                if pred_char == true_char:
                    correct_count += 1
                else:
                    wrong_cases.append({
                        "qid": item_id,
                        "question": item['question'],
                        "true_char": true_char,
                        "pred_char": pred_char,
                        "retrieved_context": retrieved_context 
                    })

        # --- 4. GHI FILE ---
        df = pd.DataFrame(submission_results)

        if MODE == "DOCKER" or (MODE == "LOCAL" and IS_FULL_RUN):
            df.to_csv(OUTPUT_FILE_PATH, index=False, encoding='utf-8')
            print(f"\n✅ Đã lưu file kết quả: {OUTPUT_FILE_PATH}")
        else:
            print("\n💾 Debug xong (Không ghi file CSV).")

        # --- 5. TỔNG KẾT ---
        print("\n" + "="*40)
        if IS_VAL_MODE:
            acc = (correct_count / len(data_to_process)) * 100
            print(f"🏆 Accuracy (Tập Val): {acc:.2f}%")
            
            if wrong_cases:
                pd.DataFrame(wrong_cases).to_csv("wrong_answers.csv", index=False, encoding='utf-8')
                print(f"⚠️ Đã lưu {len(wrong_cases)} câu sai vào 'wrong_answers.csv'")
        elif MODE == "DOCKER":
            print("✅ Docker Run Complete.")
        else:
            print("🏁 Test Run Complete.")
        print("="*40)
            
    except Exception as e:
        print(f"❌ Lỗi Nghiêm Trọng: {e}")