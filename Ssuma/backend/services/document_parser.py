from pathlib import Path
from typing import Optional
import PyPDF2
import docx


class DocumentParser:
    @staticmethod
    def parse(file_path: str) -> Optional[str]:
        path = Path(file_path)
        if not path.exists():
            return None
        
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return DocumentParser._parse_pdf(path)
        elif ext in ['.docx', '.doc']:
            return DocumentParser._parse_docx(path)
        elif ext in ['.md', '.markdown']:
            return DocumentParser._parse_markdown(path)
        elif ext in ['.txt', '.text']:
            return DocumentParser._parse_text(path)
        else:
            return DocumentParser._parse_text(path)

    @staticmethod
    def _parse_pdf(path: Path) -> Optional[str]:
        try:
            text = []
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return '\n\n'.join(text) if text else None
        except Exception:
            return None

    @staticmethod
    def _parse_docx(path: Path) -> Optional[str]:
        try:
            doc = docx.Document(path)
            return '\n\n'.join([para.text for para in doc.paragraphs])
        except Exception:
            return None

    @staticmethod
    def _parse_markdown(path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding='utf-8')
        except Exception:
            return None

    @staticmethod
    def _parse_text(path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding='utf-8')
        except Exception:
            return None
