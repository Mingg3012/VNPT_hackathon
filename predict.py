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
BLACKLIST_KEYWORDS = ["sex", "khiêu dâm", "ma túy", "cờ bạc", "lừa đảo", "khủng bố", "tự tử", "hacking", "phân biệt chủng tộc", "xúc phạm", "lăng mạ"] 
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

    for attempt in range(3):
        try:
            r = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if r.status_code == 200:
                data = r.json() # ✅ Thêm dòng này
                # ... (xử lý 200) ...
                return data["choices"][0]["message"]["content"]


            if r.status_code == 401:
                print(f"❌ {model_type.upper()} 401 – Hết quota / quyền")
                return None

            # SỬA LỖI 429: Sử dụng thời gian chờ tăng dần
            if r.status_code == 429:
                wait_time = 60 + (attempt * 60) 
                print(f"⏳ {model_type.upper()} rate limit → ngủ {wait_time}s")
                time.sleep(wait_time)
                continue
                
            if r.status_code == 400:
                 # Logic này đã đúng: Dừng retry vì prompt không thay đổi
                 print(f"❌ {model_type.upper()} 400 – Lỗi Content Filter. Dừng retry.")
                 return ""

            print(f"⚠️ {model_type.upper()} HTTP {r.status_code}: {r.text}")
            time.sleep(5)

        except requests.exceptions.ReadTimeout:
            print(f"⏳ {model_type.upper()} timeout → retry")
            time.sleep(5)

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