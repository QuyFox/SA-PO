# SA Agent (sa-01)

- **Vai trò:** SA
- **Máy phát triển:** Máy 2
- **Cổng kết nối mặc định (Port):** 8004
- **Capabilities đã đăng ký:** system_architecture, api_design, technology_selection
- **Mô tả:** Thiết kế kiến trúc hệ thống, lựa chọn công nghệ, thiết kế API specifications

## Cách chạy thử nghiệm:

```powershell
# 1. Chạy prompt trực tiếp qua CLI
python cli.py prompt "Thực hiện tác vụ đầu tiên"

# 2. Mở chế độ chat tương tác
python cli.py chat

# 3. Chạy server API
python -m uvicorn api:app --port 8004
```
