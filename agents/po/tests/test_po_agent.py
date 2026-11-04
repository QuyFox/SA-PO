import sys
from pathlib import Path

agent_dir = Path(__file__).resolve().parent.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

for key in list(sys.modules.keys()):
    if key in ["agent", "config", "llm", "prompt", "schemas", "api", "tools"] or key.startswith("tools."):
        sys.modules.pop(key, None)

import pytest
from agent_contract.enums import AgentRole, ErrorCode, TaskStatus
from agent_contract.models import TaskRequest
from agent import PoAgent
from config import AgentConfig
from llm import LLMClient


@pytest.fixture
def agent(tmp_path) -> PoAgent:
    cfg = AgentConfig(
        base_dir=tmp_path,
        port=8005,
        agent_id="po-01",
        agent_role=AgentRole.PO,
        artifact_dir=str(tmp_path / "artifacts"),
    )
    llm = LLMClient(config=cfg, mock=True)
    return PoAgent(config=cfg, llm=llm, artifact_dir=cfg.artifact_dir)


def test_identity(agent):
    identity = agent.get_identity()
    assert identity.agent_id == "po-01"
    assert identity.role == AgentRole.PO
    assert len(identity.capabilities) > 0


def test_handle_valid_action(agent):
    req = TaskRequest(
        task_id="TASK-TEST-001",
        project_id="PROJ-TEST",
        agent_id="po-01",
        role=AgentRole.PO,
        action="define_vision",
        instruction="Chạy thử nghiệm kiểm tra tính tương thích",
        context={},
    )
    res = agent.handle(req)
    assert res.status == TaskStatus.COMPLETED
    assert res.error is None
    assert len(res.outputs) == 1


def test_handle_invalid_action(agent):
    req = TaskRequest(
        task_id="TASK-TEST-BAD-ACT",
        project_id="PROJ-TEST",
        agent_id="po-01",
        role=AgentRole.PO,
        action="action_khong_ton_tai",
        instruction="Thử action sai",
    )
    res = agent.handle(req)
    assert res.status == TaskStatus.FAILED
    assert res.error.code == ErrorCode.PERMISSION_DENIED


def test_handle_invalid_input(agent):
    req = TaskRequest(
        task_id="TASK-TEST-BAD-INPUT",
        project_id="PROJ-TEST",
        agent_id="po-01",
        role=AgentRole.PO,
        action="define_vision",
        instruction="   ",
    )
    res = agent.handle(req)
    assert res.status == TaskStatus.FAILED
    assert res.error.code == ErrorCode.INVALID_INPUT
