from typing import Any
from pydantic import BaseModel, Field


class DesignArchitectureOutput(BaseModel):
    """Schema đầu ra cho action 'design_architecture' của SA Agent."""
    summary: str = Field(description="Tóm tắt kết quả thực hiện")
    details: dict[str, Any] = Field(default_factory=dict, description="Chi tiết kết quả")
