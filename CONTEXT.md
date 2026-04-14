# Project Context — python-docx-builder + n8n Workflow

## What this project does

An n8n automation that accepts raw financial text via webhook, uses LLMs to clean/classify/structure it, then calls a Python microservice hosted on Railway to generate a branded `.docx` Word file using a custom GBM Securities template.

---

## Architecture

```
POST /raw-text-to-docx (n8n Webhook)
        │
        ▼
[Clean Raw Text]          — JS: strip HTML, decode entities, normalise whitespace
        │
        ▼
[Document Clarifier]      — LLM: extract metadata, synopsis, entities, compliance markers
        │
        ▼
[Document Type Classifier]— LLM: classify into one of 10 document types
        │
        ▼
[Structure Document]      — LLM: segment text into heading/paragraph/bullet/note blocks (JSON)
        │
        ▼
[Map Semantic Blocks      — JS: parse LLM JSON → flat styled_blocks array with Word style names
 to Word Styles]
        │
        ▼
[Python DOCX Builder]     — HTTP POST → Railway FastAPI service → returns .docx binary
        │
        ▼
[Return DOCX File]        — n8n respondToWebhook → streams .docx to original caller
```

---

## Repository — `python-docx-builder`

### File structure
```
main.py                          # FastAPI app (the Railway microservice)
requirements.txt                 # Pinned Python deps
Dockerfile                       # python:3.11-slim, runs uvicorn on port 8000
templates/
  GBM Securities Template11.docx # The branded Word template (has custom GBM styles)
n8n_workflow_fixed.json          # Fixed n8n workflow — import this into n8n
```

### API contract (`POST /`)
```json
{
  "template": "GBM Securities Template11.docx",
  "payload": {
    "title": "optional string",
    "document_type": "optional string",
    "styled_blocks": [
      { "type": "heading",     "text": "...", "word_style": "Heading 1",      "level": 1 },
      { "type": "paragraph",   "text": "...", "word_style": "GBM Normal1" },
      { "type": "bullet_list", "text": "line1\nline2", "word_style": "GBM Dash Bullet" },
      { "type": "note",        "text": "...", "word_style": "GBM Note" },
      { "type": "raw",         "text": "...", "word_style": "GBM Raw" }
    ]
  }
}
```

### Allowed Word styles (must exist in the .docx template)
- `Heading 1`, `Heading 2`, `Heading 3`
- `GBM Normal1`, `GBM Dash Bullet`, `GBM Note`, `GBM Raw`

### Auth
Optional. Set `API_KEY` env var on Railway. Middleware checks `X-API-Key` header on all routes except `/health`. Leave `API_KEY` empty to disable.

---

## Bugs fixed in this session

### Railway service (`main.py`)
| Issue | Fix |
|---|---|
| API key auth was deleted | Re-added HTTP middleware; opt-in via `API_KEY` env var |
| `/tmp` files never deleted | `BackgroundTasks.add_task(os.remove, out_path)` runs after response is streamed |
| Port mismatch (8080 vs 8000) | `__main__` default aligned to `8000` to match Dockerfile |
| Unpinned dependencies | Pinned to `fastapi==0.115.12`, `uvicorn==0.34.0`, `python-docx==1.1.2` |

### n8n workflow (`n8n_workflow_fixed.json`)
| Node | Bug | Fix |
|---|---|---|
| Python DOCX Builder | `jsonBody` used `{{$json}}` inside a string → serialised as `[object Object]` → invalid JSON | Changed to expression object literal `={{ ({ "template": "...", "payload": $json }) }}` |
| Python DOCX Builder | No auth header sent to Railway | Added `X-API-Key: {{ $vars.DOCX_API_KEY }}` header |
| Map Semantic Blocks | `JSON.parse()` crashed when LLM wrapped output in ` ```json ``` ` fences | Strip fences with regex before parsing; throw readable error if still invalid |
| Return DOCX File | `inputDataFieldName` not set → empty response body returned to caller | Set to `data` (the binary key n8n's HTTP Request node uses) |
| All LLM system prompts | Did not explicitly forbid markdown code fences | Added "No markdown code fences. No prose." to every system prompt |

---

## n8n setup required

1. **Import** `n8n_workflow_fixed.json` into your n8n instance (replace the old workflow)
2. **n8n Variables** → create `DOCX_API_KEY` = same value as `API_KEY` on Railway
3. **Railway** → set `API_KEY` env var to a strong secret string
4. Re-connect the OpenAI credentials in the three LLM nodes after import (n8n strips credential IDs on import)

---

## LLM nodes (currently OpenAI — migration to Anthropic pending)

| Node | Model | Purpose |
|---|---|---|
| Document Clarifier | `gpt-4o-mini` | Extract metadata: headings, entities, compliance markers, synopsis |
| Document Type Classifier | `gpt-4o-mini` | Classify into 1 of 10 document type strings |
| Structure Document | `o4-mini` | Segment full text into typed blocks with JSON schema output |

> **Next step:** Migrate all three LLM nodes from OpenAI to Anthropic Claude models with model selection research per step.

---

## Key constraints to keep in mind
- `pydantic<2.0` is intentional — the FastAPI code uses Pydantic v1 API
- The `.docx` template must contain all custom style names or `python-docx` will throw at render time
- `bullet_list` blocks are split on `\n` — each line becomes a separate bullet paragraph
- Heading blocks use `level` (not `word_style`) to pick the Word style; `word_style` is validated but ignored for headings
