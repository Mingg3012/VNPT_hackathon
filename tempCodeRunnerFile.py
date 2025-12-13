# debug_db.py
import chromadb
import config
import requests

# 1. Cấu hình
DB_PATH = "./vector_db"
COLLECTION_NAME = "vnpt_knowledge"

def get_test_embedding(text):
    print(f"🔌 Đang test API Embedding với text: '{text}'...")
    payload = {"model": "vnptai_hackathon_embedding", "input": text, "encoding_format": "float"}
    try:
        resp = requests.post(config.URL_EMBEDDING, headers=config.HEADERS_EMBED, json=payload, timeout=10)
        if resp.status_code == 200:
            print("✅ Gọi API thành công!")
            return resp.json()['data'][0]['embedding']
        else:
            print(f"❌ Lỗi API: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
    return None

if __name__ == "__main__":
    print(f"📂 Đang kiểm tra DB tại: {DB_PATH}")
    
    try:
        # Kết nối
        client = chromadb.PersistentClient(path=DB_PATH)
        
        # 1. Liệt kê tất cả các bảng (Collections) đang có
        col_list = client.list_collections()
        print(f"\n📋 Danh sách các Collections tìm thấy: {[c.name for c in col_list]}")
        
        if not col_list:
            print("😱 DB RỖNG! Không có collection nào cả. Bạn cần chạy lại bước Ingest/Crawl dữ liệu.")
            exit()
            
        # 2. Kiểm tra Collection mục tiêu
        try:
            collection = client.get_collection(name=COLLECTION_NAME)
            count = collection.count()
            print(f"📊 Collection '{COLLECTION_NAME}' đang có: {count} documents.")
            
            if count == 0:
                print("⚠️ Collection này có tồn tại nhưng KHÔNG CÓ DỮ LIỆU (Count = 0).")
                exit()
                
            # 3. Soi thử dữ liệu bên trong
            print("\n👀 Soi thử 1 bản ghi đầu tiên:")
            peek = collection.peek(limit=1)
            if peek['documents']:
                print(f"- ID: {peek['ids'][0]}")
                print(f"- Nội dung: {peek['documents'][0][:100]}...") # In 100 ký tự đầu
            
            # 4. Test tìm kiếm thực tế
            print("\n🔎 Thử tìm kiếm câu: 'Việt Nam nằm ở đâu?'")
            test_vec = get_test_embedding("Việt Nam nằm ở đâu?")
            if test_vec:
                results = collection.query(query_embeddings=[test_vec], n_results=1)
                if results['documents'] and results['documents'][0]:
                    print(f"✅ TÌM THẤY: {results['documents'][0][0][:100]}...")
                else:
                    print("⚠️ Query chạy ok nhưng không tìm thấy kết quả nào khớp (Distance quá xa?).")
            
        except ValueError:
            print(f"❌ Lỗi: Không tìm thấy Collection tên là '{COLLECTION_NAME}'.")
            print(f"👉 Hãy sửa lại biến COLLECTION_NAME trong code predict.py thành một trong các tên ở danh sách trên.")

    except Exception as e:
        print(f"❌ Lỗi Critical: {e}")