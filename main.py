from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from docx import Document
from fastapi.responses import FileResponse
import uuid
import os

app = FastAPI()

class Payload(BaseModel):
    template: str
    payload: dict

@app.post("/")
def generate_docx(data: Payload):
    doc = Document()

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

    filename = f"output-{uuid.uuid4()}.docx"
    doc.save(filename)

    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
