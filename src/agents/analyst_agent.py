"""
Главный агент-аналитик на базе SmolAgents
Использует FAISS для семантического поиска, Vision для графиков,
CodeAgent для SQL, и структурированный вывод через Pydantic
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    tool,
    DuckDuckGoSearchTool,
)
from smolagents.models import LiteLLMModel

from ..tools.pdf_parser import PDFParser
from ..tools.excel_parser import ExcelParser
from ..tools.vision_analyzer import VisionAnalyzer, VisionAPIError
from ..tools.calculator import FinancialCalculator
from ..tools.faiss_search import FAISSSearchEngine
from ..models.kpi_models import (
    AnalysisResult,
    ReportType,
    BalanceSheetKPI,
    IncomeStatementKPI,
    ChartAnalysis,
    FinancialMetric
)
from ..utils.logging_config import get_logger
from ..utils.retry_handler import retry_with_backoff
from ..core.config import settings
from ..core.exceptions import ProcessingError

logger = get_logger(__name__)


class FinancialAnalystAgent:
    """
    Production-ready финансовый аналитик
    
    Capabilities:
    - Извлечение текста из PDF/Excel
    - Семантический поиск по архиву отчетов (FAISS)
    - Распознавание графиков через Vision API
    - SQL генерация для структурирования данных
    - Извлечение KPI с валидацией (Pydantic)
    
    Architecture:
    - Primary: ToolCallingAgent (оркестрация)
    - Secondary: CodeAgent (SQL generation)
    - Tools: PDF/Excel parsers, Vision, Calculator, FAISS
    """
    
    def __init__(self):
        """Инициализация агента и всех компонентов"""
        logger.info("Initializing FinancialAnalystAgent")
        
        # LLM модель (через LiteLLM для унификации)
        self.llm = LiteLLMModel(
            model_id=settings.LLM_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.1,  # Низкая для точности
        )
        
        # Tools
        self.pdf_parser = PDFParser()
        self.excel_parser = ExcelParser()
        self.vision_analyzer = VisionAnalyzer()
        self.calculator = FinancialCalculator()
        self.faiss_engine = FAISSSearchEngine(
            index_path=settings.FAISS_INDEX_PATH
        )
        
        # CodeAgent для SQL генерации
        self.code_agent = CodeAgent(
            tools=[],
            model=self.llm,
            max_steps=5,
            verbosity_level=1 if settings.DEBUG else 0
        )
        
        # Main ToolCallingAgent
        self.agent = ToolCallingAgent(
            tools=self._build_tools(),
            model=self.llm,
            max_steps=10,
            verbosity_level=1 if settings.DEBUG else 0
        )
        
        logger.info("✅ FinancialAnalystAgent initialized")
    
    def _build_tools(self) -> List:
        """Построение списка tools для агента"""
        
        @tool
        def parse_pdf_document(file_path: str) -> Dict[str, Any]:
            """
            Извлечение текста и таблиц из PDF документа
            
            Args:
                file_path: Путь к PDF файлу
            
            Returns:
                Dict с текстом, таблицами и метаданными
            """
            try:
                result = self.pdf_parser.parse(Path(file_path))
                logger.info(f"PDF parsed: {len(result['text'])} chars")
                return result
            except Exception as e:
                logger.error(f"PDF parsing failed: {e}")
                raise ProcessingError(f"Failed to parse PDF: {e}")
        
        @tool
        def parse_excel_document(file_path: str) -> Dict[str, Any]:
            """
            Извлечение данных из Excel файла
            
            Args:
                file_path: Путь к Excel файлу
            
            Returns:
                Dict с листами, таблицами и формулами
            """
            try:
                result = self.excel_parser.parse(Path(file_path))
                logger.info(f"Excel parsed: {len(result['sheets'])} sheets")
                return result
            except Exception as e:
                logger.error(f"Excel parsing failed: {e}")
                raise ProcessingError(f"Failed to parse Excel: {e}")
        
        @tool
        async def analyze_chart_image(image_path: str, context: str = "") -> Dict[str, Any]:
            """
            Анализ графика/диаграммы через Vision API
            
            Args:
                image_path: Путь к изображению графика
                context: Дополнительный контекст для анализа
            
            Returns:
                Dict с типом графика, значениями и трендами
            """
            try:
                chart_analysis = await self.vision_analyzer.analyze_chart(
                    Path(image_path),
                    context=context
                )
                logger.info(f"Chart analyzed: {chart_analysis.chart_type}")
                return chart_analysis.model_dump()
                
            except VisionAPIError as e:
                logger.warning(f"Vision API error, using fallback: {e}")
                # Graceful degradation уже в VisionAnalyzer
                fallback = await self.vision_analyzer.analyze_chart(
                    Path(image_path),
                    context=context
                )
                return fallback.model_dump()
        
        @tool
        def search_similar_reports(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
            """
            Поиск похожих отчетов в архиве через FAISS
            
            Args:
                query: Текстовый запрос для поиска
                top_k: Количество результатов
            
            Returns:
                List похожих документов с метаданными
            """
            try:
                results = self.faiss_engine.search(query, top_k=top_k)
                logger.info(f"FAISS search: {len(results)} results for '{query}'")
                return results
            except Exception as e:
                logger.error(f"FAISS search failed: {e}")
                return []  # Graceful degradation
        
        @tool
        def calculate_financial_metric(
            metric_name: str,
            values: Dict[str, float]
        ) -> float:
            """
            Расчет финансового коэффициента
            
            Args:
                metric_name: Название метрики (current_ratio, roe, etc.)
                values: Dict с необходимыми значениями
            
            Returns:
                Рассчитанное значение метрики
            """
            try:
                result = self.calculator.calculate(metric_name, values)
                logger.info(f"Calculated {metric_name}: {result}")
                return result
            except Exception as e:
                logger.error(f"Calculation failed for {metric_name}: {e}")
                raise ProcessingError(f"Calculation error: {e}")
        
        @tool
        def extract_kpi_with_sql(
            table_name: str,
            kpi_description: str
        ) -> str:
            """
            Генерация SQL запроса для извлечения KPI
            (Использует CodeAgent для генерации)
            
            Args:
                table_name: Название таблицы
                kpi_description: Описание нужных KPI
            
            Returns:
                SQL запрос для извлечения данных
            """
            try:
                prompt = f"""
                Сгенерируй SQL запрос для извлечения следующих KPI:
                {kpi_description}
                
                Из таблицы: {table_name}
                
                Требования:
                - Используй стандартный SQL (PostgreSQL синтаксис)
                - Добавь комментарии
                - Обработай NULL значения
                - Верни только SQL запрос, без объяснений
                """
                
                # Вызов CodeAgent
                sql_query = self.code_agent.run(prompt)
                
                # Санитизация для защиты от injection
                from ..utils.validators import InputValidator
                safe_sql = InputValidator.sanitize_sql_input(sql_query)
                
                logger.info(f"Generated SQL for {kpi_description}")
                return safe_sql
                
            except Exception as e:
                logger.error(f"SQL generation failed: {e}")
                raise ProcessingError(f"SQL generation error: {e}")
        
        return [
            parse_pdf_document,
            parse_excel_document,
            analyze_chart_image,
            search_similar_reports,
            calculate_financial_metric,
            extract_kpi_with_sql
        ]
    
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    async def analyze_document(
        self,
        file_path: Path,
        report_type: ReportType,
        company_name: Optional[str] = None
    ) -> AnalysisResult:
        """
        Главная функция анализа финансового документа
        
        Args:
            file_path: Путь к файлу отчета
            report_type: Тип отчета
            company_name: Название компании
        
        Returns:
            AnalysisResult с извлеченными KPI
        
        Raises:
            ProcessingError: При ошибках обработки
        """
        logger.info(
            f"Starting analysis",
            extra={
                "file": file_path.name,
                "type": report_type,
                "company": company_name
            }
        )
        
        start_time = datetime.now()
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        
        try:
            # 1. Парсинг документа
            parsed_data = await self._parse_document(file_path)
            
            # 2. Семантический поиск похожих отчетов
            similar_reports = await self._find_similar_reports(
                parsed_data['text'],
                company_name
            )
            
            # 3. Анализ графиков (если есть)
            charts_analysis = await self._analyze_charts(
                parsed_data.get('images', [])
            )
            
            # 4. Извлечение KPI через агента
            kpi_data = await self._extract_kpi(
                parsed_data,
                report_type,
                similar_reports
            )
            
            # 5. Построение структурированного результата
            result = self._build_result(
                report_id=report_id,
                report_type=report_type,
                company_name=company_name,
                parsed_data=parsed_data,
                kpi_data=kpi_data,
                charts_analysis=charts_analysis,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            logger.info(
                f"✅ Analysis completed",
                extra={
                    "report_id": report_id,
                    "duration": result.processing_time
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Analysis failed for {file_path.name}",
                exc_info=True
            )
            raise ProcessingError(f"Document analysis failed: {e}")
    
    async def _parse_document(self, file_path: Path) -> Dict[str, Any]:
        """Парсинг PDF или Excel"""
        if file_path.suffix.lower() == '.pdf':
            return self.pdf_parser.parse(file_path)
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            return self.excel_parser.parse(file_path)
        else:
            raise ProcessingError(f"Unsupported file type: {file_path.suffix}")
    
    async def _find_similar_reports(
        self,
        text: str,
        company_name: Optional[str]
    ) -> List[Dict]:
        """Поиск похожих отчетов в FAISS"""
        try:
            query = f"{company_name} {text[:500]}" if company_name else text[:500]
            return self.faiss_engine.search(query, top_k=3)
        except Exception as e:
            logger.warning(f"FAISS search failed: {e}")
            return []  # Graceful degradation
    
    async def _analyze_charts(self, images: List[Path]) -> List[ChartAnalysis]:
        """Анализ всех графиков в документе"""
        charts = []
        
        for img_path in images:
            try:
                chart = await self.vision_analyzer.analyze_chart(img_path)
                charts.append(chart)
            except Exception as e:
                logger.warning(f"Chart analysis failed for {img_path}: {e}")
                # Продолжаем с другими графиками
        
        return charts
    
    async def _extract_kpi(
        self,
        parsed_data: Dict[str, Any],
        report_type: ReportType,
        similar_reports: List[Dict]
    ) -> Dict[str, Any]:
        """
        Извлечение KPI через ToolCallingAgent
        
        Агент использует tools для:
        - Поиска нужных метрик в тексте
        - SQL генерации для таблиц
        - Расчета коэффициентов
        - Проверки через similar reports
        """
        
        # Построение промпта для агента
        prompt = self._build_extraction_prompt(
            parsed_data,
            report_type,
            similar_reports
        )
        
        # Запуск агента
        try:
            response = self.agent.run(prompt)
            
            # Парсинг ответа агента в structured format
            kpi_data = self._parse_agent_response(response, report_type)
            
            return kpi_data
            
        except Exception as e:
            logger.error(f"KPI extraction failed: {e}")
            raise ProcessingError(f"KPI extraction error: {e}")
    
    def _build_extraction_prompt(
        self,
        parsed_data: Dict,
        report_type: ReportType,
        similar_reports: List[Dict]
    ) -> str:
        """Построение промпта для агента"""
        
        base_prompt = f"""
