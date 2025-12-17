import pytesseract
from pdf2image import convert_from_path
import os
from tqdm import tqdm # Thư viện này để hiện thanh tiến trình cho đẹp

# Cấu hình đường dẫn (Nếu chạy trên Windows cần trỏ đúng path cài đặt tesseract.exe)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def convert_scanned_pdf_to_txt(pdf_path, output_txt_path):
    """
    Chuyển đổi PDF scan sang text sử dụng OCR tiếng Việt.
    """
    print(f"Đang xử lý file: {pdf_path}")
    
    # Kiểm tra file tồn tại
    if not os.path.exists(pdf_path):
        print(f"Lỗi: Không tìm thấy file {pdf_path}")
        return

    try:
        # 1. Chuyển đổi các trang PDF thành danh sách các hình ảnh
        # dpi=300 để đảm bảo độ nét cho việc nhận dạng chữ
        images = convert_from_path(pdf_path, dpi=300)
        
        full_text = ""
        
        # 2. Duyệt qua từng trang ảnh để OCR
        print(f"Đang quét {len(images)} trang...")
        
        for i, image in enumerate(tqdm(images)):
            # Sử dụng ngôn ngữ tiếng Việt ('vie')
            # config='--psm 6' giả định khối văn bản thống nhất (tốt cho văn bản luật)
            text = pytesseract.image_to_string(image, lang='vie', config='--psm 6')
            
            # Thêm dấu phân trang để dễ nhìn
            full_text += f"\n--- Trang {i+1} ---\n"
            full_text += text

        # 3. Lưu kết quả ra file txt
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        print(f"Xong! Kết quả đã lưu tại: {output_txt_path}")

    except Exception as e:
        print(f"Có lỗi xảy ra: {str(e)}")

# --- THỰC THI ---

# Danh sách file cần chuyển (Dựa trên tên file bạn đã upload)
files_to_convert = [
    "Bo luat dan su.pdf",
    "Bo luat hang hai Viet nam.pdf"
]

# Vòng lặp xử lý từng file
for file_name in files_to_convert:
    # Tạo tên file output (ví dụ: Bo luat dan su.txt)
    output_name = file_name.replace(".pdf", ".txt")
    convert_scanned_pdf_to_txt(file_name, output_name)
