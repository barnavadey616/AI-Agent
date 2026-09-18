"""
Pydantic schemas and request models for TaskFlow AI backend.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RunOrganizerRequest(BaseModel):
    source_dir: Optional[str] = Field(default=None, description="Source directory to organize")
    target_dir: Optional[str] = Field(default=None, description="Target base directory")


class RunResearchRequest(BaseModel):
    topic: str = Field(..., description="Topic or query to research")
    urls: Optional[List[str]] = Field(default=None, description="Optional custom source URLs")


class RunDataCleanRequest(BaseModel):
    file_path: Optional[str] = Field(default=None, description="Path to dirty CSV/Excel file")
    output_path: Optional[str] = Field(default=None, description="Destination cleaned file path")


class RunEmailTriageRequest(BaseModel):
    inquiries: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="List of email inquiries with sender, subject, and body"
    )


class RunCustomTaskRequest(BaseModel):
    prompt: str = Field(..., description="Natural language task instruction")
    agent_name: Optional[str] = Field(default="CustomAgent", description="Optional agent display name")


class RunScamInvestigationRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Raw message, SMS, email, or URL text to investigate")
    image_base64: Optional[str] = Field(default=None, description="Optional base64-encoded screenshot image")
    file_path: Optional[str] = Field(default=None, description="Optional server-side file path to inspect")
    sample_id: Optional[str] = Field(default=None, description="Pre-loaded sample ID (e.g. 'upi_refund', 'telegram_job', 'electricity_cut', 'fedex_customs')")


class RunAmazonOpsRequest(BaseModel):
    scenario_id: Optional[str] = Field(default=None, description="Amazon operational scenario ID (e.g. 'amz_delays', 'amz_warehouse')")
    query: Optional[str] = Field(default="", description="Operational audit query or details")


class NaturalTaskRequest(BaseModel):
    query: str = Field(..., description="User instruction or prompt")
    target_agent: Optional[str] = Field(default="auto", description="Target agent key or 'auto'")
    image_base64: Optional[str] = Field(default=None, description="Optional attached screenshot or document (base64)")
    sample_id: Optional[str] = Field(default=None, description="Optional pre-configured sample ID")


class AddKnowledgeRequest(BaseModel):
    title: str = Field(..., description="Title of the knowledge document")
    content: str = Field(..., description="Detailed body/content")
    category: Optional[str] = Field(default="General", description="Category classification")
    tags: Optional[List[str]] = Field(default=None, description="Tags or labels")


class SearchKnowledgeRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: Optional[int] = Field(default=3, description="Number of top matches to return")