Ты - эксперт финансовый аналитик. Твоя задача - извлечь ключевые показатели (KPI) 
из финансового отчета.

**Тип отчета:** {report_type.value}

**Текст документа (первые 3000 символов):**
{parsed_data['text'][:3000]}

**Доступные таблицы:**
{parsed_data.get('tables', [])}

**Похожие отчеты из архива:**
{similar_reports[:2] if similar_reports else 'Нет'}

**Задача:**
Извлеки следующие KPI и верни в JSON формате:

"""
        
        if report_type == ReportType.BALANCE_SHEET:
            base_prompt += """
{
  "total_assets": {"value": число, "unit": "RUB", "period": "YYYY-MM-DD"},
  "total_liabilities": {...},
  "equity": {...},
  "current_assets": {...},
  "current_liabilities": {...}
}

**Инструкции:**
1. Используй инструмент `parse_pdf_document` если нужно
2. Используй `search_similar_reports` для проверки
3. Используй `calculate_financial_metric` для коэффициентов
4. Если данных нет - укажи null
5. Добавь confidence score для каждой метрики (0.0-1.0)
"""
        
        elif report_type == ReportType.INCOME_STATEMENT:
            base_prompt += """
{
  "revenue": {"value": число, "unit": "RUB", "period": "YYYY-MM-DD"},
  "gross_profit": {...},
  "operating_income": {...},
  "net_income": {...}
}

