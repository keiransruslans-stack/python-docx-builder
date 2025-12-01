from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from docx import Document
from fastapi.responses import FileResponse
import uuid
import os

app = FastAPI()

TEMPLATE_DIR = "templates"

class Payload(BaseModel):
    template: str
    payload: dict


@app.post("/")
def generate_docx(data: Payload):

    template_path = os.path.join(TEMPLATE_DIR, data.template)

    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template not found: {data.template}")

    # Load DOCX template (MUST be .docx)
    doc = Document(template_path)

    # Add title
    doc.add_heading(data.payload.get("title", ""), level=1)

    # Add content blocks
    for block in data.payload.get("styled_blocks", []):
        style = block.get("word_style", "Normal")
        text = block.get("text", "")

        if block["type"] == "heading":
            doc.add_heading(text, level=block.get("level", 1))

        elif block["type"] == "bullet_list":
            for line in text.split("\n"):
                doc.add_paragraph(line, style="List Bullet")

        else:
            doc.add_paragraph(text, style=style)

    # Save output
    filename = f"output-{uuid.uuid4()}.docx"
    doc.save(filename)

    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename
    )
