import pytest
from pathlib import Path
from services.document_parser import DocumentParser


class TestDocumentParser:

    def test_parse_unknown_extension(self):
        result = DocumentParser.parse("/tmp/unknown.xyz")
        # Returns None for non-existent file
        assert result is None

    def test_parse_markdown(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nContent here", encoding='utf-8')
        
        result = DocumentParser.parse(str(md_file))
        
        assert result == "# Test\n\nContent here"

    def test_parse_text(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text content", encoding='utf-8')
        
        result = DocumentParser.parse(str(txt_file))
        
        assert result == "Plain text content"

    def test_parse_markdown_with_chinese(self, tmp_path):
        md_file = tmp_path / "zh.md"
        md_file.write_text("# 标题\n\n中文内容", encoding='utf-8')
        
        result = DocumentParser.parse(str(md_file))
        
        assert "标题" in result
        assert "中文内容" in result