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
    "tình dục", "khiêu dâm", "khiêu dâm trẻ em", "dâm ô",
    "hiếp dâm", "cưỡng hiếp", "mại dâm", "kích dục", 
    "ảnh nóng", "clip nóng", "thủ dâm", "loạn luân", 
    "mua dâm", "bán dâm", "ấu dâm", 

    # # 2. Ma túy – chất cấm
    # "heroin", "cocaine", "cần sa", "thuốc lắc", "meth",
    # "buôn bán ma túy", "chích ma túy", "pha chế ma túy",
    
    # # 3. Cờ bạc – cá độ (Giữ các nhà cái nổi bật)
    # "cờ bạc", "đánh bạc", "cá độ", "lô đề", "xổ số lậu",
    # "đánh bài ăn tiền", "nhà cái", 
    # "1xbet", "fun88", "m88", "w88", "fb88", "8xbet", "bet365", "onbet", "letou", "melbet", "men88",

    # # 4. Bạo lực – giết chóc – khủng bố
    # "khủng bố", "đánh bom", "ám sát", "giết người",
    # "thảm sát", "chặt đầu", "xả súng",
    # "chế tạo bom", "chế tạo vũ khí",

    # # 5. Vũ khí & chiến tranh (phi học thuật)
    # # Giữ các từ liên quan đến chế tạo/buôn bán
    # "chế tạo vũ khí", "mua bán vũ khí",
    # "buôn lậu vũ khí",

    # # 6. Tự tử – tự hại – rối loạn tâm lý nguy cấp
    # "tự tử", "tự sát", "tự hại", "muốn chết",
    # "kết liễu bản thân", "uống thuốc tự tử",
    # "nhảy lầu", "cắt cổ tay",

    # # 7. Hacking – an ninh mạng – xâm nhập trái phép
    # "hacking", "hack", "bẻ khóa", "crack",
    # "xâm nhập trái phép", "đánh cắp dữ liệu",
    # "tấn công mạng", "ddos", "phishing",
    # "keylogger", "malware", "virus máy tính",
    # "chiếm quyền điều khiển",

    # # 8. Lừa đảo – tội phạm kinh tế – tài chính
    # "lừa đảo", "chiếm đoạt tài sản", "đa cấp",
    # "rửa tiền", "tham nhũng", "hối lộ",
    # "trốn thuế", "làm giả giấy tờ",
    # "lừa đảo trực tuyến", "gian lận tài chính",

    # # 9. Thù hận – xúc phạm – phân biệt
    # "phân biệt chủng tộc", "kỳ thị", "thù hằn",
    # "xúc phạm", "lăng mạ", "miệt thị",
    # "chửi bới", "bôi nhọ", "vu khống",
    # "kích động thù ghét",

    # # 10. Chính trị cực đoan / chống phá (ngoài học thuật)
    # "lật đổ", "chống phá nhà nước",
    # "biểu tình bạo loạn", "bạo loạn",
    # "ly khai", "tuyên truyền phản động",
    # "chủ nghĩa cực đoan",

    # # 11. Tội phạm con người & gia đình
    # "mua bán người", "buôn người",
    # "xâm hại trẻ em", "bạo hành gia đình",
    # "bắt cóc", "tra tấn", "ngược đãi",

    # # 12. Hành vi trái pháp luật khác
    # "vi phạm pháp luật", "hành vi phạm tội",
    # "che giấu tội phạm", "tiêu thụ tài sản phạm pháp",
    # "đường dây tội phạm",

    # # 13. Xâm phạm quyền riêng tư & Doxing
    # "doxing", "tìm info", "tra cứu thông tin cá nhân",
    # "số cccd", "số chứng minh thư", "lộ clip riêng tư", 
    # "quay lén", "camera quay lén", "theo dõi vị trí",
    # "ăn cắp danh tính", "giả mạo danh tính",

    # # 14. Tin giả, Deepfake & Thao túng thông tin
    # "deepfake", "ghép mặt", "giả giọng nói", 
    # "tung tin đồn thất thiệt", "chỉnh sửa ảnh nhạy cảm", "ghép ảnh nóng",

    # # 15. Hàng cấm & Động vật hoang dã
    # "ngà voi", "sừng tê giác", "mật gấu", "vảy tê tê",
    # "động vật sách đỏ", "buôn lậu động vật",
    # "tiền giả", "in tiền giả", 
    # "làm bằng giả", "làm giấy tờ giả", "bằng lái xe giả",

    # # 16. Bắt nạt qua mạng (Cyberbullying) & Quấy rối
    # "bóc phốt", "tẩy chay", "dìm hàng", "ném đá hội đồng",
    # "body shaming", "miệt thị ngoại hình", "công kích cá nhân",
    # "stalking", "bám đuôi", "quấy rối tin nhắn", "đe dọa tung ảnh",

    # # 17. Tệ nạn xã hội & Dịch vụ phi pháp khác
    # "đòi nợ thuê", "siết nợ", "tín dụng đen", "vay nặng lãi",
    # "bốc bát họ", "cho vay lãi cắt cổ",
    # "mang thai hộ (thương mại)", "đẻ thuê", "bán thận", "bán nội tạng",
    # "kết hôn giả", "vượt biên trái phép",

    # # 18. Từ lóng/Viết tắt thường dùng để lách luật
    # "kẹo ke" , "bay lắc", "xào ke", "hàng trắng", "đá", "ma túy đá",
    # "gà móng đỏ" , "mại dâm", "checker" , 
    # "sugar baby", "sugar daddy" , 
    # "child porn",  
    
    # # 19. Vi phạm bản quyền & Phần mềm lậu (Tập trung vào hành vi)
    # "crack win", "crack office", "bẻ khóa phần mềm",
    # "xem phim lậu", "tải game crack",
    # "tool hack game",

    # # 20. Gian lận thi cử & Học thuật (Giữ các hành vi trực tiếp)
    # "thi hộ", "học hộ", "làm bài thuê", "viết luận văn thuê",
    # "mua bằng đại học", "làm giả bằng cấp", "chạy điểm",
    # "phao thi", "tai nghe siêu nhỏ", "camera cúc áo",
    # "mua đề thi", "lộ đề thi",
    # "ghostwriter", "dịch vụ viết thuê",

    # # 21. Y tế sai lệch & Sức khỏe độc hại
    # "thuốc kích dục nữ", "thuốc mê", "bán thuốc phá thai",
    # "pro-ana", "móc họng giảm cân",

    # # 22. Lừa đảo tuyển dụng & Việc làm
    # "việc nhẹ lương cao", "ngồi nhà kiếm tiền", 
    # "nạp tiền nhận thưởng", "đầu tư sinh lời 100%",
    # "xuất khẩu lao động chui",

    # # 23. Phân biệt vùng miền (Giữ các từ nhạy cảm trực tiếp)
    # "parky", "nam cầy", "tộc cối",
    # "phân biệt vùng miền", "pbvm",

    # # 24. Tôn giáo mê tín & Tà giáo
    # "bùa ngải", "yểm bùa", "nuôi kumanthong", "chơi ngải",
    # "hội thánh đức chúa trời", "tà đạo", "truyền đạo trái phép",
    # "lên đồng lừa đảo", "trục vong thu tiền",

    # # 25. Từ khóa lóng/Code mới của giới trẻ (Chỉ giữ từ lóng thô tục)
    # "xếp hình" , "chịch", "xoạc",
    # "nứng", "hứng", "buscu", "vét máng",

    # # 26. Các loại bom/vũ khí tự chế (Tập trung vào chế tạo/nguy hiểm)
    # "bom xăng", "bom khói", "chế pháo", "thuốc pháo",
    # "dao phóng lợn", "mã tấu", "kiếm nhật",
    # "súng cồn", "súng bắn bi", "ná thun sát thương",

    # # 27. Khai thác trẻ vị thành niên & grooming (Giữ nguyên)
    # "grooming", "dụ dỗ trẻ em", "chat sex với trẻ em",
    # "quan hệ với trẻ vị thành niên",

    # # 28. Tấn công sinh học – hóa học (Giữ nguyên)
    # "nuôi vi khuẩn", "tạo virus", "phát tán dịch bệnh",
    # "chế tạo chất độc", "phát tán khí độc",
    # "vũ khí sinh học tự chế",

    # # 29. Hướng dẫn phạm tội (HOW-TO) - Tăng cường
    # "cách giết người", "cách trốn công an",
    # "cách phi tang xác", "cách rửa tiền",
    # "cách lừa đảo", "cách hack",
    # "cách tẩu thoát", "hướng dẫn phạm tội",

    # # 30. Trốn tránh pháp luật & kỹ thuật né kiểm soát (Giữ nguyên)
    # "né thuế", "lách luật", "chuyển tiền bất hợp pháp",
    # "tẩu tán tài sản", "né kiểm tra",
    # "đối phó công an", "đối phó thanh tra",

    # # 31. Thao túng tâm lý & ép buộc (Giữ nguyên)
    # "tẩy não", "thao túng tâm lý",
    # "ép buộc quan hệ", "khống chế tinh thần",
    # "đe dọa tinh thần",

    # # 32. Nội dung khiêu khích – kích động tập thể (Giữ nguyên)
    # "kêu gọi đánh", "kêu gọi giết",
    # "kích động đám đông", "kích động bạo lực",
    # "kêu gọi trả thù",

    # # 33. Xâm phạm an ninh – cơ sở hạ tầng (Giữ nguyên)
    # "phá hoại hệ thống", "tấn công hạ tầng",
    # "phá hoại điện lưới", "phá hoại mạng",
    # "đánh sập hệ thống",

    # # 34. Mua bán – trao đổi dịch vụ bất hợp pháp (Giữ nguyên)
    # "mua bán dữ liệu", "mua bán thông tin cá nhân",
    # "mua tài khoản ngân hàng",
    # "bán sim rác", "thuê tài khoản ngân hàng",
    # "thuê đứng tên công ty",

    # # 35. Nội dung kích động thù ghét theo giới tính/xu hướng (Giữ nguyên)
    # "kỳ thị giới tính", "ghét người đồng tính",
    # "chống lgbt", "kỳ thị lgbt",
    # "miệt thị giới",

    # # 36. Nội dung xuyên tạc lịch sử – phủ nhận tội ác (Giữ nguyên)
    # "phủ nhận holocaust", "xuyên tạc lịch sử",
    # "bịa đặt lịch sử", "chối bỏ tội ác chiến tranh",

    # # 37. Gian lận thương mại & tiêu dùng (Giữ nguyên)
    # "bán hàng giả", "hàng fake",
    # "làm giả nhãn hiệu", "bán thuốc giả",
    # "quảng cáo sai sự thật",

    # # 39. Nội dung thao túng truyền thông – dư luận (Giữ nguyên)
    # "seeding bẩn", "thao túng dư luận",
    # "định hướng dư luận", "dẫn dắt dư luận",
    # "bơm tin giả",

    # # 40. Nội dung gây hoảng loạn xã hội (Giữ nguyên)
    # "gây hoang mang", "lan truyền hoảng loạn",
    # "kích động sợ hãi", "đe dọa đánh bom",

    # # 41. Lạm dụng AI & deepfake nâng cao (Giữ nguyên)
    # "giả mạo bằng ai", "deepfake chính trị",
    # "giả giọng lãnh đạo", "tạo video giả",
    # "mạo danh bằng ai",

    # 42. Nội dung phá hoại đạo đức học đường (Giữ nguyên)
    "bắt nạt học sinh", "đánh học sinh",
    "làm nhục học sinh", "quay clip đánh bạn",

    # # 43. Giao dịch tiền điện tử bất hợp pháp (Giữ nguyên)
    # "rửa tiền crypto", "trộn tiền",
    # "mixer crypto", "ẩn danh tiền điện tử",
    # "lừa đảo tiền ảo",

    # 44. Nội dung kích dục trá hình (Giữ nguyên)
    "phim 18+", "truyện 18+",
    "chat 18+", "video nóng",
    "ảnh nhạy cảm",

    # # 45. Từ khóa lách kiểm duyệt (pattern nguy hiểm) - Chỉ giữ các mẫu phổ biến
    # "s3x", "p0rn", "h@ck", "cr@ck", "m@tuy", "m@túy",
    # "b0m", "v!rus", "ph!shing",
    # "s-e-x", "s.e.x", "s_e_x", 
    # "p-o-r-n", "p_o_r_n", "p0rno",
    # "n00d", "n00ds", "nudes",
    # "18+", "1 8 +", 
    # "onlyfans", "0nlyfans", 
    # "m@ tuy", "m@ túy",
    # "h@ng tr@ng", "k3o", "kẹo ke", 
    # "c@n s@", "c4n s4",
    # "w33d", "m3th", "h3roin",
    # "c0caine", "c0 bac", "c@ d0", 
    # "l0 de", "h4ck", "cr4ck", "b3 kh0a",
    # "ph!shing", "ph1shing", 
    # "b0m", "b@m", "b0m xang",
    # "m1n", "sú ng",
    # "t.u.t.u", "tự t.ử", "tủ t.u",
    # "c@t co t@y", "u0ng thu0c",
    # "p@rky", "n@m c@y", "t0c c0i",

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

