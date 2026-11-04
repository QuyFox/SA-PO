# My AI Agents: SA & PO (Solution Architect & Product Owner)

Thư mục độc lập dành riêng cho máy của bạn, bao gồm 2 AI Agent:
- **SA (Solution Architect)**: `sa-01` (Cổng: `8004`)
- **PO (Product Owner)**: `po-01` (Cổng: `8005`)

Hệ thống tuân thủ 100% **Agent Contract v1.1.0** chuẩn REST API của nhóm, đã vượt qua toàn bộ **14/14 tiêu chí kiểm thử tự động** (`tools/validate_agent.py`), sẵn sàng kết nối qua mạng LAN hoặc Tailscale với các Agent còn lại (PM, DevOps, BA, DEV, Tester...).

---

## 1. Cấu trúc thư mục

```
my-agents/
├── contract/              # Gói Agent Contract dùng chung (enums, models, validators, registry)
├── config/                # Cấu hình danh mục 10 agent (agents_registry.json)
├── agents/
│   ├── sa/                # Solution Architect Agent (Port 8004)
│   │   ├── agent.py       # Xử lý: design_architecture, review_architecture
│   │   ├── api.py         # REST API chuẩn Agent API v1 (FastAPI/Uvicorn)
│   │   ├── cli.py         # Chạy trực tiếp qua dòng lệnh CLI
│   │   ├── config.py      # Cấu hình môi trường (port 8004, auth token, dirs)
│   │   ├── llm.py         # LLM Client hỗ trợ Gemini, Groq, Ollama, OpenAI
│   │   ├── prompt.py      # System prompt chuyên sâu cho Solution Architect
│   │   ├── schemas.py     # Pydantic Output Models
│   │   ├── tools/         # Quản lý artifact, băm SHA256 an toàn
│   │   └── tests/         # Unit tests chạy offline 100% mock
│   │
│   └── po/                # Product Owner Agent (Port 8005)
│       ├── agent.py       # Xử lý: define_backlog, accept_release, define_vision
│       ├── api.py         # REST API chuẩn Agent API v1 (FastAPI/Uvicorn)
│       ├── cli.py         # Chạy trực tiếp qua dòng lệnh CLI
│       ├── config.py      # Cấu hình môi trường (port 8005, auth token, dirs)
│       ├── llm.py         # LLM Client
│       ├── prompt.py      # System prompt chuyên sâu cho Product Owner
│       ├── schemas.py     # Pydantic Output Models
│       ├── tools/         # Quản lý artifact & LinearClient đồng bộ Linear tickets
│       └── tests/         # Unit tests chạy offline 100% mock
│
├── scripts/
│   ├── local_agents.yaml  # Cấu hình 2 agent chạy trên máy này (SA: 8004, PO: 8005)
│   └── run_local.py       # Script quản trị: up | status | down
└── tools/
    └── validate_agent.py  # Bộ kiểm thử 14 tiêu chí chuẩn hóa Contract
```

---

## 2. Thông số 2 Agent trên máy này

| Agent | ID | Port | Capabilities | Action chính | Artifacts xuất xưởng |
|---|---|---|---|---|---|
| **SA** | `sa-01` | `8004` | `system_architecture`, `api_design`, `technology_selection` | `design_architecture`, `review_architecture` | `architecture.md` (Loại `ARCHITECTURE`) |
| **PO** | `po-01` | `8005` | `product_vision`, `feature_prioritization`, `backlog_management`, `acceptance` | `define_backlog`, `accept_release`, `define_vision` | `backlog.json` (Loại `BACKLOG`), `release_acceptance.md` (Loại `DOCUMENTATION`) |

---

## 3. Hướng dẫn sử dụng

### Bước 1: Kích hoạt môi trường và cài đặt Contract
Từ thư mục `my-agents`:
```bash
pip install -e ./contract
```

### Bước 2: Chạy kiểm thử Offline (Mock)
Chạy toàn bộ 8 bài test offline mà không cần API Key:
```bash
pytest agents/sa/tests agents/po/tests -v
```

### Bước 3: Chấm điểm tiêu chuẩn Contract v1.1.0
Chạy script tự động kiểm tra 14 tiêu chí của cả 2 Agent:
```bash
python tools/validate_agent.py
```
*(Hiện tại cả 2 Agent đều đạt 100% PASS)*

### Bước 4: Khởi động 2 Agent chạy nền
Khởi động đồng thời cả SA (8004) và PO (8005):
```bash
python scripts/run_local.py up
```

Kiểm tra trạng thái sức khỏe:
```bash
python scripts/run_local.py status
```

Dừng cụm Agent:
```bash
python scripts/run_local.py down
```

---

## 4. Tích hợp Linear (Dành cho PO Agent)
Trong file `agents/po/.env`:
```env
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxx
LINEAR_TEAM_ID=your-linear-team-id
```
PO Agent được trang bị sẵn công cụ `agents/po/tools/linear_tool.py`:
- `create_issue()`: Tự động đẩy task/feature vào Linear backlog.
- `sync_backlog()`: Đồng bộ danh sách tính năng từ kết quả phân rã sang Linear.
- Khi chưa điền key, hệ thống tự động chạy chế độ Mock an toàn, không gây crash agent.

---

## 5. Kết nối mạng LAN với PM và DevOps
- **Tường lửa Windows (Mở PowerShell với quyền Admin):**
  ```powershell
  New-NetFirewallRule -DisplayName "AI-Team (SA & PO)" -Direction Inbound -LocalPort 8004,8005 -Protocol TCP -Action Allow
  ```
- Khi máy PM gửi lệnh điều phối (qua Conductor hoặc HTTP REST API):
  - Gửi task tới SA: `POST http://<IP_MÁY_BẠN>:8004/tasks` (kèm header `Authorization: Bearer sa-secure-token-32bytes-secret`)
  - Gửi task tới PO: `POST http://<IP_MÁY_BẠN>:8005/tasks` (kèm header `Authorization: Bearer po-secure-token-32bytes-secret`)
