import json
from typing import Any, Callable
from agent_contract.models import ArtifactRef, TaskRequest

SA_SYSTEM_PROMPT = """Bạn là SA AI Agent (ID: sa-01) trong hệ thống 'ai-team'.
Chuyên môn và khả năng: system_architecture, api_design, technology_selection.

QUY TẮC:
1. Bạn chỉ thực hiện các công việc thuộc phạm vi của vai trò SA.
2. Trả về DUY NHẤT một chuỗi JSON hợp lệ theo Schema được cung cấp, không kèm văn bản dẫn dắt bên ngoài.
"""


def build_messages(
    system_prompt: str,
    request: TaskRequest,
    output_schema: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Ghép system prompt, instruction, context thành messages chuẩn OpenAI-compatible."""
    system_parts = [system_prompt.strip()]
    system_parts.append(
        "\n--- QUY TẮC BẮT BUỘC ---\n"
        "1. Trả về DUY NHẤT một chuỗi JSON hợp lệ theo Schema.\n"
        "2. Không thêm bất kỳ lời dẫn hay văn bản nào bên ngoài JSON."
    )
    if output_schema:
        schema_json = json.dumps(output_schema, indent=2, ensure_ascii=False)
        system_parts.append(f"\n--- JSON SCHEMA BẮT BUỘC ---\n```json\n{schema_json}\n```")

    full_system = "\n\n".join(system_parts)

    user_parts = [
        f"Mã tác vụ (Task ID): {request.task_id}",
        f"Hành động (Action): {request.action}",
        f"Chỉ dẫn (Instruction):\n{request.instruction}",
    ]
    if request.context:
        user_parts.append(f"Ngữ cảnh (Context):\n```json\n{json.dumps(request.context, indent=2, ensure_ascii=False)}\n```")

    return [
        {"role": "system", "content": full_system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
