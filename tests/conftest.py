import pytest
import asyncio
from pathlib import Path
from typing import Generator
import tempfile
import shutil

from src.agents.analyst_agent import FinancialAnalystAgent
from src.core.config import settings
from src.utils.logging_config import setup_logging


@pytest.fixture(scope="session")
def event_loop():
    """Event loop для async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Setup логирования для тестов"""
    setup_logging(log_level="DEBUG")


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Временная директория для тестов"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_pdf_path(temp_dir: Path) -> Path:
    """Путь к тестовому PDF"""
    # Создание простого тестового PDF
    from reportlab.pdfgen import canvas
    
    pdf_path = temp_dir / "test_report.pdf"
    c = canvas.Canvas(str(pdf_path))
    
    # Добавление текста
    c.drawString(100, 750, "Финансовый отчет за 2024 год")
    c.drawString(100, 700, "ООО Тестовая Компания")
    c.drawString(100, 650, "Активы: 1 000 000 руб")
    c.drawString(100, 600, "Пассивы: 500 000 руб")
    c.drawString(100, 550, "Собственный капитал: 500 000 руб")
    
    c.save()
    return pdf_path


@pytest.fixture
def mock_vision_response():
    """Mock ответ от Vision API"""
    return {
        "chart_type": "line",
        "title": "Динамика выручки",
        "extracted_values": {
            "2023": 1000000,
            "2024": 1500000
        },
        "trends": ["Рост на 50%"],
        "confidence": 0.95
    }


@pytest.fixture
async def analyst_agent() -> FinancialAnalystAgent:
    """Инстанс FinancialAnalystAgent для тестов"""
    return FinancialAnalystAgent()
