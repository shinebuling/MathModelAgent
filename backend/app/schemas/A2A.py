from pydantic import BaseModel, Field
from typing import Any, Optional


class CoordinatorToModeler(BaseModel):
    questions: dict
    ques_count: int


class ModelerToCoder(BaseModel):
    questions_solution: dict[str, str]


class CoderToWriter(BaseModel):
    code_response: str | None = None
    code_output: str | None = None
    created_images: list[str] | None = None


class Footnote(BaseModel):
    """文献引用信息模型"""
    query: str = Field(..., description="检索查询词")
    content: str = Field(..., description="文献内容/引用信息")
    papers_count: Optional[int] = Field(None, description="检索到的论文数量")
    metadata: Optional[dict] = Field(None, description="额外的元数据（如DOI、URL等）")


class WriterResponse(BaseModel):
    response_content: Any
    footnotes: Optional[list[Footnote]] = Field(None, description="文献引用列表")
