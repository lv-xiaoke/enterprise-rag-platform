from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html import escape
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "demo_policies" / "policies.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "demo_policies" / "pdfs"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "demo_policies" / "manifest.json"
FONT_NAME = "DemoPolicyCJK"
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
)
SENSITIVE_PATTERNS = {
    "电子邮箱": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    ),
    "中国大陆手机号": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "中国大陆身份证号": re.compile(
        r"(?<!\d)\d{17}[0-9Xx](?!\d)"
    ),
    "疑似银行卡号": re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
    "疑似 API Key": re.compile(
        r"(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16})"
    ),
    "数据库连接串": re.compile(
        r"(?:postgresql|postgres)://[^\s]+",
        re.IGNORECASE,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成并验证 Day 9 虚构企业制度 PDF。"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="YAML 事实源路径。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="PDF 输出目录。",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="完整性清单路径。",
    )
    parser.add_argument(
        "--font-path",
        type=Path,
        default=None,
        help="可选的中文 TrueType/OpenType 字体路径。",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="不重新生成，只验证已有 PDF 和清单。",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 必须是非空字符串")
    return value.strip()


def scan_sensitive_data(text: str) -> None:
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(text):
            raise ValueError(
                f"演示数据疑似包含{label}；请改为不可联系的虚构描述"
            )


def page_source_text(page: dict[str, Any]) -> str:
    parts = [require_non_empty_string(page.get("page_title"), "page_title")]
    sections = page.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("每一页都必须包含至少一个 section")

    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("section 必须是对象")
        parts.append(
            require_non_empty_string(section.get("heading"), "heading")
        )
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            raise ValueError("每个 section 都必须包含 paragraphs")
        parts.extend(
            require_non_empty_string(paragraph, "paragraph")
            for paragraph in paragraphs
        )

    return "\n".join(parts)


def validate_source(payload: Any, raw_source: str) -> dict[str, Any]:
    scan_sensitive_data(raw_source)
    if not isinstance(payload, dict):
        raise ValueError("YAML 根节点必须是对象")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version 必须为 1")

    require_non_empty_string(payload.get("corpus_version"), "corpus_version")
    require_non_empty_string(payload.get("organization"), "organization")
    require_non_empty_string(
        payload.get("fictional_notice"),
        "fictional_notice",
    )

    scenarios = payload.get("cross_document_scenarios")
    if not isinstance(scenarios, list) or len(scenarios) < 2:
        raise ValueError("至少需要两个跨文档场景")
    for scenario in scenarios:
        require_non_empty_string(scenario, "cross_document_scenario")

    absent_topics = payload.get("reserved_absent_topics")
    if not isinstance(absent_topics, list) or len(absent_topics) < 3:
        raise ValueError("至少需要三个明确的无答案主题")
    for topic in absent_topics:
        require_non_empty_string(topic, "reserved_absent_topic")

    documents = payload.get("documents")
    if not isinstance(documents, list) or not 3 <= len(documents) <= 5:
        raise ValueError("documents 数量必须在 3 到 5 之间")

    filenames: set[str] = set()
    domains: set[str] = set()
    for document_index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"第 {document_index} 个 document 必须是对象")

        filename = require_non_empty_string(
            document.get("filename"),
            f"documents[{document_index}].filename",
        )
        if Path(filename).name != filename or not filename.lower().endswith(
            ".pdf"
        ):
            raise ValueError(f"非法 PDF 文件名：{filename}")
        if filename in filenames:
            raise ValueError(f"PDF 文件名重复：{filename}")
        filenames.add(filename)

        require_non_empty_string(document.get("title"), "title")
        domain = require_non_empty_string(document.get("domain"), "domain")
        domains.add(domain)
        require_non_empty_string(document.get("owner"), "owner")
        require_non_empty_string(document.get("version"), "version")
        require_non_empty_string(
            document.get("effective_date"),
            "effective_date",
        )

        pages = document.get("pages")
        if not isinstance(pages, list) or len(pages) != 2:
            raise ValueError(f"{filename} 必须恰好定义两页")

        for page_number, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                raise ValueError(f"{filename} 第 {page_number} 页必须是对象")
            source_text = normalize_text(page_source_text(page))
            markers = page.get("expected_markers")
            if not isinstance(markers, list) or len(markers) < 2:
                raise ValueError(
                    f"{filename} 第 {page_number} 页至少需要两个标记"
                )
            for marker in markers:
                marker_text = require_non_empty_string(
                    marker,
                    "expected_marker",
                )
                if normalize_text(marker_text) not in source_text:
                    raise ValueError(
                        f"{filename} 第 {page_number} 页的标记不在正文中"
                    )

    if len(domains) < 2:
        raise ValueError("演示语料至少覆盖两个业务领域")

    return payload


