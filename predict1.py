import json
import re
import time
import requests
import chromadb
from tqdm import tqdm
import config # File config của bạn
import sys
import pandas as pd
from enum import Enum

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# --- ENUM ĐỊNH NGHĨA 5 DOMAINS ---
class DomainType(Enum):
    """5 domain types for adaptive prompting"""
    PRECISION_CRITICAL = "precision_critical"  # Black list words - don't answer
    COMPULSORY = "compulsory"                   # Common sense questions
    RAG = "rag"                                 # Retrieval-Augmented Generation
    STEM = "stem"                               # Science, Technology, Engineering, Math
    MULTI_DOMAIN = "multi_domain"               # History, Economics, Law, Culture, Art, University

# --- CẤU HÌNH ---
# 1. PRECISION_CRITICAL - Black list từ khóa (bảo mật, cá nhân)
PRECISION_CRITICAL_KEYWORDS = {
    'mật khẩu', 'password', 'tài khoản ngân hàng', 'số tài khoản', 'mã pin', 'pin',
    'số căn cước', 'số cmnd', 'chứng minh nhân dân', 'thông tin cá nhân bảo mật',
    'bí mật quốc phòng', 'tài liệu mật', 'classified', 'tài chính cá nhân',
    'sex', 'khiêu dâm', 'hướng dẫn chế tạo vũ khí', 'cách làm bom', 'công thức thuốc nổ'
}

# 2. STEM - Khoa học, Công nghệ, Kỹ thuật, Toán học
STEM_KEYWORDS = {
    'tính', 'giá trị', 'phương trình', 'hàm số', 'biểu thức',
    'xác suất', 'thống kê', 'log', 'sin', 'cos', 'tan', 'cot',
    'đạo hàm', 'tích phân', 'nguyên hàm', 'vector', 'ma trận',
    'vận tốc', 'gia tốc', 'lực', 'điện trở', 'năng lượng', 'công suất',
    'mol', 'phản ứng', 'cân bằng', 'khối lượng', 'hoá chất', 'hoá học',
    'enzyme', 'protein', 'dna', 'gen', 'tế bào', 'sinh học', 'vi khuẩn',
    'latex', '$', '\\\\frac', 'công thức', 'chứng minh'
}

# 3. LỊCH SỬ VIỆT NAM
VIETNAM_HISTORY_KEYWORDS = {
    'lịch sử', 'chiến tranh', 'độc lập', 'phong kiến', 'đại việt',
    'vua', 'hoàng đế', 'triều đại', 'ngô', 'đinh', 'lý', 'trần', 'tây sơn',
    'nguyễn', 'thực dân pháp', 'pháp thuộc', '1945', '1954', '1975',
    'cộng hòa', 'xã hội chủ nghĩa', 'cộng hòa xã hội chủ nghĩa'
}

# 4. PHÁP LUẬT VIỆT NAM
VIETNAM_LAW_KEYWORDS = {
    'pháp luật', 'luật', 'điều', 'khoản', 'bộ luật', 'hình sự', 'dân sự',
    'hành chính', 'lao động', 'thuế', 'giao thông', 'tư pháp', 'tòa án',
    'công tố viên', 'tội phạm', 'hình phạt', 'hiến pháp', 'pháp lệnh',
    'quy định', 'quyết định', 'thông tư', 'nghị định'
}

# 5. VĂN HÓA VIỆT NAM
VIETNAM_CULTURE_KEYWORDS = {
    'văn hóa', 'truyền thống', 'phong tục', 'tập quán', 'lễ hội', 'tết',
    'nôm na', 'chữ nôm', 'văn học', 'thơ', 'nhân vật văn học', 'tác phẩm',
    'anh hùng', 'tín ngưỡng', 'tôn giáo', 'đạo phật', 'ca trù', 'múa lân',
    'ngôn ngữ', 'tiếng việt'
}

# 6. KINH TẾ VIỆT NAM
VIETNAM_ECONOMICS_KEYWORDS = {
    'kinh tế', 'thương mại', 'buôn bán', 'nông nghiệp', 'công nghiệp',
    'công ty', 'doanh nghiệp', 'bao cấp', 'đổi mới', 'thị trường', 'hàng hóa',
    'tiền tệ', 'lạm phát', 'tăng trưởng', 'xuất khẩu', 'nhập khẩu', 'ngân hàng'
}

# 7. COMPULSORY - Câu hỏi lý thuyết cơ bản
COMPULSORY_KEYWORDS = {
    'là gì', 'cái gì', 'ai là', 'khi nào', 'ở đâu', 'bao nhiêu',
    'định nghĩa', 'ý nghĩa', 'tác dụng', 'chức năng', 'đặc điểm',
    'phân biệt', 'so sánh', 'khác biệt', 'giống nhau'
}

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
# PHÂN LOẠI CÂU HỎI VÀO 5 DOMAINS
# =========================================================

