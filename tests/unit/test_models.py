import pytest
from datetime import date
from decimal import Decimal

from src.models.kpi_models import (
    FinancialMetric,
    BalanceSheetKPI,
    IncomeStatementKPI
)


class TestFinancialMetric:
    """Unit tests для FinancialMetric"""
    
    def test_create_valid_metric(self):
        """Создание валидной метрики"""
        metric = FinancialMetric(
            name="Активы",
            value=Decimal("1000000"),
            unit="RUB",
            period=date(2024, 12, 31)
        )
        
        assert metric.name == "Активы"
        assert metric.value == Decimal("1000000")
        assert metric.confidence == 1.0
    
    def test_negative_value_validation(self):
        """Валидация отрицательных значений"""
        with pytest.raises(ValueError, match="не может быть отрицательной"):
            FinancialMetric(
                name="Активы",
                value=Decimal("-1000"),
                period=date(2024, 12, 31)
            )


class TestBalanceSheetKPI:
    """Unit tests для BalanceSheetKPI"""
    
    def test_current_ratio_calculation(self):
        """Расчет коэффициента текущей ликвидности"""
        kpi = BalanceSheetKPI(
            total_assets=FinancialMetric(
                name="Активы",
                value=Decimal("1000000"),
                period=date(2024, 12, 31)
            ),
            total_liabilities=FinancialMetric(
                name="Пассивы",
                value=Decimal("500000"),
                period=date(2024, 12, 31)
            ),
            equity=FinancialMetric(
                name="Капитал",
                value=Decimal("500000"),
                period=date(2024, 12, 31)
            ),
            current_assets=FinancialMetric(
                name="Текущие активы",
                value=Decimal("600000"),
                period=date(2024, 12, 31)
            ),
            current_liabilities=FinancialMetric(
                name="Текущие пассивы",
                value=Decimal("300000"),
                period=date(2024, 12, 31)
            )
        )
        
        assert kpi.current_ratio == pytest.approx(2.0, rel=0.01)
