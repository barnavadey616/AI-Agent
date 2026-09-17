"""
Knowledge Base query and management tools for TaskFlow AI Agents.
Enables agents to ground responses and actions in enterprise policies, SOPs, and domain guidelines.
"""

from typing import Dict, Any, List, Optional
from taskflow.core.tool import tool
from taskflow.core.knowledge import default_knowledge_base

@tool(name="query_knowledge_base", description="Query internal company knowledge, SOPs, refund policies, pricing tiers, and filing taxonomy.")
def query_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Retrieves relevant knowledge articles and policy snippets."""
    return default_knowledge_base.search(query, top_k=top_k)

@tool(name="add_knowledge_document", description="Add a new SOP, policy, guideline, or company document to the knowledge repository.")
def add_knowledge_document(title: str, content: str, category: str = "General", tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Adds a new document to the persistent knowledge index."""
    doc = default_knowledge_base.add_document(title=title, content=content, category=category, tags=tags)
    return {
        "success": True,
        "message": f"Document '{title}' successfully indexed into knowledge base.",
        "document": doc.to_dict()
    }

@tool(name="list_knowledge_documents", description="List all available knowledge articles, SOPs, and policies in the knowledge base.")
def list_knowledge_documents() -> List[Dict[str, Any]]:
    """Returns all stored documents with metadata and word counts."""
    return default_knowledge_base.list_documents()
