from pathlib import Path
from html import escape
import importlib.util
import json
import re
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / ".venv/Lib/site-packages"))
import pdfplumber
import yaml
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("demo_generator", ROOT / "scripts/generate_demo_pdfs.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
from app.services.pdf_service import PDFService

payload = yaml.safe_load((ROOT / "data/demo_policies/policies.yaml").read_text(encoding="utf-8"))
generator.register_font(Path("C:/Windows/Fonts/simhei.ttf"))
styles = generator.build_styles()
output = ROOT / "output/pdf/rag_test_enterprise_handbook.pdf"
output.parent.mkdir(parents=True, exist_ok=True)
all_pages = [(doc, page, index) for doc in payload["documents"] for index, page in enumerate(doc["pages"])]
story = []
for page_number, (doc, page, index) in enumerate(all_pages, 1):
    if page_number > 1:
        story.append(PageBreak())
    if index == 0:
        story.append(Paragraph(escape(doc["title"]), styles["title"]))
        metadata = f'{payload["organization"]} | {doc["owner"]} | {doc["version"]} | 生效日期 {doc["effective_date"]}'
        story.append(Paragraph(escape(metadata), styles["meta"]))
        story.append(Paragraph(escape(payload["fictional_notice"]), styles["notice"]))
    story.append(Paragraph(escape(page["page_title"]), styles["page_heading"]))
    for section in page["sections"]:
        story.append(Paragraph(escape(section["heading"]), styles["section_heading"]))
        story.extend(Paragraph(escape(p), styles["body"]) for p in section["paragraphs"])

def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8E1E8"))
    canvas.line(18 * mm, 19 * mm, A4[0] - 18 * mm, 19 * mm)
    canvas.setFont(generator.FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(18 * mm, 13 * mm, "企业知识库 RAG 测试语料 | 虚构制度")
    canvas.drawRightString(A4[0] - 18 * mm, 13 * mm, f"第 {document.page} 页 / 共 {len(all_pages)} 页")
    if document.page <= len(all_pages):
        doc, _, index = all_pages[document.page - 1]
        if index == 0:
            key = f"policy-{document.page}"
            canvas.bookmarkPage(key)
            canvas.addOutlineEntry(doc["title"], key, 0)
    canvas.restoreState()

SimpleDocTemplate(str(output), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                  topMargin=18*mm, bottomMargin=24*mm,
                  title="企业知识库 RAG 测试手册", author=payload["organization"],
                  subject=payload["fictional_notice"], pageCompression=1).build(
                      story, onFirstPage=footer, onLaterPages=footer)

normalize = lambda text: re.sub(r"\s+", "", text)
reader = PdfReader(output)
service_pages = PDFService().extract_pages(output)
with pdfplumber.open(output) as pdf:
    plumber_pages = [p.extract_text() or "" for p in pdf.pages]
assert len(reader.pages) == len(all_pages) == len(service_pages) == len(plumber_pages)
for i, (_, page, _) in enumerate(all_pages):
    source = [page["page_title"]]
    for section in page["sections"]:
        source.extend([section["heading"], *section["paragraphs"]])
    for extractor, texts in [("project PDFService", service_pages), ("pdfplumber", plumber_pages)]:
        extracted = normalize(texts[i])
        assert all(normalize(part) in extracted for part in source), (extractor, i + 1)
        assert "\ufffd" not in texts[i]
assert not reader.is_encrypted
text_path = output.with_suffix(".txt")
text_path.write_text("\n\n".join(f"=== 第 {i} 页 ===\n{text}" for i, text in enumerate(service_pages, 1)), encoding="utf-8")
report = {"file": str(output), "pages": len(reader.pages), "size_bytes": output.stat().st_size,
          "text_characters_per_page": [len(normalize(t)) for t in service_pages],
          "verified": ["All source paragraphs match project PDFService extraction", "All source paragraphs match pdfplumber extraction", "Not encrypted"],
          "page_topics": [doc["title"] + " / " + page["page_title"] for doc, page, _ in all_pages]}
(ROOT / "tmp/pdfs/verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
