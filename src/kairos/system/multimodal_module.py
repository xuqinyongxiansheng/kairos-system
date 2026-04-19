"""
多模态能力模块
实现图片描述、文档解析、截图分析等多模态交互功能
整合 002/AAagent 的优秀实现
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModalityType(Enum):
    """模态类型枚举"""
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    SCREENSHOT = "screenshot"


class DocumentType(Enum):
    """文档类型枚举"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


@dataclass
class ImageDescription:
    """图片描述数据类"""
    image_path: str
    description: str
    objects: List[str]
    scenes: List[str]
    colors: List[str]
    confidence: float
    timestamp: datetime


@dataclass
class DocumentContent:
    """文档内容数据类"""
    document_path: str
    document_type: str
    title: str
    content: str
    pages: int
    word_count: int
    timestamp: datetime


@dataclass
class ScreenshotAnalysis:
    """截图分析数据类"""
    screenshot_path: str
    text_content: str
    ui_elements: List[Dict[str, Any]]
    confidence: float
    timestamp: datetime


class MultimodalModule:
    """多模态模块类"""
    
    def __init__(self):
        self.clip_api_url = "http://localhost:7860"
        
        # 尝试导入可选依赖
        self.PyPDF2 = None
        self.Document = None
        self.pytesseract = None
        
        try:
            import PyPDF2
            self.PyPDF2 = PyPDF2
        except ImportError:
            pass
        
        try:
            from docx import Document as DocxDocument
            self.Document = DocxDocument
        except ImportError:
            pass
        
        try:
            import pytesseract
            self.pytesseract = pytesseract
        except ImportError:
            pass
        
        logger.info("多模态模块初始化完成")
    
    def set_tesseract_path(self, path: str):
        """设置 Tesseract OCR 路径"""
        if self.pytesseract:
            self.pytesseract.pytesseract.tesseract_cmd = path
    
    def describe_image(self, image_path: str) -> Optional[ImageDescription]:
        """描述图片内容"""
        if not os.path.exists(image_path):
            return None
        
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            return None
        
        try:
            description_data = self._generate_image_description(image_path)
            
            return ImageDescription(
                image_path=image_path,
                description=description_data["description"],
                objects=description_data["objects"],
                scenes=description_data["scenes"],
                colors=description_data["colors"],
                confidence=description_data["confidence"],
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"描述图片失败：{e}")
            return None
    
    def parse_document(self, document_path: str) -> Optional[DocumentContent]:
        """解析文档内容"""
        if not os.path.exists(document_path):
            return None
        
        ext = os.path.splitext(document_path)[1].lower()
        
        try:
            if ext == '.pdf':
                return self._parse_pdf(document_path)
            elif ext == '.docx':
                return self._parse_docx(document_path)
            elif ext in ['.txt', '.md']:
                return self._parse_text(document_path)
            else:
                return None
                
        except Exception as e:
            logger.error(f"解析文档失败：{e}")
            return None
    
    def analyze_screenshot(self, screenshot_path: str) -> Optional[ScreenshotAnalysis]:
        """分析屏幕截图"""
        if not os.path.exists(screenshot_path):
            return None
        
        try:
            text_content = self._extract_text_from_image(screenshot_path)
            ui_elements = self._analyze_ui_elements(text_content)
            
            return ScreenshotAnalysis(
                screenshot_path=screenshot_path,
                text_content=text_content,
                ui_elements=ui_elements,
                confidence=0.85,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"分析截图失败：{e}")
            return None
    
    def process_multimodal_input(self, input_path: str, modality_type: str = None) -> Dict[str, Any]:
        """处理多模态输入（统一入口）"""
        if not os.path.exists(input_path):
            return {"success": False, "error": "文件不存在"}
        
        # 自动检测模态类型
        if not modality_type:
            ext = os.path.splitext(input_path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                modality_type = ModalityType.IMAGE.value
            elif ext in ['.pdf', '.docx', '.txt', '.md']:
                modality_type = ModalityType.DOCUMENT.value
            else:
                return {"success": False, "error": "不支持的文件类型"}
        
        try:
            if modality_type == ModalityType.IMAGE.value:
                result = self.describe_image(input_path)
                if result:
                    return {
                        "success": True,
                        "type": "image_description",
                        "data": {
                            "description": result.description,
                            "objects": result.objects,
                            "scenes": result.scenes,
                            "colors": result.colors,
                            "confidence": result.confidence,
                            "summary": self.generate_image_summary(result)
                        }
                    }
            
            elif modality_type == ModalityType.DOCUMENT.value:
                result = self.parse_document(input_path)
                if result:
                    return {
                        "success": True,
                        "type": "document_content",
                        "data": {
                            "title": result.title,
                            "document_type": result.document_type,
                            "pages": result.pages,
                            "word_count": result.word_count,
                            "summary": self.generate_document_summary(result)
                        }
                    }
            
            elif modality_type == ModalityType.SCREENSHOT.value:
                result = self.analyze_screenshot(input_path)
                if result:
                    return {
                        "success": True,
                        "type": "screenshot_analysis",
                        "data": {
                            "text_content": result.text_content,
                            "ui_elements": result.ui_elements,
                            "confidence": result.confidence,
                            "summary": self.generate_screenshot_summary(result)
                        }
                    }
            
            return {"success": False, "error": "处理失败"}
            
        except Exception as e:
            logger.error(f"多模态处理失败：{e}")
            return {"success": False, "error": str(e)}
    
    def _generate_image_description(self, image_path: str) -> Dict[str, Any]:
        """生成图片描述（模拟实现）"""
        file_size = os.path.getsize(image_path) / 1024 / 1024  # MB
        
        description = "一张数字图片"
        objects = []
        scenes = []
        colors = []
        
        if file_size < 0.5:
            description = "一张小尺寸的图片，可能是图标或简单图形"
            objects = ["图形", "图标"]
            scenes = ["抽象"]
            colors = ["单色"]
        elif file_size < 2:
            description = "一张中等尺寸的图片，可能包含人物或景物"
            objects = ["人物", "景物", "建筑"]
            scenes = ["户外", "室内"]
            colors = ["彩色"]
        else:
            description = "一张大尺寸的高清图片，包含丰富的细节"
            objects = ["人物", "景物", "建筑", "自然景观"]
            scenes = ["自然", "城市", "室内"]
            colors = ["多彩", "鲜艳"]
        
        return {
            "description": description,
            "objects": objects,
            "scenes": scenes,
            "colors": colors,
            "confidence": 0.75
        }
    
    def _parse_pdf(self, pdf_path: str) -> Optional[DocumentContent]:
        """解析 PDF 文档"""
        if not self.PyPDF2:
            return None
        
        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)
                pages = len(reader.pages)
                
                content = []
                for page_num in range(min(pages, 10)):
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        content.append(text)
                
                full_content = "\n".join(content)
                word_count = len(full_content.split())
                
                title = os.path.basename(pdf_path).replace('.pdf', '')
                
                return DocumentContent(
                    document_path=pdf_path,
                    document_type=DocumentType.PDF.value,
                    title=title,
                    content=full_content,
                    pages=pages,
                    word_count=word_count,
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"解析 PDF 失败：{e}")
            return None
    
    def _parse_docx(self, docx_path: str) -> Optional[DocumentContent]:
        """解析 Word 文档"""
        if not self.Document:
            return None
        
        try:
            doc = self.Document(docx_path)
            
            content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content.append(paragraph.text)
            
            full_content = "\n".join(content)
            word_count = len(full_content.split())
            
            title = os.path.basename(docx_path).replace('.docx', '')
            
            return DocumentContent(
                document_path=docx_path,
                document_type=DocumentType.DOCX.value,
                title=title,
                content=full_content,
                pages=1,
                word_count=word_count,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"解析 DOCX 失败：{e}")
            return None
    
    def _parse_text(self, text_path: str) -> Optional[DocumentContent]:
        """解析文本文件"""
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            word_count = len(content.split())
            ext = os.path.splitext(text_path)[1].lower()
            
            title = os.path.basename(text_path).replace(ext, '')
            lines = content.split('\n')
            for line in lines[:3]:
                if line.strip() and 10 < len(line.strip()) < 100:
                    title = line.strip()
                    break
            
            doc_type = DocumentType.TXT.value if ext == '.txt' else DocumentType.MD.value
            
            return DocumentContent(
                document_path=text_path,
                document_type=doc_type,
                title=title,
                content=content,
                pages=1,
                word_count=word_count,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"解析文本文件失败：{e}")
            return None
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """从图片中提取文本 (OCR)"""
        if not self.pytesseract:
            return "OCR 功能未可用，请安装 pytesseract"
        
        try:
            text = self.pytesseract.image_to_string(image_path, lang='chi_sim+eng')
            return text
        except Exception as e:
            logger.error(f"OCR 提取失败：{e}")
            return f"OCR 提取失败：{str(e)}"
    
    def _analyze_ui_elements(self, text_content: str) -> List[Dict[str, Any]]:
        """分析 UI 元素"""
        ui_elements = []
        lines = text_content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 识别按钮
            if any(kw in line.lower() for kw in ['button', '按钮', 'click', '点击']):
                ui_elements.append({"type": "button", "text": line, "position": {"line": i + 1}})
            
            # 识别输入框
            elif any(kw in line.lower() for kw in ['input', '输入', 'textbox']):
                ui_elements.append({"type": "input", "text": line, "position": {"line": i + 1}})
            
            # 识别标题
            elif len(line) > 20 and line.isupper():
                ui_elements.append({"type": "heading", "text": line, "position": {"line": i + 1}})
        
        return ui_elements
    
    def generate_image_summary(self, image_desc: ImageDescription) -> str:
        """生成图片描述摘要"""
        parts = [f"图片描述：{image_desc.description}"]
        
        if image_desc.objects:
            parts.append(f"包含对象：{', '.join(image_desc.objects)}")
        if image_desc.scenes:
            parts.append(f"场景类型：{', '.join(image_desc.scenes)}")
        if image_desc.colors:
            parts.append(f"色彩特点：{', '.join(image_desc.colors)}")
        
        parts.append(f"置信度：{image_desc.confidence:.1%}")
        
        return "\n".join(parts)
    
    def generate_document_summary(self, doc_content: DocumentContent) -> str:
        """生成文档摘要"""
        parts = [
            f"文档：{doc_content.title}",
            f"类型：{doc_content.document_type.upper()}",
            f"页数：{doc_content.pages}",
            f"字数：{doc_content.word_count}"
        ]
        
        lines = doc_content.content.split('\n')
        preview_lines = [l.strip() for l in lines if l.strip()][:5]
        
        if preview_lines:
            parts.append("\n内容预览：")
            parts.extend([f"  {l}" for l in preview_lines])
        
        return "\n".join(parts)
    
    def generate_screenshot_summary(self, screenshot_analysis: ScreenshotAnalysis) -> str:
        """生成截图分析摘要"""
        parts = [f"截图分析结果：\n"]
        
        if screenshot_analysis.text_content.strip():
            parts.append(f"识别文本：\n{screenshot_analysis.text_content}\n")
        
        if screenshot_analysis.ui_elements:
            parts.append("UI 元素：\n")
            for elem in screenshot_analysis.ui_elements:
                parts.append(f"  - {elem['type']}: {elem['text']}")
        
        parts.append(f"\n置信度：{screenshot_analysis.confidence:.1%}")
        
        return "\n".join(parts)


multimodal_module = MultimodalModule()
