from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PDFService:
    """负责从文本型 PDF 中提取每一页的文字。"""

    def extract_pages(
        self,
        pdf_path: str | Path,
    ) -> list[str]:
        """从本地 PDF 路径中按页提取文字。"""
        path = Path(pdf_path)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF 文件不存在：{path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("只支持 PDF 文件")

        reader = PdfReader(path)
        return self._extract_text(reader)

    def extract_pages_from_bytes(
        self,
        pdf_bytes: bytes,
    ) -> list[str]:
        """从上传得到的 PDF 字节中按页提取文字。"""
        if not pdf_bytes:
            raise ValueError("PDF 文件不能为空")

        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            return self._extract_text(reader)
        except (PdfReadError, EOFError) as exc:
            raise ValueError("PDF 文件无法解析") from exc

    def _extract_text(
        self,
        reader: PdfReader,
    ) -> list[str]:
        """复用按页提取文字的共同逻辑。"""
        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text.strip())

        if not any(pages):
            raise ValueError(
                "没有提取到文本，请确认 PDF 包含可复制的文字"
            )

        return pages