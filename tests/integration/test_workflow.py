import pytest
from pathlib import Path

from src.agents.analyst_agent import FinancialAnalystAgent
from src.models.kpi_models import ReportType


@pytest.mark.asyncio
class TestAnalysisWorkflow:
    """Integration tests для полного workflow"""
    
    async def test_analyze_pdf_balance_sheet(
        self,
        analyst_agent: FinancialAnalystAgent,
        sample_pdf_path: Path
    ):
        """Тест полного анализа PDF баланса"""
        result = await analyst_agent.analyze_document(
            file_path=sample_pdf_path,
            report_type=ReportType.BALANCE_SHEET,
            company_name="ООО Тестовая Компания"
        )
        
        # Проверки
        assert result.report_id is not None
        assert result.report_type == ReportType.BALANCE_SHEET
        assert result.company_name == "ООО Тестовая Компания"
        assert result.processing_time > 0
        
        # Проверка KPI
        if result.balance_sheet:
            assert result.balance_sheet.total_assets is not None
            assert result.balance_sheet.equity is not None
    
    async def test_graceful_degradation_vision_api(
        self,
        analyst_agent: FinancialAnalystAgent,
        sample_pdf_path: Path,
        monkeypatch
    ):
        """Тест graceful degradation при недоступности Vision API"""
        
        # Mock Vision API failure
        async def mock_vision_fail(*args, **kwargs):
            from src.tools.vision_analyzer import VisionAPIError
            raise VisionAPIError("API unavailable")
        
        monkeypatch.setattr(
            analyst_agent.vision_analyzer,
            "analyze_chart",
            mock_vision_fail
        )
        
        # Анализ должен пройти с fallback
        result = await analyst_agent.analyze_document(
            file_path=sample_pdf_path,
            report_type=ReportType.BALANCE_SHEET
        )
        
        assert result is not None
        assert result.report_id is not None