def resolve_font(explicit_font: Path | None) -> Path:
    candidates = (
        (explicit_font,) if explicit_font is not None else FONT_CANDIDATES
    )
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "未找到可嵌入的中文字体；请使用 --font-path 指定 .ttf 或 .ttc 文件"
    )


def register_font(font_path: Path) -> None:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(
        TTFont(
            FONT_NAME,
            str(font_path),
            subfontIndex=0,
        )
    )


def build_styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            name="PolicyTitle",
            fontName=FONT_NAME,
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=8 * mm,
            wordWrap="CJK",
        ),
        "meta": ParagraphStyle(
            name="PolicyMeta",
            fontName=FONT_NAME,
            fontSize=9,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#52616B"),
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
        "page_heading": ParagraphStyle(
            name="PageHeading",
            fontName=FONT_NAME,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#1F5A75"),
            spaceBefore=3 * mm,
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
        "section_heading": ParagraphStyle(
            name="SectionHeading",
            fontName=FONT_NAME,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#234E52"),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            name="PolicyBody",
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=18,
            firstLineIndent=2 * 10.5,
            textColor=colors.HexColor("#1F2933"),
            spaceAfter=2.5 * mm,
            wordWrap="CJK",
        ),
        "notice": ParagraphStyle(
            name="PolicyNotice",
            fontName=FONT_NAME,
            fontSize=9,
            leading=15,
            textColor=colors.HexColor("#8A3B12"),
            backColor=colors.HexColor("#FFF4E5"),
            borderColor=colors.HexColor("#F2C078"),
            borderWidth=0.5,
            borderPadding=6,
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
    }


def make_page_callback(
    title: str,
    organization: str,
    notice: str,
):
    def draw_page(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setTitle(title)
        canvas.setAuthor(organization)
        canvas.setSubject(notice)
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(
            18 * mm,
            12 * mm,
            f"{organization}｜公开演示虚构资料",
        )
        canvas.drawRightString(
            A4[0] - 18 * mm,
            12 * mm,
            f"第 {document.page} 页",
        )
        canvas.restoreState()

    return draw_page


def build_pdf(
    document_data: dict[str, Any],
    organization: str,
    notice: str,
    output_path: Path,
) -> None:
    styles = build_styles()
    pdf_document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=document_data["title"],
        author=organization,
        subject=notice,
        pageCompression=1,
        invariant=1,
    )

    story: list[Any] = []
    for page_index, page in enumerate(document_data["pages"]):
        if page_index > 0:
            story.append(PageBreak())
        else:
            story.append(
                Paragraph(
                    escape(document_data["title"]),
                    styles["title"],
                )
            )
            metadata = (
                f"{escape(organization)}｜{escape(document_data['owner'])}｜"
                f"版本 {escape(document_data['version'])}｜"
                f"生效日期 {escape(document_data['effective_date'])}"
            )
            story.append(Paragraph(metadata, styles["meta"]))
            story.append(
                Paragraph(
                    escape(notice),
                    styles["notice"],
                )
            )

        story.append(
            Paragraph(
                escape(page["page_title"]),
                styles["page_heading"],
            )
        )
        for section in page["sections"]:
            story.append(
                Paragraph(
                    escape(section["heading"]),
                    styles["section_heading"],
                )
            )
            for paragraph in section["paragraphs"]:
                story.append(
                    Paragraph(
                        escape(paragraph),
                        styles["body"],
                    )
                )
            story.append(Spacer(1, 1.5 * mm))

    callback = make_page_callback(
        title=document_data["title"],
        organization=organization,
        notice=notice,
    )
    pdf_document.build(
        story,
        onFirstPage=callback,
        onLaterPages=callback,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_pdf(
    document_data: dict[str, Any],
    pdf_path: Path,
) -> dict[str, Any]:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"缺少演示 PDF：{pdf_path}")

    reader = PdfReader(pdf_path)
    expected_pages = document_data["pages"]
    if len(reader.pages) != len(expected_pages):
        raise ValueError(
            f"{pdf_path.name} 页数应为 {len(expected_pages)}，"
            f"实际为 {len(reader.pages)}"
        )

    page_text_characters: list[int] = []
    for page_number, (pdf_page, page_data) in enumerate(
        zip(reader.pages, expected_pages),
        start=1,
    ):
        extracted_text = pdf_page.extract_text() or ""
        normalized_page = normalize_text(extracted_text)
        if not normalized_page:
            raise ValueError(
                f"{pdf_path.name} 第 {page_number} 页没有可提取文字"
            )
        scan_sensitive_data(extracted_text)
        for marker in page_data["expected_markers"]:
            if normalize_text(marker) not in normalized_page:
                raise ValueError(
                    f"{pdf_path.name} 第 {page_number} 页缺少预期事实标记"
                )
        page_text_characters.append(len(normalized_page))

    return {
        "filename": pdf_path.name,
        "title": document_data["title"],
        "domain": document_data["domain"],
        "sha256": sha256_file(pdf_path),
        "page_count": len(reader.pages),
        "page_text_characters": page_text_characters,
        "expected_markers": [
            page["expected_markers"] for page in expected_pages
        ],
    }


def build_manifest(
    payload: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    document_results = [
        inspect_pdf(
            document_data=document_data,
            pdf_path=output_dir / document_data["filename"],
        )
        for document_data in payload["documents"]
    ]
    return {
        "schema_version": 1,
        "corpus_version": payload["corpus_version"],
        "organization": payload["organization"],
        "fictional_notice": payload["fictional_notice"],
        "document_count": len(document_results),
        "cross_document_scenarios": payload[
            "cross_document_scenarios"
        ],
        "reserved_absent_topics": payload["reserved_absent_topics"],
        "documents": document_results,
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_frozen_manifest(
    actual_manifest: dict[str, Any],
    manifest_path: Path,
) -> None:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"缺少冻结清单：{manifest_path}")
    expected_manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    if expected_manifest != actual_manifest:
        raise ValueError(
            "现有 PDF 与 manifest.json 不一致；请确认是否需要升级语料版本"
        )


def main() -> None:
    args = parse_args()
    source_path = args.source.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = args.manifest.resolve()

    if not source_path.is_file():
        raise FileNotFoundError(f"找不到 YAML 事实源：{source_path}")
    raw_source = source_path.read_text(encoding="utf-8")
    payload = validate_source(
        yaml.safe_load(raw_source),
        raw_source,
    )

    if not args.verify_only:
        font_path = resolve_font(args.font_path)
        register_font(font_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        for document_data in payload["documents"]:
            build_pdf(
                document_data=document_data,
                organization=payload["organization"],
                notice=payload["fictional_notice"],
                output_path=output_dir / document_data["filename"],
            )
        print(f"使用字体：{font_path}")

    actual_manifest = build_manifest(payload, output_dir)
    if args.verify_only:
        verify_frozen_manifest(actual_manifest, manifest_path)
    else:
        write_manifest(actual_manifest, manifest_path)

    for document in actual_manifest["documents"]:
        print(
            "OK："
            f"{document['filename']}，"
            f"{document['page_count']} 页，"
            f"每页文字数 {document['page_text_characters']}"
        )
    print(f"语料版本：{actual_manifest['corpus_version']}")
    print(f"完整性清单：{manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR：{exc}", file=sys.stderr)
        raise SystemExit(1) from None