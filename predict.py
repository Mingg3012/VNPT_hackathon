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
BLACKLIST_KEYWORDS = ["sex", "khiêu dâm"] 
SAFE_ANSWER_DEFAULT = "A" # Mặc định trả về A (chữ cái)

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
        "mol", "phản ứng", "cân bằng", "khối lượng",
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


# =========================================================
# CLEAN OUTPUT (BẮT CHỮ CÁI)
# =========================================================

def clean_output(ans_text):
    # Regex tìm ký tự A, B, C, D (không phân biệt hoa thường)
    tag_match = re.search(r"<ans>\s*([A-Da-d])\s*</ans>", ans_text)
    if tag_match:
        return tag_match.group(1).upper()

    matches = re.findall(r"\b([A-Da-d])\b", ans_text)
    if matches:
        return matches[-1].upper()

    return SAFE_ANSWER_DEFAULT


# =========================================================
# GỌI LLM
# =========================================================

def call_vnpt_llm(prompt, model_type="small"):
    if model_type == "large":
        url = config.URL_LLM_LARGE
        headers = config.HEADERS_LARGE
        model = "vnptai_hackathon_large"
        max_tokens = 400
    else:
        url = config.URL_LLM_SMALL
        headers = config.HEADERS_SMALL
        model = "vnptai_hackathon_small"
        max_tokens = 150

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_completion_tokens": max_tokens,
    }

    for _ in range(5):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=40)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            elif r.status_code == 429:
                print("⏳ Rate limit, ngủ 60s...")
                time.sleep(60)
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)

    return ""


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

    CONTEXT_LENGTH_THRESHOLD = 1200
    model_to_use = "small"

    # --- Prompt chỉ thị LLM trả về chữ cái tương ứng ---
    instruction_text = "Hãy chọn đáp án đúng (tương ứng 0->A, 1->B, 2->C, 3->D, 3->D, 4->E, 5->F, 6->G, 7->H, 8->I, 9->J) và chỉ trả về chữ cái (A, B, C, D) trong thẻ <ans>."

    if q_type == "STEM":
        model_to_use = "large"
        prompt = f"""
        Bạn là một Giáo sư Khoa học Tự nhiên xuất sắc.

        --- THÔNG TIN BỔ TRỢ ---
        {context_text}

        Câu hỏi:
        {real_question}

        Các lựa chọn (đánh số từ 0):
        {choices_str}

        CHIẾN LƯỢC SUY LUẬN:
        1. Xác định dạng bài và công thức/định luật cần dùng.
        2. Trích xuất dữ kiện quan trọng.
        3. Thực hiện tính toán hoặc suy luận logic.
        4. SO KHỚP kết quả với TẤT CẢ các lựa chọn và loại trừ các phương án sai.
        5. Chọn phương án DUY NHẤT đúng nhất.

        YÊU CẦU ĐẦU RA:
        - Trình bày suy luận ngắn gọn.
        - {instruction_text}
        """
    else:
        if (
            len(context_text) > CONTEXT_LENGTH_THRESHOLD
            or q_type == "PRECISION"
            or is_reading_comprehension
        ):
            model_to_use = "large"

        prompt = f"""
        Bạn là chuyên gia phân tích thông tin.

        --- DỮ LIỆU THAM KHẢO (CONTEXT) ---
        {context_text}
        --- HẾT CONTEXT ---

        Câu hỏi:
        {real_question}

        Các lựa chọn (đánh số từ 0):
        {choices_str}

        NGUYÊN TẮC QUAN TRỌNG:
        - Nếu CONTEXT có thông tin liên quan trực tiếp: PHẢI ưu tiên CONTEXT.
        - Chỉ dùng kiến thức bên ngoài khi CONTEXT không đủ hoặc không liên quan.
        - Không được tự suy diễn trái với CONTEXT.

        CHIẾN LƯỢC:
        1. Tìm câu trong CONTEXT liên quan trực tiếp đến câu hỏi.
        2. Đối chiếu từng lựa chọn với CONTEXT.
        3. Loại trừ các phương án không khớp.
        4. Chọn đáp án đúng nhất.

        YÊU CẦU ĐẦU RA:
        {instruction_text}
        """

    ans = call_vnpt_llm(prompt, model_type=model_to_use)
    final_choice = clean_output(ans)

    return final_choice, context_text


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