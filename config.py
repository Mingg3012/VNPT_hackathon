# config.py
import json
import os

# --- CẤU HÌNH ĐƯỜNG DẪN API THEO TÀI LIỆU [cite: 41, 154, 193] ---
URL_EMBEDDING = "https://api.idg.vnpt.vn/data-service/vnptai-hackathon-embedding"
URL_LLM_SMALL = "https://api.idg.vnpt.vn/data-service/v1/chat/completions/vnptai-hackathon-small"
URL_LLM_LARGE = "https://api.idg.vnpt.vn/data-service/v1/chat/completions/vnptai-hackathon-large"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE_PATH = os.path.join(BASE_DIR, "api_keys.json")

def load_headers():
    if not os.path.exists(KEY_FILE_PATH):
        print(f"⚠️ Không tìm thấy file {KEY_FILE_PATH}")
        return {}, {}, {}

    with open(KEY_FILE_PATH, "r") as f:
        data = json.load(f)

    headers_small = {}
    headers_large = {}
    headers_embed = {}

    for item in data:
        name = item.get("llmApiName", "")
        # Lấy thông tin từ file json của bạn
        auth = item.get("authorization", "") # Đã có sẵn chữ "Bearer ..."
        token_id = item.get("tokenId", "")
        token_key = item.get("tokenKey", "")
        
        # Tạo bộ header chuẩn theo tài liệu 
        headers = {
            "Authorization": auth,
            "Token-id": token_id,
            "Token-key": token_key,
            "Content-Type": "application/json"
        }

        if name == "LLM small":
            headers_small = headers
        elif name == "LLM large":
            headers_large = headers
        elif "embedings" in name: # Xử lý typo trong file json của bạn
            headers_embed = headers
            
    return headers_small, headers_large, headers_embed

# Khởi tạo header để các file khác dùng
HEADERS_SMALL, HEADERS_LARGE, HEADERS_EMBED = load_headers()