**Инструкции:**
1. Найди строки "Выручка", "Валовая прибыль", "Операционная прибыль", "Чистая прибыль"
2. Используй `calculate_financial_metric` для рентабельности
3. Проверь через `search_similar_reports`
"""
        
        base_prompt += "\n\n**Важно:** Верни только JSON, без дополнительных пояснений."
        
        return base_prompt
    
    def _parse_agent_response(
        self,
        response: str,
        report_type: ReportType
    ) -> Dict[str, Any]:
        """Парсинг ответа агента в structured format"""
        import json
        import re
        
        try:
            # Извлечение JSON из ответа
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Валидация через Pydantic
                if report_type == ReportType.BALANCE_SHEET:
                    # Преобразование в BalanceSheetKPI
                    validated = self._validate_balance_sheet(data)
                elif report_type == ReportType.INCOME_STATEMENT:
                    validated = self._validate_income_statement(data)
                else:
                    validated = data
                
                return validated
            else:
                raise ValueError("No JSON found in agent response")
                
        except Exception as e:
            logger.error(f"Failed to parse agent response: {e}")
            raise ProcessingError(f"Response parsing error: {e}")
    
    def _validate_balance_sheet(self, data: Dict) -> Dict:
        """Валидация данных баланса через Pydantic"""
        try:
            # Преобразование в Pydantic модели
            metrics = {}
            for key, value in data.items():
                if value and isinstance(value, dict):
                    metrics[key] = FinancialMetric(**value)
            
            return metrics
        except Exception as e:
            logger.warning(f"Validation failed: {e}, using raw data")
            return data
    
    def _validate_income_statement(self, data: Dict) -> Dict:
        """Валидация данных о прибылях"""
        return self._validate_balance_sheet(data)  # Same structure
    
    def _build_result(
        self,
        report_id: str,
        report_type: ReportType,
        company_name: Optional[str],
        parsed_data: Dict,
        kpi_data: Dict,
        charts_analysis: List[ChartAnalysis],
        processing_time: float
    ) -> AnalysisResult:
        """Построение финального результата"""
        
        # Извлечение даты отчета из текста (простая эвристика)
        report_date = self._extract_report_date(parsed_data['text'])
        
        # Построение KPI объектов
        balance_sheet = None
        income_statement = None
        
        if report_type == ReportType.BALANCE_SHEET and kpi_data:
            balance_sheet = BalanceSheetKPI(
                total_assets=kpi_data.get('total_assets'),
                total_liabilities=kpi_data.get('total_liabilities'),
                equity=kpi_data.get('equity'),
                current_assets=kpi_data.get('current_assets'),
                current_liabilities=kpi_data.get('current_liabilities')
            )
        
        elif report_type == ReportType.INCOME_STATEMENT and kpi_data:
            income_statement = IncomeStatementKPI(
                revenue=kpi_data.get('revenue'),
                gross_profit=kpi_data.get('gross_profit'),
                operating_income=kpi_data.get('operating_income'),
                net_income=kpi_data.get('net_income')
            )
        
        return AnalysisResult(
            report_id=report_id,
            report_type=report_type,
            company_name=company_name,
            report_date=report_date or datetime.now().date(),
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            charts=charts_analysis,
            raw_text=parsed_data['text'][:5000],  # Первые 5000 символов
            metadata={
                'file_size': parsed_data.get('file_size'),
                'num_pages': parsed_data.get('num_pages'),
                'num_tables': len(parsed_data.get('tables', [])),
                'num_charts': len(charts_analysis)
            },
            processing_time=processing_time
        )
    
    def _extract_report_date(self, text: str) -> Optional[datetime.date]:
        """Извлечение даты отчета из текста"""
        import re
        from datetime import datetime
        
        # Паттерны дат
        patterns = [
            r'(\d{2}\.\d{2}\.\d{4})',  # DD.MM.YYYY
            r'(\d{4}-\d{2}-\d{2})',     # YYYY-MM-DD
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:1000])
            if match:
                try:
                    date_str = match.group(1)
                    if '.' in date_str:
                        return datetime.strptime(date_str, '%d.%m.%Y').date()
                    else:
                        return datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    continue
        
        return None
