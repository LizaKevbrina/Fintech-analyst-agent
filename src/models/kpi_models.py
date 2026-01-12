from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal
from enum import Enum


class ReportType(str, Enum):
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    ANNUAL_REPORT = "annual_report"


class FinancialMetric(BaseModel):
    """Базовая финансовая метрика"""
    name: str = Field(..., description="Название метрики")
    value: Decimal = Field(..., description="Значение")
    unit: str = Field(default="RUB", description="Единица измерения")
    period: date = Field(..., description="Отчетный период")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Метрика не может быть отрицательной")
        return v


class BalanceSheetKPI(BaseModel):
    """KPI из баланса"""
    total_assets: FinancialMetric
    total_liabilities: FinancialMetric
    equity: FinancialMetric
    current_assets: Optional[FinancialMetric] = None
    current_liabilities: Optional[FinancialMetric] = None
    
    @property
    def current_ratio(self) -> Optional[float]:
        """Коэффициент текущей ликвидности"""
        if self.current_assets and self.current_liabilities:
            if self.current_liabilities.value > 0:
                return float(self.current_assets.value / self.current_liabilities.value)
        return None


class IncomeStatementKPI(BaseModel):
    """KPI из отчета о прибылях"""
    revenue: FinancialMetric
    gross_profit: FinancialMetric
    operating_income: FinancialMetric
    net_income: FinancialMetric
    
    @property
    def profit_margin(self) -> float:
        """Рентабельность"""
        if self.revenue.value > 0:
            return float(self.net_income.value / self.revenue.value)
        return 0.0


class ChartAnalysis(BaseModel):
    """Результат анализа графика"""
    chart_type: str = Field(..., description="Тип графика (line, bar, pie)")
    title: Optional[str] = None
    extracted_values: Dict[str, float] = Field(default_factory=dict)
    trends: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class AnalysisResult(BaseModel):
    """Итоговый результат анализа"""
    report_id: str
    report_type: ReportType
    company_name: Optional[str] = None
    report_date: date
    balance_sheet: Optional[BalanceSheetKPI] = None
    income_statement: Optional[IncomeStatementKPI] = None
    charts: List[ChartAnalysis] = Field(default_factory=list)
    raw_text: str
    metadata: Dict = Field(default_factory=dict)
    processing_time: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "report_2024_q1",
                "report_type": "balance_sheet",
                "company_name": "ООО Пример",
                "report_date": "2024-03-31",
                "balance_sheet": {
                    "total_assets": {
                        "name": "Активы",
                        "value": 1000000,
                        "unit": "RUB",
                        "period": "2024-03-31"
                    }
                },
                "processing_time": 5.2
            }
        }
