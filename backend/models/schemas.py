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


class NaturalTaskRequest(BaseModel):
    query: str = Field(..., description="User instruction or prompt")
    target_agent: Optional[str] = Field(default="auto", description="Target agent key or 'auto'")


class AddKnowledgeRequest(BaseModel):
    title: str = Field(..., description="Title of the knowledge document")
    content: str = Field(..., description="Detailed body/content")
    category: Optional[str] = Field(default="General", description="Category classification")
    tags: Optional[List[str]] = Field(default=None, description="Tags or labels")


class SearchKnowledgeRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: Optional[int] = Field(default=3, description="Number of top matches to return")
