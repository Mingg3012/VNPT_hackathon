# debug_model.py (Đã sửa Prompt Template)
import json
import re
import config
import requests
import chromadb
import time
from tqdm import tqdm # Thêm tqdm để có thanh tiến trình

# from predict import solve_question, call_vnpt_llm # Không cần import nếu chạy logic giả lập bên dưới

def debug_solve(item):
    print("\n" + "="*50)
    print(f"❓ CÂU HỎI: {item['question']}")
    print("-" * 20)
    
    question = item['question']
    choices = item['choices']
    
    # --- 1. RAG (TÌM KIẾM DỮ LIỆU) ---
    print("🚀 Đang chạy Embedding & Search...")
    context = []
    try:
        # Kết nối DB
        client = chromadb.PersistentClient(path="./vector_db")
        collection = client.get_collection(name="vnpt_knowledge")
        
        # Gọi API Embedding
        payload = {"model": "vnptai_hackathon_embedding", "input": question, "encoding_format": "float"}
        emb_resp = requests.post(config.URL_EMBEDDING, headers=config.HEADERS_EMBED, json=payload, timeout=10)
        
        if emb_resp.status_code == 200:
            vec = emb_resp.json()['data'][0]['embedding']
            results = collection.query(query_embeddings=[vec], n_results=3)
            
            if results['documents']:
                context = results['documents'][0]
                print(f"✅ TÌM THẤY {len(context)} ĐOẠN CONTEXT:")
                for i, c in enumerate(context):
                    print(f"  [{i+1}] {c[:100].replace(chr(10), ' ')}...") # In 100 ký tự đầu, xóa xuống dòng
            else:
                print("⚠️ DB trả về rỗng (Không tìm thấy context phù hợp).")
        else:
            print(f"❌ Lỗi API Embedding: {emb_resp.status_code} - {emb_resp.text}")

    except Exception as e:
        print(f"❌ Lỗi kết nối ChromaDB/Embedding: {e}")

    # --- 2. PROMPT (TẠO TEMPLATE AN TOÀN & RAG MẠNH) ---
    choices_str = "\n".join([f"{i}. {v}" for i, v in enumerate(choices)]) if isinstance(choices, list) else str(choices)
    context_text = "\n".join(context) if context else "Không có thông tin tham khảo."
    
    # TEMPLATE MỚI: Chuyên gia tự-phát-hiện lĩnh vực + bắt buộc dùng Context
    # Tự động phát hiện lĩnh vực từ câu hỏi
    domain_keywords = {
        'y học|thuốc|bệnh|chẩn đoán|điều trị|sinh lý|giải phẫu': 'Chuyên gia Y tế',
        'luật|pháp|quyền|nghĩa vụ|vi phạm|hợp đồng': 'Luật sư / Chuyên gia Luật pháp',
        'lịch sử|sự kiện|chiến tranh|nhân vật|chế độ': 'Nhà sử học / Chuyên gia Lịch sử',
        'công nghệ|máy tính|phần mềm|internet|lập trình': 'Kỹ sư / Chuyên gia Công nghệ',
        'kinh tế|tài chính|tiền tệ|thị trường|ngân hàng': 'Chuyên gia Kinh tế',
        'môi trường|sinh thái|biến đổi khí hậu|tài nguyên': 'Chuyên gia Môi trường',
        'giáo dục|học tập|nuôi dạy': 'Chuyên gia Giáo dục',
    }
    
    detected_domain = 'Chuyên gia chuyên sâu'
    question_lower = question.lower()
    for keywords, domain in domain_keywords.items():
        if any(kw in question_lower for kw in keywords.split('|')):
            detected_domain = domain
            break
    
    prompt = f"""
    Bạn là một {detected_domain} với kiến thức sâu rộng trong lĩnh vực của mình. Hãy sử dụng chuyên môn của bạn để phân tích và trả lời câu hỏi này.

    Tuy nhiên, **TUYỆT ĐỐI CHỈ DỰA VÀO** các đoạn thông tin tham khảo (CONTEXT) được cung cấp dưới đây. Không sử dụng bất kỳ kiến thức bên ngoài hoặc suy luận không có cơ sở trong CONTEXT. Nếu CONTEXT không cung cấp đủ thông tin để trả lời, hãy dựa trên những gì có sẵn và chọn đáp án hợp lý nhất.

    --- BẮT ĐẦU THÔNG TIN THAM KHẢO ---
    {context_text}
    --- KẾT THÚC THÔNG TIN THAM KHẢO ---

    Câu hỏi trắc nghiệm: {question}
    Các lựa chọn:
    {choices_str}

    Dựa vào thông tin tham khảo và chuyên môn của bạn, hãy chọn đáp án đúng nhất.
    Chỉ trả về đáp án là số chỉ mục (index) của lựa chọn đó (0, 1, 2, hoặc 3) gói gọn trong thẻ <ans>.
    Ví dụ: <ans>2</ans>
    """
    
    print("-" * 20)
    print("🤖 MODEL ĐANG SUY NGHĨ...")
    
    # --- 3. GỌI LLM (CÓ BẮT LỖI) ---
    payload_llm = {
        "model": "vnptai_hackathon_small",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    raw_ans = ""
    try:
        resp = requests.post(config.URL_LLM_SMALL, headers=config.HEADERS_SMALL, json=payload_llm, timeout=30)
        
        # KIỂM TRA LỖI API (QUAN TRỌNG)
        if resp.status_code != 200:
            print(f"❌ API LỖI (Code {resp.status_code}):")
            print(f"   Nội dung lỗi: {resp.text}")
            print("👉 Gợi ý: Nếu là 429 thì do hết quota/gọi quá nhanh. Nếu 401 là sai Key.")
            return # Dừng luôn
            
        resp_json = resp.json()
        if 'choices' in resp_json and len(resp_json['choices']) > 0:
            raw_ans = resp_json['choices'][0]['message']['content']
            print(f"💬 PHẢN HỒI THỰC TẾ CỦA MODEL:\n{raw_ans}")
        else:
            print(f"⚠️ API trả về JSON lạ (Thiếu 'choices'): {resp_json}")
            return

    except Exception as e:
        print(f"❌ Lỗi kết nối mạng đến LLM: {e}")
        return

    print("-" * 20)
    
    # --- 4. TEST REGEX ---
    print("🕵️ TEST REGEX (BÓC TÁCH ĐÁP ÁN):")
    
    # Regex 1: Tìm thẻ chuẩn <ans>
    tag_match = re.search(r'<ans>\s*([0-3])\s*</ans>', raw_ans)
    
    # Regex 2: Tìm số đứng cuối câu (Fallback)
    matches = re.findall(r'\b([0-3])\b', raw_ans)
    
    final_choice = "?"
    
    if tag_match:
        final_choice = tag_match.group(1)
        print(f"✅ Bắt được thẻ <ans>: {final_choice}")
    elif matches:
        final_choice = matches[-1]
        print(f"⚠️ Không có thẻ <ans>, dùng Regex tìm số cuối cùng: {final_choice}")
        print(f"   (Các số tìm thấy: {matches})")
    else:
        final_choice = "0"
        print("❌ KHÔNG tìm thấy số nào cả -> Default về '0' (A)")

    # Check đáp án đúng
    true_ans = str(item.get('answer', '?')).upper()
    
    # Map số sang chữ để so sánh
    map_idx = {'0': 'A', '1': 'B', '2': 'C', '3': 'D'}
    pred_char = map_idx.get(final_choice, '?')
    
    print(f"🎯 ĐÁP ÁN ĐÚNG TRONG FILE: {true_ans}")
    print(f"🤖 MODEL CHỌN: {pred_char} ({final_choice})")
    
    if pred_char == true_ans:
        print("🎉 KẾT QUẢ: ĐÚNG")
    else:
        print("💀 KẾT QUẢ: SAI")
        
    print("="*50)

# --- CHẠY ---
if __name__ == "__main__":
    try:
        # Thêm tqdm vào đây
        from tqdm import tqdm 
        
        with open("data/val.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"📂 Đang test trên {len(data)} câu hỏi.")
        # Chạy thử 3 câu đầu tiên thôi để debug
        for item in data[:3]:
            debug_solve(item)
            
    except FileNotFoundError:
        print("❌ Không tìm thấy file data/val.json")
    except Exception as e:
        print(f"❌ Lỗi chung: {e}")
