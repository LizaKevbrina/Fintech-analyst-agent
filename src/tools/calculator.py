from typing import Dict
import math

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class FinancialCalculator:
    """
    Калькулятор финансовых коэффициентов
    
    Поддерживаемые метрики:
    - Current ratio (коэффициент текущей ликвидности)
    - Quick ratio (быстрая ликвидность)
    - ROE (рентабельность собственного капитала)
    - ROA (рентабельность активов)
    - Debt-to-equity ratio
    - Profit margin
    """
    
    SUPPORTED_METRICS = {
        'current_ratio',
        'quick_ratio',
        'roe',
        'roa',
        'debt_to_equity',
        'profit_margin',
        'gross_margin',
        'operating_margin'
    }
    
    def calculate(self, metric_name: str, values: Dict[str, float]) -> float:
        """
        Расчет финансовой метрики
        
        Args:
            metric_name: Название метрики
            values: Dict с необходимыми значениями
        
        Returns:
            Рассчитанное значение
        
        Raises:
            ValueError: Если метрика не поддерживается или недостаточно данных
        """
        metric_name = metric_name.lower()
        
        if metric_name not in self.SUPPORTED_METRICS:
            raise ValueError(
                f"Unsupported metric: {metric_name}. "
                f"Supported: {self.SUPPORTED_METRICS}"
            )
        
        try:
            if metric_name == 'current_ratio':
                return self._current_ratio(values)
            elif metric_name == 'quick_ratio':
                return self._quick_ratio(values)
            elif metric_name == 'roe':
                return self._roe(values)
            elif metric_name == 'roa':
                return self._roa(values)
            elif metric_name == 'debt_to_equity':
                return self._debt_to_equity(values)
            elif metric_name == 'profit_margin':
                return self._profit_margin(values)
            elif metric_name == 'gross_margin':
                return self._gross_margin(values)
            elif metric_name == 'operating_margin':
                return self._operating_margin(values)
        
        except KeyError as e:
            raise ValueError(f"Missing required value: {e}")
        except ZeroDivisionError:
            raise ValueError("Division by zero in calculation")
    
    def _current_ratio(self, values: Dict) -> float:
        """Коэффициент текущей ликвидности"""
        return values['current_assets'] / values['current_liabilities']
    
    def _quick_ratio(self, values: Dict) -> float:
        """Быстрая ликвидность"""
        return (
            (values['current_assets'] - values['inventory']) /
            values['current_liabilities']
        )
    
    def _roe(self, values: Dict) -> float:
        """Рентабельность собственного капитала"""
        return values['net_income'] / values['equity'] * 100
    
    def _roa(self, values: Dict) -> float:
        """Рентабельность активов"""
        return values['net_income'] / values['total_assets'] * 100
    
    def _debt_to_equity(self, values: Dict) -> float:
        """Соотношение долга к капиталу"""
        return values['total_debt'] / values['equity']
    
    def _profit_margin(self, values: Dict) -> float:
        """Рентабельность по чистой прибыли"""
        return values['net_income'] / values['revenue'] * 100
    
    def _gross_margin(self, values: Dict) -> float:
        """Валовая рентабельность"""
        return values['gross_profit'] / values['revenue'] * 100
    
    def _operating_margin(self, values: Dict) -> float:
        """Операционная рентабельность"""
        return values['operating_income'] / values['revenue'] * 100
