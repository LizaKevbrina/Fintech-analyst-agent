import base64
from pathlib import Path
from typing import Optional, Dict, Any
import anthropic
from PIL import Image
import io
from ..models.kpi_models import ChartAnalysis
from ..utils.retry_handler import retry_with_backoff
from ..utils.logging_config import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class VisionAnalyzer:
    """Анализатор графиков через Claude Vision"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.fallback_enabled = settings.VISION_FALLBACK_ENABLED
        
    def _encode_image(self, image_path: Path) -> str:
        """Кодирование изображения в base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _validate_image(self, image_path: Path) -> bool:
        """Валидация изображения"""
        try:
            # Проверка размера (макс 5MB)
            if image_path.stat().st_size > 5 * 1024 * 1024:
                logger.warning(f"Image too large: {image_path}")
                return False
            
            # Проверка формата
            img = Image.open(image_path)
            if img.format not in ['PNG', 'JPEG', 'JPG', 'WEBP']:
                logger.warning(f"Unsupported format: {img.format}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return False
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def analyze_chart(
        self, 
        image_path: Path,
        context: Optional[str] = None
    ) -> ChartAnalysis:
        """
        Анализ графика/диаграммы
        
        Args:
            image_path: Путь к изображению
            context: Дополнительный контекст (название отчета и т.д.)
        
        Returns:
            ChartAnalysis с извлеченными данными
        
        Raises:
            ValueError: Если изображение невалидно
            VisionAPIError: Если API недоступен
        """
        try:
            # Валидация
            if not self._validate_image(image_path):
                raise ValueError(f"Invalid image: {image_path}")
            
            # Кодирование
            image_data = self._encode_image(image_path)
            
            # Prompt для анализа
            prompt = self._build_analysis_prompt(context)
            
            # Вызов Claude Vision
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # Парсинг ответа
            result = self._parse_vision_response(response.content[0].text)
            
            logger.info(f"Chart analyzed successfully: {image_path}")
            return result
            
        except anthropic.APIError as e:
            logger.error(f"Vision API error: {e}")
            
            # Graceful degradation
            if self.fallback_enabled:
                logger.info("Using fallback analysis")
                return self._fallback_analysis(image_path)
            
            raise VisionAPIError(f"Vision API unavailable: {e}")
    
    def _build_analysis_prompt(self, context: Optional[str]) -> str:
        """Построение промпта для анализа"""
        base_prompt = """Проанализируй этот финансовый график/диаграмму.

Извлеки следующую информацию:
1. Тип графика (линейный, столбчатый, круговая диаграмма)
2. Название/заголовок (если есть)
3. Ключевые значения (цифры, проценты)
4. Тренды (рост, падение, стабильность)

Верни результат в JSON формате:
{
    "chart_type": "line/bar/pie",
    "title": "название",
    "extracted_values": {"метрика": значение},
    "trends": ["тренд1", "тренд2"],
    "confidence": 0.0-1.0
}"""
        
        if context:
            base_prompt += f"\n\nКонтекст: {context}"
        
        return base_prompt
    
    def _parse_vision_response(self, text: str) -> ChartAnalysis:
        """Парсинг ответа от Vision API"""
        import json
        
        # Извлечение JSON из ответа
        try:
            # Попытка найти JSON блок
            start = text.find('{')
            end = text.rfind('}') + 1
            json_str = text[start:end]
            data = json.loads(json_str)
            
            return ChartAnalysis(**data)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from vision response")
            # Fallback парсинг
            return ChartAnalysis(
                chart_type="unknown",
                extracted_values={},
                trends=[],
                confidence=0.5
            )
    
    def _fallback_analysis(self, image_path: Path) -> ChartAnalysis:
        """Упрощенный анализ без Vision API"""
        logger.info(f"Fallback analysis for {image_path}")
        
        # Базовая информация из файла
        return ChartAnalysis(
            chart_type="unknown",
            title=image_path.stem,
            extracted_values={},
            trends=["Данные недоступны (Vision API offline)"],
            confidence=0.3
        )


class VisionAPIError(Exception):
    """Ошибка Vision API"""
    pass