def detect_domain(question: str) -> DomainType:
    """
    Detect the domain of a question based on keywords and scoring.
    Returns one of 5 DomainType: PRECISION_CRITICAL, COMPULSORY, RAG, STEM, MULTI_DOMAIN
    """
    question_lower = question.lower()
    
    # 1. Check PRECISION_CRITICAL first (Black list words)
    for keyword in PRECISION_CRITICAL_KEYWORDS:
        if keyword.lower() in question_lower:
            return DomainType.PRECISION_CRITICAL
    
    # 2. Score each domain
    stem_score = sum(1 for keyword in STEM_KEYWORDS if keyword.lower() in question_lower)
    history_score = sum(1 for keyword in VIETNAM_HISTORY_KEYWORDS if keyword.lower() in question_lower)
    law_score = sum(1 for keyword in VIETNAM_LAW_KEYWORDS if keyword.lower() in question_lower)
    culture_score = sum(1 for keyword in VIETNAM_CULTURE_KEYWORDS if keyword.lower() in question_lower)
    economics_score = sum(1 for keyword in VIETNAM_ECONOMICS_KEYWORDS if keyword.lower() in question_lower)
    compulsory_score = sum(1 for keyword in COMPULSORY_KEYWORDS if keyword.lower() in question_lower)
    
    multi_domain_score = history_score + law_score + culture_score + economics_score
    
    # 3. Decision logic (priority order)
    if stem_score >= 2:
        return DomainType.STEM
    elif multi_domain_score >= 2:
        return DomainType.MULTI_DOMAIN
    elif compulsory_score >= 1 and stem_score == 0:
        return DomainType.COMPULSORY
    elif multi_domain_score >= 1:
        return DomainType.MULTI_DOMAIN
    elif stem_score >= 1:
        return DomainType.STEM
    else:
        # Default to RAG for general questions or reading comprehension
        return DomainType.RAG


def get_prompt_for_domain(domain: DomainType, context_text: str, real_question: str, choices_str: str, instruction_text: str) -> str:
    """
    Generate domain-specific prompt strategy.
    """
    
    
    if domain == DomainType.COMPULSORY:
        # Common sense / Definition questions
        prompt = f"""
Bạn là một chuyên gia giáo dục. Nhiệm vụ: Trả lời câu hỏi lý thuyết dựa vào định nghĩa, khái niệm cơ bản và lẫy lý chung.

Câu hỏi: {real_question}

Các lựa chọn:
{choices_str}

--- CHIẾN LƯỢC ---
1. Hiểu rõ định nghĩa của các khái niệm trong câu hỏi.
2. Chọn đáp án phù hợp nhất với định nghĩa hoặc ý nghĩa cơ bản.
3. Tránh suy đoán, chỉ dùng kiến thức nền tảng.

--- YÊU CẦU ĐẦU RA ---
- KHÔNG giải thích dài, lan man.
- {instruction_text}
"""
    
    elif domain == DomainType.STEM:
        # Scientific / Math / Engineering approach
        prompt = f"""
Bạn là Giáo sư Khoa học Tự nhiên. Nhiệm vụ: Giải bài tập chính xác tuyệt đối bằng phương pháp khoa học.

--- CÔNG THỨC & KIẾN THỨC BỔ TRỢ (CONTEXT) ---
{context_text}

--- BÀI TOÁN ---
Câu hỏi: {real_question}

Các lựa chọn:
{choices_str}

--- HƯỚNG DẪN GIẢI ---
1. Xác định công thức/định lý từ CONTEXT cần dùng.
2. Trích xuất các con số từ Câu hỏi (Lưu ý đơn vị).
3. Thực hiện tính toán nội bộ một cách chính xác.
4. Chỉ chọn MỘT đáp án duy nhất khớp kết quả.

--- YÊU CẦU ĐẦU RA ---
- KHÔNG trình bày lời giải dài dòng.
- KHÔNG giải thích dài.
- {instruction_text}
"""
    
    elif domain == DomainType.MULTI_DOMAIN:
        # History, Law, Culture, Economics - Vietnamese context
        prompt = f"""
Bạn là chuyên gia về Lịch sử Việt Nam, Pháp luật Việt Nam, Văn hóa Việt Nam, và Kinh tế Việt Nam.
Nhiệm vụ: Trả lời dựa vào kiến thức chuyên sâu về Việt Nam.

--- THÔNG TIN THAM KHẢO ---
{context_text}

--- CÂU HỎI ---
Câu hỏi: {real_question}

Các lựa chọn:
{choices_str}

--- CHIẾN LƯỢC ---
1. Tìm thông tin trong CONTEXT khớp với từ khóa câu hỏi.
2. Chọn đáp án ĐƯỢC HỖ TRỢ BỞI CONTEXT.
3. Dùng kiến thức lịch sử Việt Nam, pháp luật Việt Nam, văn hóa Việt Nam để suy luận.
4. Chọn đáp án đúng nhất dựa vào sự kiện, quy định, hoặc truyền thống Việt Nam cụ thể.

--- YÊU CẦU ĐẦU RA ---
- KHÔNG giải thích dài, lan man.
- {instruction_text}
"""
    
    else:  # RAG (default)
        # Retrieval-Augmented Generation
        prompt = f"""
Bạn là chuyên gia phân tích thông tin. Nhiệm vụ: Đọc thật kĩ văn bản và trả lời câu hỏi dựa trên văn bản cung cấp.

--- VĂN BẢN THAM KHẢO ---
{context_text}

--- CÂU HỎI ---
Câu hỏi: {real_question}

Các lựa chọn:
{choices_str}

--- CHIẾN LƯỢC ---
1. Tìm thông tin trong CONTEXT khớp với từ khóa câu hỏi.
2. Chọn đáp án ĐƯỢC HỖ TRỢ BỞI CONTEXT.
3. Nếu CONTEXT không đủ, chọn đáp án được nhắc trực tiếp hoặc suy ra rõ ràng nhất.
4. Không suy đoán ngoài.

--- YÊU CẦU ĐẦU RA ---
- KHÔNG giải thích dài, lan man.
- {instruction_text}
"""
    
    return prompt


