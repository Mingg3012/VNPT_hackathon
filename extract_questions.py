import json
import re
from collections import Counter

# File dữ liệu
FILES = ["data/val.json", "data/test.json"]

# Từ dừng (Stopwords) để lọc từ rác
STOP_WORDS = {
    "là", "của", "và", "có", "các", "những", "một", "sẽ", "đã", "từ", "vào", 
    "nào", "gì", "như", "việc", "khi", "trong", "được", "người", "theo", 
    "nhất", "ngày", "điều", "bằng", "hoặc", "cũng", "phải", "giữa", "theo", "dưới",
    "câu", "hỏi", "đáp", "án", "chọn", "thông", "tin", "tham", "khảo"
}

def extract_entities(text):
    """Hàm tách từ khóa đơn giản (lấy các cụm từ viết hoa hoặc cụm từ dài)"""
    # 1. Tách các cụm viết hoa (Tên riêng, Tổ chức)
    entities = re.findall(r'\b[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s[A-ZÀ-Ỹ][a-zà-ỹ]+)*\b', text)
    return entities

def generate_topic_list():
    all_text = ""
    for file_path in FILES:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    all_text += " " + item['question']
        except:
            pass

    # Trích xuất thực thể
    entities = extract_entities(all_text)
    
    # Lọc rác và đếm tần suất
    clean_entities = [e for e in entities if e.lower() not in STOP_WORDS and len(e.split()) >= 2]
    counter = Counter(clean_entities)
    
    # Lấy top 200 từ khóa xuất hiện nhiều nhất
    top_topics = [topic for topic, count in counter.most_common(200)]
    
    print("🎯 DANH SÁCH TỪ KHÓA GỢI Ý CHO CRAWLER:")
    print(top_topics)
    return top_topics

if __name__ == "__main__":
    generate_topic_list()