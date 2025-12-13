import os
import re
import time
import requests
import chromadb
from tqdm import tqdm
import config
import sys
import pandas as pd

# --- FIX LỖI CHROMA DB TRÊN DOCKER ---
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# --- CẤU HÌNH ---
DB_PATH = "./vector_db"
DATA_SOURCE = "data/documents.txt"
MAX_CHUNK_SIZE = 1200 # Ký tự tối đa cho 1 chunk (An toàn cho Embedding)

def clean_text(text):
    # Xóa khoảng trắng thừa, tab, xuống dòng lộn xộn
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def split_long_text(text, limit=1000):
    """Chia đoạn văn dài thành các đoạn nhỏ hơn nhưng vẫn giữ nghĩa"""
    if len(text) <= limit:
        return [text]
    
    # Cắt theo câu (.) để không bị đứt gãy ý
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < limit:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def get_embedding(text):
    payload = {
        "model": "vnptai_hackathon_embedding",
        "input": text,
        "encoding_format": "float"
    }
    # Retry 3 lần
    for _ in range(3):
        try:
            response = requests.post(config.URL_EMBEDDING, headers=config.HEADERS_EMBED, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()['data'][0]['embedding']
            elif response.status_code == 429: # Rate limit
                time.sleep(2)
        except:
            pass
        time.sleep(0.5)
    return None

def build_database():
    print("🚀 Bắt đầu xây dựng Vector Database (Bản Tối ưu)...")
    
    # 1. Kết nối và Reset DB
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection("vnpt_knowledge")
        print("🗑️ Đã xóa Collection cũ.")
    except:
        pass
        
    collection = client.get_or_create_collection(name="vnpt_knowledge")

    # 2. Đọc file
    if not os.path.exists(DATA_SOURCE):
        print(f"❌ Không tìm thấy file {DATA_SOURCE}")
        return

    with open(DATA_SOURCE, "r", encoding="utf-8") as f:
        full_text = f.read()
        # Bước 1: Tách theo đoạn văn lớn (\n\n)
        raw_paragraphs = full_text.split('\n\n') 
        
    # 3. Xử lý & Làm sạch & Cắt nhỏ
    final_docs = []
    print("⚙️ Đang xử lý và làm sạch dữ liệu...")
    
    for p in raw_paragraphs:
        cleaned = clean_text(p)
        if len(cleaned) < 20: continue # Bỏ qua rác
        
        # Nếu đoạn vẫn quá dài > 1200 ký tự -> Cắt nhỏ tiếp
        if len(cleaned) > MAX_CHUNK_SIZE:
            sub_chunks = split_long_text(cleaned, limit=MAX_CHUNK_SIZE)
            final_docs.extend(sub_chunks)
        else:
            final_docs.append(cleaned)
    
    print(f"📄 Số lượng đoạn văn sau khi xử lý: {len(final_docs)}")
    
    # 4. Nạp vào DB
    batch_size = 10 
    ids_batch = []
    docs_batch = []
    emb_batch = []
    metadatas_batch = []
    
    print("embedding...")
    for i, doc in tqdm(enumerate(final_docs), total=len(final_docs)):
        emb = get_embedding(doc)
        
        if emb:
            ids_batch.append(f"doc_{i}")
            docs_batch.append(doc)
            emb_batch.append(emb)
            metadatas_batch.append({"source": "manual_ingest", "length": len(doc)})
        
        # Batch insert
        if len(ids_batch) >= batch_size:
            collection.add(
                ids=ids_batch, 
                embeddings=emb_batch, 
                documents=docs_batch,
                metadatas=metadatas_batch
            )
            ids_batch, docs_batch, emb_batch, metadatas_batch = [], [], [], []
            time.sleep(0.1) # Giữ tốc độ an toàn

    # Nạp nốt số lẻ
    if ids_batch:
        collection.add(
            ids=ids_batch, 
            embeddings=emb_batch, 
            documents=docs_batch,
            metadatas=metadatas_batch
        )

    print(f"\n✅ HOÀN TẤT! Tổng số documents trong DB: {collection.count()}")

if __name__ == "__main__":
    build_database()