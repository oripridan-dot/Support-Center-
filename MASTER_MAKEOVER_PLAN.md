# Master Makeover Plan: Enterprise-Grade Local AI Product Knowledge System

## Phase 1: The Local AI Stack (Week 1-2)

### The Model Choice
- **Runtime:** Ollama
- **LLM:** Llama 3.2 (3B) or Phi-3 Mini
- **Embedding Model:** `nomic-embed-text`

### The Architecture
```
Staff Interface → Local RAG Engine → Local LLM → Instant Response
                  (Your M1 Mac)      (Free)      (Private)
```

## Phase 2: The Multi-Brand Data Architecture (Week 2-3)

### The Data Model
Structure vector database by brand hierarchy (Brand -> Product Line -> Product).

### The Metadata Schema
```json
{
  "text": "The FP-30X features...",
  "brand": "Roland",
  "product_line": "Digital Pianos",
  "product_model": "FP-30X",
  "doc_type": "user_manual | spec_sheet | troubleshooting",
  "section": "Connectivity",
  "page": 23,
  "last_updated": "2024-01-15",
  "language": "en",
  "related_products": ["FP-60X", "FP-90X"],
  "accessories": ["KSC-70", "DP-10"],
  "confidence": 0.95
}
```

## Phase 3: The Staff Interface (Week 3-4)
- **Type:** Electron App (or Web App optimized for local usage)
- **Features:**
    - Multi-Modal Search
    - Context-Aware Responses
    - Answer Quality Indicators
    - Action-Oriented Outputs

## Phase 4: The Data Ingestion Pipeline (Week 4-5)
1. **Source Authentication:** Automated Login (Playwright)
2. **Document Processing:** Format Detection -> Extraction -> Cleaning -> Chunking
3. **Quality Gates:** Content Quality Check -> Brand Verification
4. **Metadata Enrichment:** Extract Product Models -> Link Related

## Phase 5: The Implementation Stack
- **Frontend:** Electron + React (or Vite + React for now)
- **Backend:** FastAPI
- **Vector DB:** Qdrant (Docker)
- **LLM Runtime:** Ollama

## Phase 6: The Rollout Strategy
- **Month 1:** Proof of Concept (1 brand)
- **Month 2:** Multi-Brand Expansion
- **Month 3:** Production Hardening
