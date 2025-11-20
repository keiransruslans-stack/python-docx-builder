from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from docx import Document
from fastapi.responses import FileResponse
import uuid
import os

app = FastAPI()

TEMPLATE_DIR = "templates"   # <--- NEW

class Payload(BaseModel):
    template: str     # name of template file (string)
    payload: dict     # JSON data containing title + styled blocks


@app.post("/")
def generate_docx(data: Payload):

    # Full path to template file
    template_path = os.path.join(TEMPLATE_DIR, data.template)

    # Check if template exists
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template not found: {data.template}")

    # Load DOCX/DOTX template
    doc = Document(template_path)   # <--- FIX: USE TEMPLATE HERE

    # Title
    doc.add_heading(data.payload.get("title", ""), level=1)

    # Styled blocks
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

    # Save output file
    filename = f"output-{uuid.uuid4()}.docx"
    doc.save(filename)

    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
