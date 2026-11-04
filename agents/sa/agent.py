import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar, Union
from pathlib import Path

from pydantic import BaseModel

from agent_contract.enums import AgentRole, AgentStatus, ArtifactType, ErrorCode, Priority, TaskStatus
from agent_contract.models import (
    AgentError,
    AgentIdentity,
    AgentState,
    ArtifactRef,
    NextAction,
    TaskRequest,
    TaskResult,
    blocked_result,
    failed_result,
    make_error,
)
from agent_contract.registry import ACTION_MAP, CAPABILITY_REGISTRY
from config import AgentConfig
from llm import LLMClient, LLMError
from prompt import SA_SYSTEM_PROMPT, build_messages
from schemas import DesignArchitectureOutput
from tools.artifact import ArtifactError, save_artifact

T = TypeVar("T", bound=BaseModel)


def action(
    name: str,
    output_model: type[BaseModel] | None = None,
    capability: str | None = None,
) -> Callable:
    """Decorator đăng ký action cho SA Agent."""
    def decorator(func: Callable) -> Callable:
        func._action_name = name  # type: ignore[attr-defined]
        func._output_model = output_model  # type: ignore[attr-defined]
        func._capability = capability  # type: ignore[attr-defined]
        return func
    return decorator


class BaseAgent:
    """Lớp nền tảng quản lý vòng đời tác vụ và bảo vệ lỗi chuẩn Contract v1.0."""

    def __init__(
        self,
        identity: AgentIdentity,
        config: AgentConfig,
        llm: LLMClient | None = None,
    ) -> None:
        self.identity = identity
        self.config = config
        self.llm = llm or LLMClient(config=config, mock=True)
        self._current_task: str | None = None
        self._actions: dict[str, tuple[Callable, type[BaseModel] | None, str | None]] = {}
        self._scan_and_register_actions()

    def _scan_and_register_actions(self) -> None:
        for attr_name in dir(self):
            try:
                attr = getattr(self, attr_name)
                if callable(attr) and hasattr(attr, "_action_name"):
                    action_name = getattr(attr, "_action_name")
                    output_model = getattr(attr, "_output_model", None)
                    capability = getattr(attr, "_capability", None)
                    self._actions[action_name] = (attr, output_model, capability)
            except Exception:
                continue

    def get_identity(self) -> AgentIdentity:
        return self.identity

    def get_state(self) -> AgentState:
        return AgentState(
            agent_id=self.identity.agent_id,
            role=self.identity.role,
            status=self.identity.status,
            current_task=self._current_task,
            updated_at=datetime.now(timezone.utc),
        )

    def handle(self, request: TaskRequest) -> TaskResult:
        start_time = time.perf_counter()

        if not request.instruction or not request.instruction.strip() or request.context.get("invalid_input"):
            return failed_result(
                request,
                make_error(
                    code=ErrorCode.INVALID_INPUT,
                    message="Dữ liệu đầu vào bị hỏng hoặc thiếu chỉ dẫn thực thi hợp lệ.",
                    retryable=False,
                ),
                summary="Dữ liệu đầu vào không hợp lệ.",
            )

        if request.role != self.identity.role:
            return failed_result(
                request,
                make_error(
                    code=ErrorCode.PERMISSION_DENIED,
                    message=f"Role mismatch: Agent role is {self.identity.role.value}, but request role is {request.role.value}.",
                    retryable=False,
                ),
            )

        if request.agent_id != self.identity.agent_id:
            return failed_result(
                request,
                make_error(
                    code=ErrorCode.PERMISSION_DENIED,
                    message=f"Agent ID mismatch: Agent is {self.identity.agent_id}, but request is for {request.agent_id}.",
                    retryable=False,
                ),
            )

        if request.action not in self._actions:
            return failed_result(
                request,
                make_error(
                    code=ErrorCode.PERMISSION_DENIED,
                    message=f"Action '{request.action}' không được hỗ trợ bởi agent {self.identity.agent_id}.",
                    retryable=False,
                ),
            )

        self.identity.status = AgentStatus.RUNNING
        self._current_task = request.task_id

        final_result: TaskResult

        try:
            handler, _, _ = self._actions[request.action]
            raw_output = handler(request)

            if isinstance(raw_output, TaskResult):
                final_result = raw_output
            elif isinstance(raw_output, BaseModel):
                final_result = TaskResult(
                    contract_version=request.contract_version,
                    task_id=request.task_id,
                    agent_id=request.agent_id,
                    status=TaskStatus.COMPLETED,
                    summary=f"Thực thi thành công action '{request.action}'",
                    outputs=[raw_output.model_dump(mode="json")],
                    artifacts=[],
                    next_actions=[],
                    error=None,
                )
            elif isinstance(raw_output, dict):
                final_result = TaskResult(
                    contract_version=request.contract_version,
                    task_id=request.task_id,
                    agent_id=request.agent_id,
                    status=TaskStatus.COMPLETED,
                    summary=f"Thực thi thành công action '{request.action}'",
                    outputs=[raw_output],
                    artifacts=[],
                    next_actions=[],
                    error=None,
                )
            else:
                final_result = TaskResult(
                    contract_version=request.contract_version,
                    task_id=request.task_id,
                    agent_id=request.agent_id,
                    status=TaskStatus.COMPLETED,
                    summary=str(raw_output),
                    outputs=[],
                    artifacts=[],
                    next_actions=[],
                    error=None,
                )

            self.identity.status = AgentStatus.IDLE
            self._current_task = None

        except LLMError as err:
            self.identity.status = AgentStatus.FAILED
            self._current_task = None
            final_result = failed_result(
                request,
                make_error(code=ErrorCode.LLM_ERROR, message=str(err), retryable=True),
                summary=f"Lỗi LLM khi thực thi action '{request.action}'",
            )
        except ArtifactError as err:
            self.identity.status = AgentStatus.FAILED
            self._current_task = None
            final_result = failed_result(
                request,
                make_error(code=ErrorCode.TOOL_ERROR, message=str(err), retryable=True),
                summary=f"Lỗi artifact khi thực thi action '{request.action}'",
            )
        except ValueError as err:
            self.identity.status = AgentStatus.FAILED
            self._current_task = None
            final_result = failed_result(
                request,
                make_error(code=ErrorCode.INVALID_INPUT, message=str(err), retryable=False),
                summary=f"Dữ liệu đầu vào không hợp lệ khi thực thi action '{request.action}'",
            )
        except Exception as err:
            self.identity.status = AgentStatus.FAILED
            self._current_task = None
            final_result = failed_result(
                request,
                make_error(code=ErrorCode.UNKNOWN_ERROR, message=f"Lỗi không xác định: {err}", retryable=False),
                summary=f"Thực thi action '{request.action}' thất bại",
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        final_result.metadata.setdefault("provider", self.config.llm_provider)
        final_result.metadata.setdefault("model", self.config.llm_model)
        final_result.metadata.setdefault("duration_ms", duration_ms)
        final_result.metadata.setdefault("dry_run", self.config.dry_run)

        self.identity.status = AgentStatus.IDLE
        return final_result


class SaAgent(BaseAgent):
    """Thiết kế kiến trúc hệ thống, lựa chọn công nghệ, thiết kế API specifications."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        llm: LLMClient | None = None,
        artifact_dir: Union[Path, str, None] = None,
    ) -> None:
        cfg = config or AgentConfig()
        if artifact_dir:
            cfg.artifact_dir = str(artifact_dir)

        identity = AgentIdentity(
            agent_id=cfg.agent_id or "sa-01",
            role=AgentRole.SA,
            name="SA Agent",
            version="1.0.0",
            capabilities=CAPABILITY_REGISTRY[AgentRole.SA],
            status=AgentStatus.IDLE,
        )
        super().__init__(identity=identity, config=cfg, llm=llm)

    @action("design_architecture", output_model=DesignArchitectureOutput, capability="system_architecture")
    def handle_design_architecture(self, request: TaskRequest) -> TaskResult:
        """Xử lý action 'design_architecture'."""
        if not self.llm.mock or self.llm.mock_responder:
            messages = build_messages(
                system_prompt=SA_SYSTEM_PROMPT,
                request=request,
                output_schema=DesignArchitectureOutput.model_json_schema(),
            )
            data = self.llm.complete_json(messages, DesignArchitectureOutput)
        else:
            data = DesignArchitectureOutput(
                summary=f"Kết quả xử lý từ SA: {request.instruction}",
                details={
                    "task_id": request.task_id,
                    "role": "SA",
                    "architecture_style": "Microservices & Event-Driven",
                    "components": ["API Gateway", "Core Business Service", "Task Engine"],
                    "tech_stack": {
                        "backend": "Python / FastAPI",
                        "database": "PostgreSQL 16",
                        "cache": "Redis 7",
                        "messaging": "RabbitMQ",
                    },
                },
            )

        # Lưu artifact kiến trúc chuẩn
        content_md = (
            f"# Tài liệu Kiến trúc Hệ thống (SA)\n\n"
            f"**Tác vụ:** {request.task_id}\n"
            f"**Tóm tắt:** {data.summary}\n\n"
            f"## Thiết kế chi tiết (JSON):\n"
            f"```json\n{json.dumps(data.details, indent=2, ensure_ascii=False)}\n```\n"
        )
        art_ref = save_artifact(
            name="architecture.md",
            type=ArtifactType.ARCHITECTURE,
            content=content_md,
            created_by=self.identity.agent_id,
            artifact_dir=self.config.artifact_dir,
        )

        # Gợi ý NextActions cho DBA và DEV theo đúng contract NextAction
        next_actions = [
            NextAction(
                suggested_role=AgentRole.DBA,
                action="design_schema",
                reason="Kiến trúc đã hoàn tất, DBA có thể thiết kế cơ sở dữ liệu",
            ),
            NextAction(
                suggested_role=AgentRole.DEV,
                action="implement_project",
                reason="Chuẩn bị sẵn sàng mã nguồn theo kiến trúc",
            ),
        ]

        return TaskResult(
            contract_version=request.contract_version,
            task_id=request.task_id,
            agent_id=request.agent_id,
            status=TaskStatus.COMPLETED,
            summary="Đã hoàn thành thiết kế kiến trúc hệ thống.",
            outputs=[data.model_dump(mode="json")],
            artifacts=[art_ref],
            next_actions=next_actions,
            error=None,
        )

    @action("review_architecture", output_model=DesignArchitectureOutput, capability="system_architecture")
    def handle_review_architecture(self, request: TaskRequest) -> TaskResult:
        """Đánh giá và rà soát kiến trúc hệ thống."""
        return self.handle_design_architecture(request)
