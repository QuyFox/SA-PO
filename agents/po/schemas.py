from typing import Any
from pydantic import BaseModel, Field


class DefineBacklogOutput(BaseModel):
    """Schema đầu ra cho action 'define_backlog' của PO Agent."""
    summary: str = Field(description="Tóm tắt kết quả phân rã Product Backlog")
    details: dict[str, Any] = Field(default_factory=dict, description="Chi tiết các backlog items, user stories, priority")


class AcceptReleaseOutput(BaseModel):
    """Schema đầu ra cho action 'accept_release' của PO Agent."""
    summary: str = Field(description="Tóm tắt kết quả nghiệm thu phát hành sản phẩm")
    verdict: str = Field(default="ACCEPTED", description="Kết luận nghiệm thu (ACCEPTED hoặc REJECTED)")
    details: dict[str, Any] = Field(default_factory=dict, description="Chi tiết đánh giá tiêu chí nghiệm thu")


class DefineVisionOutput(BaseModel):
    """Schema đầu ra cho action 'define_vision' của PO Agent."""
    summary: str = Field(description="Tóm tắt kết quả thực hiện")
    details: dict[str, Any] = Field(default_factory=dict, description="Chi tiết kết quả")