def clean_output(ans_text):
    # 1. Ưu tiên tuyệt đối: Tìm trong thẻ <ans>
    # Bắt A-J, không phân biệt hoa thường
    tag_match = re.search(r"<ans>\s*([A-Ja-j])\s*</ans>", ans_text, re.IGNORECASE)
    if tag_match:
        return tag_match.group(1).upper()

    # 2. Nếu không có thẻ, chỉ tìm chữ cái đứng riêng lẻ Ở CUỐI CÙNG của chuỗi output
    # Regex này chỉ bắt A-J nếu nó nằm ở cuối câu (có thể theo sau là dấu chấm/xuống dòng)
    # Tránh bắt nhầm chữ "a" trong "gia tốc a" nằm ở giữa câu.
    last_match = re.search(r"\b([A-Ja-j])\s*(\.|)\s*$", ans_text, re.IGNORECASE)
    if last_match:
        return last_match.group(1).upper()
        
    # 3. Fallback: Nếu vẫn không tìm thấy, có thể trả về None để debug hoặc chọn đại A
    # Khuyên dùng: In ra cảnh báo để biết model đang không tuân thủ format
    # print(f"⚠️ Cảnh báo: Không tìm thấy đáp án trong output: {ans_text[:50]}...")
    return SAFE_ANSWER_DEFAULT
# =========================================================
# GỌI LLM
# =========================================================

def call_vnpt_llm(prompt, model_type="small", temperature=0.1):
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
        "temperature": temperature,
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

    # --- NEW: DETECT DOMAIN (5 types) ---
    detected_domain = detect_domain(question)
    
    # Skip RAG for PRECISION_CRITICAL
    context_text = ""
    real_question = question
    is_reading_comprehension = "Đoạn thông tin:" in question

    if detected_domain != DomainType.PRECISION_CRITICAL:
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

    # --- GIỮ NGUYÊN format choices (0. ..., 1. ...) ---
    choices_str = (
        "\n. ".join([f"{i}. {v}" for i, v in enumerate(choices)])
        if isinstance(choices, list)
        else str(choices)
    )
    
    # --- Prompt chỉ thị LLM trả về chữ cái tương ứng ---
    instruction_text = "Hãy chọn đáp án đúng (tương ứng 0->A, 1->B, 2->C, 3->D, 4->E, 5->F, 6->G, 7->H, 8->I, 9->J) và chỉ trả về chữ cái (A, B, C, D, E, F, G, H, I, J). BẮT BUỘC: Đáp án cuối cùng phải nằm trong thẻ <ans>, ví dụ: <ans>A</ans>."
    
    # --- Select model and temperature based on domain ---
    model_to_use = "small"
    temperature = 0.1
    
    if detected_domain == DomainType.PRECISION_CRITICAL:
        # Refuse to answer
        final_choice = SAFE_ANSWER_DEFAULT
        return final_choice, "N/A (PRECISION_CRITICAL)"
    elif detected_domain == DomainType.STEM:
        model_to_use = "large"
        temperature = 0.0  # Lower temperature for precise scientific answers
    elif detected_domain == DomainType.MULTI_DOMAIN:
        # History, Law, Culture, Economics - use large model for nuance
        CONTEXT_LENGTH_THRESHOLD = 1200
        if len(context_text) > CONTEXT_LENGTH_THRESHOLD or is_reading_comprehension:
            model_to_use = "large"
    elif detected_domain == DomainType.COMPULSORY:
        # Common sense - small model is fine
        temperature = 0.1
    else:  # RAG
        # Default RAG
        CONTEXT_LENGTH_THRESHOLD = 1200
        if len(context_text) > CONTEXT_LENGTH_THRESHOLD or is_reading_comprehension:
            model_to_use = "large"
    
    # --- Generate domain-specific prompt ---
    prompt = get_prompt_for_domain(detected_domain, context_text, real_question, choices_str, instruction_text)

    # --- Call LLM ---
    ans = call_vnpt_llm(prompt, model_type=model_to_use, temperature=temperature)

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