def detect_question_type(question):
    q_lower = question.lower()

    # 1. PRECISION CRITICAL (UNSAFE) - Ưu tiên cao nhất
    for bad_word in BLACKLIST_KEYWORDS:
        if bad_word in q_lower:
            return "PRECISION_CRITICAL"

    # 2. RAG (Đọc hiểu văn bản dài có sẵn trong đề)
    # Dấu hiệu: Có từ khóa báo hiệu đoạn văn
    rag_signals = ["đoạn thông tin:", "dựa vào văn bản", "đọc đoạn sau", "thông tin dưới đây:"]
    if any(s in q_lower for s in rag_signals) or len(question) > 500: # Hoặc câu hỏi quá dài
        return "RAG_LONG_TEXT"

    # 3. STEM (Toán & Logic)
    stem_keywords = [
        "tính", "giá trị", "phương trình", "hàm số", "biểu thức",
        "xác suất", "thống kê", "log", "sin", "cos", "tan", 
        "đạo hàm", "tích phân", "vector", "ma trận",
        "vận tốc", "gia tốc", "lực", "công suất", "mol", "phản ứng",
        "tọa độ", "hình học", "tam giác", "số đo", "$", "\\frac"
    ]
    if any(k in q_lower for k in stem_keywords):
        return "STEM"

    # 4. COMPULSORY (Sự kiện, Con số, Địa danh cụ thể - Cần chính xác 100%)
    compulsory_keywords = [
        "năm nào", "ngày nào", "ai là", "tên là gì", "người nào", "ở đâu",
        "bao nhiêu", "số lượng", "thủ đô", "tỉnh nào", "thành phố nào",
        "điều khoản", "luật số", "nghị định", "hiến pháp", "ngày tháng",
        "chiến dịch nào", "hiệp định nào", "tác giả nào"
    ]
    if any(k in q_lower for k in compulsory_keywords):
        return "COMPULSORY"

    # 5. MULTIDOMAIN (Còn lại)
    return "MULTIDOMAIN"


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
            timeout=30,
        )

        if r.status_code == 200:
            try:
                data = r.json() 
            except Exception as e:
                print(f"❌ {model_type.upper()} Lỗi parse JSON: {e}")
                return None

            # ✅ KIỂM TRA LỖI NỘI DUNG 400 TRONG PHẢN HỒI 200 OK (AN TOÀN HƠN)
            if "error" in data:
                error_obj = data["error"]
                # Kiểm tra nếu error là dict và có code 400
                if isinstance(error_obj, dict) and error_obj.get("code") == 400:
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

    # --- 1. PHÂN LOẠI CÂU HỎI & CHECK SAFETY INPUT ---
    q_type = detect_question_type(question) 

    # [CRITICAL] Nếu từ khóa vi phạm -> Chặn ngay lập tức
    if q_type == "PRECISION_CRITICAL":
        return "", "N/A (BLOCKED - KEYWORD)"

    # --- 2. CHUẨN BỊ CONTEXT ---
    context_text = ""
    real_question = question
    
    # TRƯỜNG HỢP A: RAG Đọc hiểu (Văn bản nằm ngay trong đề bài)
    if q_type == "RAG_LONG_TEXT" and "Câu hỏi:" in question:
        parts = question.split("Câu hỏi:")
        context_text = parts[0].strip()
        real_question = parts[1].strip()
    
    # TRƯỜNG HỢP B: Tìm trong DB (Đã bỏ Translation, chỉ Search trực tiếp)
    elif collection:
        # Tạo vector từ câu hỏi gốc
        query_vec = get_embedding_for_search(real_question)
        
        if query_vec:
            # Truy vấn DB
            results = collection.query(
                query_embeddings=[query_vec],
                n_results=5, # Lấy 5 đoạn liên quan nhất
            )
            
            if results["documents"]:
                docs = results["documents"][0]
                # Gộp các đoạn lại thành context thô
                context_text = "\n---\n".join(docs)

    # --- 3. FORMAT ĐẦU VÀO CHO PROMPT ---
    choices_str = "\n".join([f"{i}. {v}" for i, v in enumerate(choices)]) if isinstance(choices, list) else str(choices)
    
    instruction_text = """
    ### YÊU CẦU ĐẦU RA (QUAN TRỌNG) ###
    - Chỉ trả về duy nhất một chữ cái đại diện đáp án (A, B, C, D...) nằm trong thẻ <ans>.
    - Ví dụ: <ans>A</ans>
    - TUYỆT ĐỐI KHÔNG giải thích, KHÔNG trình bày lời giải ra ngoài thẻ.
    """

    # --- 4. TẠO PROMPT THEO TỪNG LOẠI (CÓ BƯỚC REFINEMENT BẮT BUỘC) ---

    # ================= TYPE 1: STEM (Toán học / Logic) =================
    if q_type == "STEM":
        prompt = f"""
        Bạn là Giáo sư Khoa học Tự nhiên. Nhiệm vụ: Giải bài tập CHÍNH XÁC TUYỆT ĐỐI.
        
        --- DỮ LIỆU THÔ (RAW CONTEXT) ---
        {context_text}

        --- BƯỚC 1: LÀM SẠCH VÀ TRÍCH XUẤT (BẮT BUỘC) ---
        Dữ liệu thô có thể chứa thông tin rác hoặc lỗi định dạng. Hãy thực hiện:
        1. Lọc bỏ các ký tự lạ, header/footer không liên quan.
        2. Trích xuất chính xác các công thức toán/lý/hóa và hằng số quan trọng.
        3. Viết lại đề bài và dữ kiện dưới dạng ngắn gọn, chuẩn xác nhất.

        --- BƯỚC 2: GIẢI BÀI TOÁN (DỰA TRÊN DỮ LIỆU ĐÃ LÀM SẠCH) ---
        Câu hỏi: {real_question}
        Lựa chọn:
        {choices_str}

        Quy trình:
        1. Sử dụng công thức đã trích xuất ở Bước 1.
        2. Thay số và tính toán nội bộ (Double-check kết quả).
        3. Đối chiếu kết quả với các lựa chọn.
        
        {instruction_text}
        """

    # ================= TYPE 2: COMPULSORY (Tra cứu sự thật / Chính xác) =================
    elif q_type == "COMPULSORY":
        prompt = f"""
        Bạn là Chuyên gia Tra cứu Dữ liệu (Fact-Checker). 
        Nhiệm vụ: Tìm đáp án chính xác từng ký tự/con số. KHÔNG ĐƯỢC SUY ĐOÁN.

        --- DỮ LIỆU THÔ (RAW CONTEXT) ---
        {context_text}

        --- BƯỚC 1: TÁI CẤU TRÚC THÔNG TIN (REFINEMENT) ---
        1. Đọc Context thô, loại bỏ các đoạn văn rác/không có nghĩa.
        2. Tìm kiếm và làm nổi bật các thực thể: Năm, Tên người, Địa danh, Số liệu, Điều luật.
        3. Sắp xếp lại thông tin theo trình tự thời gian hoặc logic.

        --- BƯỚC 2: ĐỐI CHIẾU ---
        Câu hỏi: {real_question}
        Lựa chọn:
        {choices_str}

        Quy trình:
        1. So khớp keywords trong câu hỏi với Thông tin đã tái cấu trúc.
        2. Chọn đáp án có thông tin TRÙNG KHỚP HOÀN TOÀN.
        
        {instruction_text}
        """

    # ================= TYPE 3: RAG_LONG_TEXT (Đọc hiểu văn bản) =================
    elif q_type == "RAG_LONG_TEXT":
        prompt = f"""
        Bạn là Trợ lý Đọc hiểu. Nhiệm vụ: Trả lời câu hỏi CHỈ DỰA TRÊN văn bản cung cấp.

        --- VĂN BẢN NGUỒN ---
        {context_text}

        --- BƯỚC 1: ĐỊNH VỊ VÀ LÀM RÕ ---
        1. Xác định đoạn văn chứa thông tin trả lời trong Văn bản nguồn.
        2. Tự tóm tắt ý nghĩa của đoạn văn đó (bỏ qua các từ ngữ gây nhiễu).

        --- BƯỚC 2: TRẢ LỜI ---
        Câu hỏi: {real_question}
        Lựa chọn:
        {choices_str}

        Quy trình:
        1. So sánh ý nghĩa tóm tắt với các lựa chọn.
        2. Chọn đáp án diễn đạt lại (paraphrase) đúng nhất.
        
        {instruction_text}
        """

    # ================= TYPE 4: MULTIDOMAIN (Đa lĩnh vực / Normal) =================
    else: # MULTIDOMAIN
        prompt = f"""
        Bạn là Chuyên gia Phân tích Tổng hợp. Nhiệm vụ: Chọn đáp án phù hợp nhất theo ngữ cảnh.

        --- DỮ LIỆU THÔ (RAW CONTEXT) ---
        {context_text}

        --- BƯỚC 1: LÀM SẠCH VÀ TỔNG HỢP ---
        1. Loại bỏ thông tin rác (số trang, tiêu đề lặp lại, ký tự lỗi).
        2. Tóm tắt các ý chính liên quan đến chủ đề câu hỏi.

        --- BƯỚC 2: PHÂN TÍCH ---
        Câu hỏi: {real_question}
        Lựa chọn:
        {choices_str}

        Quy trình:
        1. Dùng thông tin đã làm sạch để trả lời.
        2. Nếu thiếu thông tin trực tiếp, dùng tư duy logic suy luận từ các manh mối còn lại.
        
        {instruction_text}
        """

    # --- 5. GỌI LLM & XỬ LÝ KẾT QUẢ ---

    # [CHIẾN LƯỢC CHO STEM]: Gọi thẳng LARGE
    if q_type == "STEM":
        print(f"🧮 STEM detected: Dùng trực tiếp LARGE model.")
        
        ans_large = call_vnpt_llm(prompt, model_type="large", temperature=0.0)
        
        # Check lỗi Content Filter (trả về rỗng)
        if ans_large == "": 
            print("🛑 STEM bị chặn (Content Filter). Trả về rỗng.")
            return "", context_text

        final_choice = clean_output(ans_large)
        
        if final_choice is None or final_choice == "X":
            final_choice = "A" # Default
            
        return final_choice, context_text

    # [CHIẾN LƯỢC CHO CÁC LOẠI KHÁC]: SMALL -> Fallback LARGE
    else:
        # B1: Gọi Small
        ans_small = call_vnpt_llm(prompt, model_type="small", temperature=0.0)
        
        if ans_small == "": # Check Filter
            print("🛑 Small LLM bị chặn. Trả về rỗng.")
            return "", context_text

        final_choice = clean_output(ans_small)

        # B2: Fallback Large
        if final_choice is None or final_choice == "X":
            print(f"🔄 Fallback SMALL -> LARGE ({q_type})")
            
            ans_large = call_vnpt_llm(prompt, model_type="large", temperature=0.0)
            
            if ans_large == "": # Check Filter Large
                print("🛑 Large LLM (Fallback) bị chặn. Trả về rỗng.")
                return "", context_text
                
            large_choice = clean_output(ans_large)
            
            if large_choice is not None and large_choice != "X":
                 final_choice = large_choice
            else:
                 final_choice = "A" # Safe Default

        return final_choice, context_text


# print("TEST SMALL:")
# print(call_vnpt_llm("Chỉ trả lời <ans>A</ans>", "small"))

# print("TEST LARGE:")
# print(call_vnpt_llm("Chỉ trả lời <ans>A</ans>", "large"))


if __name__ == "__main__":
    # --- 1. CẤU HÌNH ---
    MODE = "LOCAL"
    INPUT_FILE_PATH = "data/test.json" 
    OUTPUT_FILE_PATH = "submission_3.csv"
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