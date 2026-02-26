from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from docx import Document
from fastapi.responses import FileResponse
import uuid
import os
import uvicorn

app = FastAPI()

TEMPLATE_DIR = "templates"
API_KEY = os.environ.get("API_KEY")  # задаётся в Cloud Run → Variables & Secrets


class Payload(BaseModel):
    template: str
    payload: dict


# 🔐 API KEY middleware
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if API_KEY:
        client_key = request.headers.get("X-API-Key")
        if client_key != API_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized")
    return await call_next(request)


@app.post("/")
def generate_docx(data: Payload):

    template_path = os.path.join(TEMPLATE_DIR, data.template)

    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template not found: {data.template}")

    # Load template
    doc = Document(template_path)

    # Add title if exists
    title = data.payload.get("title")
    if title:
        doc.add_heading(title, level=1)

    # Add content blocks
    for block in data.payload.get("styled_blocks", []):
        block_type = block.get("type")
        text = block.get("text", "")
        word_style = block.get("word_style", "Normal")

        if block_type == "heading":
            level = block.get("level", 1)
            doc.add_heading(text, level=level)

        elif block_type == "bullet_list":
            for line in text.split("\n"):
                if line.strip():
                    doc.add_paragraph(line.strip(), style=word_style)

        else:
            doc.add_paragraph(text, style=word_style)

    # Save output
    filename = f"/tmp/output_{uuid.uuid4()}.docx"
    doc.save(filename)

    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="formatted_document.docx"
    )


# 🚀 Cloud Run entrypoint
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
