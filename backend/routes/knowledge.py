"""
Knowledge repository routes for TaskFlow AI.
"""

from fastapi import APIRouter
from taskflow.core.knowledge import default_knowledge_base
from backend.models.schemas import AddKnowledgeRequest, SearchKnowledgeRequest

knowledge_router = APIRouter(tags=["Knowledge Base"])


@knowledge_router.get("/api/knowledge")
def list_knowledge():
    """List all indexed knowledge articles and documents."""
    return default_knowledge_base.list_documents()


@knowledge_router.post("/api/knowledge")
def add_knowledge(req: AddKnowledgeRequest):
    """Add a new document into the knowledge base."""
    doc = default_knowledge_base.add_document(
        title=req.title,
        content=req.content,
        category=req.category or "General",
        tags=req.tags,
    )
    return {"success": True, "document": doc.to_dict()}


@knowledge_router.post("/api/knowledge/search")
def search_knowledge(req: SearchKnowledgeRequest):
    """Search the knowledge base via hybrid lexical and semantic matching."""
    return default_knowledge_base.search(query=req.query, top_k=req.top_k or 3)


@knowledge_router.delete("/api/knowledge/{doc_id}")
def delete_knowledge(doc_id: str):
    """Delete a document by ID."""
    success = default_knowledge_base.delete_document(doc_id)
    return {"success": success}
