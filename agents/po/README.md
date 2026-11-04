# PO Agent (po-01)

- **Vai trò:** PO
- **Máy phát triển:** Máy 3
- **Cổng kết nối mặc định (Port):** 8005
- **Capabilities đã đăng ký:** product_vision, feature_prioritization, backlog_management, acceptance
- **Mô tả:** Định hình tầm nhìn sản phẩm, quản lý độ ưu tiên backlog, nghiệm thu tính năng

## Cách chạy thử nghiệm:

```powershell
# 1. Chạy prompt trực tiếp qua CLI
python cli.py prompt "Thực hiện tác vụ đầu tiên"

# 2. Mở chế độ chat tương tác
python cli.py chat

# 3. Chạy server API
python -m uvicorn api:app --port 8005
```
