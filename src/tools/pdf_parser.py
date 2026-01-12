import pdfplumber
from pathlib import Path
from typing import Dict, Any, List
import io
from PIL import Image

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class PDFParser:
    """
    Parser для PDF документов
    
    Extracts:
    - Text content
    - Tables
    - Images (для графиков)
    - Metadata
    """
    
    def parse(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Парсинг PDF файла
        
        Args:
            pdf_path: Путь к PDF
        
        Returns:
            Dict с текстом, таблицами, изображениями и метаданными
        """
        logger.info(f"Parsing PDF: {pdf_path}")
        
        result = {
            'text': '',
            'tables': [],
            'images': [],
            'metadata': {},
            'num_pages': 0,
            'file_size': pdf_path.stat().st_size
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                result['num_pages'] = len(pdf.pages)
                result['metadata'] = pdf.metadata
                
                all_text = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Извлечение текста
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(page_text)
                    
                    # Извлечение таблиц
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            result['tables'].append({
                                'page': page_num,
                                'data': table
                            })
                    
                    # Извлечение изображений
                    for img_obj in page.images:
                        try:
                            # Сохранение изображения
                            img_path = self._save_image(
                                page,
                                img_obj,
                                pdf_path,
                                page_num
                            )
                            result['images'].append(img_path)
                        except Exception as e:
                            logger.warning(f"Failed to extract image: {e}")
                
                result['text'] = '\n\n'.join(all_text)
                
                logger.info(
                    f"✅ PDF parsed: {result['num_pages']} pages, "
                    f"{len(result['tables'])} tables, "
                    f"{len(result['images'])} images"
                )
                
        except Exception as e:
            logger.error(f"PDF parsing error: {e}", exc_info=True)
            raise
        
        return result
    
    def _save_image(
        self,
        page,
        img_obj: Dict,
        pdf_path: Path,
        page_num: int
    ) -> Path:
        """Сохранение изображения из PDF"""
        # Создание папки для изображений
        img_dir = Path(f"/tmp/pdf_images/{pdf_path.stem}")
        img_dir.mkdir(parents=True, exist_ok=True)
        
        # Имя файла
        img_filename = f"page_{page_num}_img_{img_obj['name']}.png"
        img_path = img_dir / img_filename
        
        # Извлечение и сохранение
        try:
            # Получение изображения из страницы
            bbox = (img_obj['x0'], img_obj['top'], img_obj['x1'], img_obj['bottom'])
            cropped = page.crop(bbox)
            
            # Сохранение как изображение
            img = cropped.to_image(resolution=150)
            img.save(img_path)
            
            return img_path
        except Exception as e:
            logger.warning(f"Image extraction failed: {e}")
            raise
