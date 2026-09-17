"""
Knowledge Base and Retrieval-Augmented Generation (RAG) Engine for TaskFlow AI.
Stores, indexes, and retrieves company SOPs, customer policies, pricing, and domain knowledge.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re
import datetime
import math
import logging

from google import genai

from taskflow import config
logger = logging.getLogger("taskflow.knowledge")

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 768

class KnowledgeDocument:       
    def __init__(
        self,
        doc_id: str,
        title: str,
        category: str,
        content: str,
        tags: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        self.doc_id = doc_id
        self.title = title
        self.category = category
        self.content = content
        self.tags = tags or []
        self.created_at = created_at or datetime.datetime.now().isoformat()
        self.embedding = embedding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.doc_id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "word_count": len(self.content.split()),
            "embedding": self.embedding
            
        }


class KnowledgeBase:
    def _generate_embedding(self, text: str, is_query: bool = False) -> Optional[List[float]]:
        """Generate a semantic embedding using Gemini."""
        if config.IS_SIMULATION or not config.GEMINI_API_KEY:
            return None

        try:
            client = genai.Client(api_key=config.GEMINI_API_KEY)

            if is_query:
                content = f"task: search result | query: {text}"
            else:
                content = text

            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=content,
                config={
                    "output_dimensionality": EMBEDDING_DIMENSIONS
                }
            )

            return result.embeddings[0].values
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else config.KNOWLEDGE_DIR
        self.index_file = self.storage_dir / "knowledge_index.json"
        self.documents: Dict[str, KnowledgeDocument] = {}
        self._initialize()

    def _initialize(self):
        """Ensure storage directory exists and load or seed knowledge documents."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        doc = KnowledgeDocument(
                            doc_id=item["id"],
                            title=item["title"],
                            category=item.get("category", "General"),
                            content=item["content"],
                            tags=item.get("tags", []),
                            created_at=item.get("created_at"),
                            embedding=item.get("embedding")
                        )
                        
                        self.documents[doc.doc_id] = doc
            except Exception as e:
                logger.error(f"Failed to load knowledge index: {e}")
                self._seed_default_knowledge()
        else:
            self._seed_default_knowledge()
        self._backfill_embeddings()

    def _save_index(self):
        """Persist documents index to disk."""
        data = [doc.to_dict() for doc in self.documents.values()]
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _backfill_embeddings(self):
        """Generate embeddings for documents that do not have one yet."""
        updated = False

        for doc in self.documents.values():
            if doc.embedding is None:
                try:
                    doc_text = f"title: {doc.title} | text: {doc.content}"
                    doc.embedding = self._generate_embedding(doc_text)
                    updated = True
                    logger.info(f"Generated embedding for '{doc.title}'")
                except Exception as e:
                    logger.error(
                        f"Failed to generate embedding for '{doc.title}': {e}"
                    )

        if updated:
            self._save_index()

    def _seed_default_knowledge(self):
        """Pre-load standard enterprise knowledge, policies, and SOPs."""
        seeds = [
            {
                "id": "sop_customer_sla_refunds",
                "title": "Customer Support SLA & Refund Policy",
                "category": "Customer Operations",
                "tags": ["sla", "refund", "billing", "escalation", "support"],
                "content": """### Customer Support SLA & Refund Policy
1. Service Level Agreements (SLA):
- High / Critical (System Down, Outage, Double Billing): Response guaranteed within 1 hour. Immediate escalation to senior operations engineer via escalations@taskflow.ai.
- Medium (Feature Request, Integration, Technical Guidance): Response within 8 business hours.
- Low (General Inquiries, Feedback): Response within 24 business hours.

2. Refund and Billing Dispute Policy:
- 30-day no-questions-asked refund policy for all annual and monthly subscriptions.
- Double charges or processing errors are refunded within 2-3 business days upon verification.
- Pro-rata refunds are applicable when downgrading enterprise plans with more than 6 months remaining."""
            },
            {
                "id": "sop_enterprise_pricing_2026",
                "title": "Product Pricing, Licensing & Service Tiers 2026",
                "category": "Commercial & Sales",
                "tags": ["pricing", "licenses", "enterprise", "costs", "sales"],
                "content": """### TaskFlow AI Pricing Tiers (2026)
1. Free Community Edition:
- Core 4 agents (File Organizer, Research Agent, Data Cleaner, Email Triage).
- Up to 1,000 tasks/month, local directory watching.

2. Pro Tier ($49/user/month):
- Unlimited autonomous tasks, priority execution.
- Automated scheduled interval crons and webhook triggers.
- Gemini 3.8 Flash high-throughput reasoning.

3. Enterprise Dedicated Tier ($199/user/month, min 10 seats):
- Custom tool development & sandboxed microVM code execution.
- Dedicated SSO, SOC2 compliance reports, private cluster deployment.
- 99.99% uptime SLA and 24/7 dedicated support representative."""
            },
            {
                "id": "sop_data_hygiene_governance",
                "title": "Data Governance, Anomaly Thresholds & PII Standards",
                "category": "Engineering SOP",
                "tags": ["data", "hygiene", "pii", "governance", "standards"],
                "content": """### Data Quality & Governance Protocols
1. Tabular Hygiene Rules:
- Negative numerical values in positive business metrics (Quantity, Price, Transaction Amounts) are flagged as anomalies and clamped to absolute values.
- Duplicated records must be pruned using first-seen timestamp precedence.
- Missing categories are imputed with 'Unknown', numeric fields with the median to avoid outlier skew.

2. PII (Personally Identifiable Information):
- Credit card numbers must always be masked to the last 4 digits (e.g., **** 4120).
- Passwords, API tokens, and secret keys must never be stored in plain text reports or CSV exports."""
            },
            {
                "id": "sop_file_naming_organization",
                "title": "Document Filing, Retention & Taxonomy Guidelines",
                "category": "Filing Guidelines",
                "tags": ["files", "invoices", "contracts", "taxonomy", "naming"],
                "content": """### Corporate Document Filing Standards
1. Target Directory Taxonomy:
- /Invoices: Vendor bills, AWS invoices, travel receipts, payment receipts.
- /Contracts: Non-disclosure agreements (NDAs), master service agreements (MSAs), signed vendor terms.
- /Reports: Quarterly financial reviews, performance decks, executive summaries.
- /Notes: Team sync notes, sprint retrospectives, meeting agendas.

2. Standardized Naming Convention:
- Format: `YYYY_Category_EntityOrTitle.ext` (e.g. `2026_Invoice_Uber_Technologies.txt`).
- All spaces converted to underscores; illegal filesystem characters stripped."""
            }
        ]

        for s in seeds:
            
            doc_text = f"title: {s['title']} | text: {s['content']}"
            embedding = self._generate_embedding(doc_text)

            doc = KnowledgeDocument(
                doc_id=s["id"],
                title=s["title"],
                category=s["category"],
                content=s["content"],
                tags=s["tags"],
                embedding=embedding
            )
            self.documents[doc.doc_id] = doc
            
        self._save_index()
        logger.info(f"Seeded {len(seeds)} default knowledge documents.")

    def add_document(
        self,
        title: str,
        content: str,
        category: str = "General",
        tags: Optional[List[str]] = None
    ) -> KnowledgeDocument:
        """Add a new document to the knowledge repository."""
        doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower()).strip("_")

        if not doc_id:
            doc_id = f"doc_{int(datetime.datetime.now().timestamp())}"

        # Ensure unique ID
        counter = 1
        base_id = doc_id
        while doc_id in self.documents:
            doc_id = f"{base_id}_{counter}"
            counter += 1

        doc_text = f"title: {title.strip()} | text: {content.strip()}"
        embedding = self._generate_embedding(doc_text)

        doc = KnowledgeDocument(
            doc_id=doc_id,
            title=title.strip(),
            category=category.strip(),
            content=content.strip(),
            tags=tags or [],
            embedding=embedding
        )

        self.documents[doc_id] = doc
        self._save_index()

        logger.info(f"Added document '{title}' (ID: {doc_id}) to knowledge base")
        return doc

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save_index()
            return True
        return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all stored knowledge articles."""
        return [d.to_dict() for d in self.documents.values()]

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge using both lexical matching
        and Gemini semantic embeddings.
        """
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return []

        # Generate semantic embedding for the user's query
        query_embedding = None
        try:
            query_embedding = self._generate_embedding(query, is_query=True)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")

        results = []

        for doc in self.documents.values():
            doc_text = (
                f"{doc.title} {doc.category} "
                f"{' '.join(doc.tags)} {doc.content}"
            ).lower()

            doc_words = re.findall(r"\w+", doc_text)
            doc_word_count = len(doc_words) or 1

            # -----------------------------
            # 1. Existing lexical score
            # -----------------------------
            lexical_score = 0.0
            matched_terms = []

            STOP_WORDS = {"taskflow", "task", "flow", "the", "and", "for", "with", "that", "this", "from", "have", "what", "how", "why", "about", "your", "our", "you"}
            for qw in query_words:
                if len(qw) <= 2 or qw in STOP_WORDS:
                    continue

                if qw in doc.title.lower():
                    lexical_score += 5.0

                if any(qw in t.lower() for t in doc.tags):
                    lexical_score += 4.0

                count = doc_words.count(qw)

                if count > 0:
                    matched_terms.append(qw)
                    lexical_score += (count / doc_word_count) * 20.0

            # -----------------------------
            # 2. Semantic cosine similarity
            # -----------------------------
            semantic_score = 0.0

            if query_embedding and doc.embedding:
                try:
                    dot_product = sum(
                        q * d
                        for q, d in zip(query_embedding, doc.embedding)
                    )

                    query_magnitude = math.sqrt(
                        sum(q * q for q in query_embedding)
                    )

                    doc_magnitude = math.sqrt(
                        sum(d * d for d in doc.embedding)
                    )

                    if query_magnitude > 0 and doc_magnitude > 0:
                        semantic_score = dot_product / (
                            query_magnitude * doc_magnitude
                        )

                    semantic_score = max(0.0, semantic_score)

                except Exception as e:
                    logger.error(
                        f"Failed semantic scoring for '{doc.title}': {e}"
                    )

            # -----------------------------
            # 3. Combined score
            # -----------------------------
            combined_score = lexical_score + (semantic_score * 10.0)

            # Include document if either lexical or strong semantic search finds it
            if lexical_score > 0 or semantic_score >= 0.78:
                snippet = self._extract_snippet(
                    doc.content,
                    query_words
                )

                results.append({
                    "id": doc.doc_id,
                    "title": doc.title,
                    "category": doc.category,
                    "tags": doc.tags,
                    "score": round(combined_score, 3),
                    "lexical_score": round(lexical_score, 3),
                    "semantic_score": round(semantic_score, 3),
                    "matched_terms": matched_terms,
                    "snippet": snippet,
                    "full_content": doc.content
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]
    def _extract_snippet(self, content: str, query_words: set, max_length: int = 240) -> str:
        """Extract best matching paragraph or sentences from document."""
        paragraphs = content.split("\n\n")
        best_p = paragraphs[0]
        max_overlap = 0

        for p in paragraphs:
            p_lower = p.lower()
            overlap = sum(1 for w in query_words if w in p_lower)
            if overlap > max_overlap:
                max_overlap = overlap
                best_p = p

        clean_p = " ".join(best_p.split())
        return clean_p[:max_length] + ("..." if len(clean_p) > max_length else "")

# Global singleton knowledge base
default_knowledge_base = KnowledgeBase()
