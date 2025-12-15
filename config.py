# config.py
import json
import os

# --- CẤU HÌNH ĐƯỜNG DẪN API THEO TÀI LIỆU [cite: 41, 154, 193] ---
URL_EMBEDDING = "https://api.idg.vnpt.vn/data-service/vnptai-hackathon-embedding"
URL_LLM_SMALL = "https://api.idg.vnpt.vn/data-service/v1/chat/completions/vnptai-hackathon-small"
URL_LLM_LARGE = "https://api.idg.vnpt.vn/data-service/v1/chat/completions/vnptai-hackathon-large"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE_PATH = os.path.join(BASE_DIR, "api-keys.json")

def load_headers():
    if not os.path.exists(KEY_FILE_PATH):
        raise FileNotFoundError(f"❌ Không tìm thấy file {KEY_FILE_PATH}")

    with open(KEY_FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    headers_small = None
    headers_large = None
    headers_embed = None

    for item in data:
        name = item.get("llmApiName", "").lower()
        auth = item.get("authorization", "")
        token_id = item.get("tokenId", "")
        token_key = item.get("tokenKey", "")

        headers = {
            "Authorization": auth,
            "Token-id": token_id,
            "Token-key": token_key,
            "Content-Type": "application/json"
        }

        if "small" in name:
            headers_small = headers

        elif "large" in name:
            headers_large = headers

        elif "embed" in name:   # bao cả embeddings / embedings
            headers_embed = headers

    return headers_small, headers_large, headers_embed


# Khởi tạo header để các file khác dùng
HEADERS_SMALL, HEADERS_LARGE, HEADERS_EMBED = load_headers()