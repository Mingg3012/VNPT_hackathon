#!/bin/bash
# inference.sh

echo "----------------------------------------"
echo "Bắt đầu chạy Inference Pipeline"
echo "----------------------------------------"

# Gọi predict.py với tham số 'docker' để kích hoạt chế độ chấm thi
# predict.py sẽ tự đọc /code/private_test.json và xuất ra submission.csv
python3 predict.py docker

echo "----------------------------------------"
echo "Đã hoàn tất Inference. File submission.csv đã được tạo."
echo "----------------------------------------"