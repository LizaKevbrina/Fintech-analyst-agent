import re
from pathlib import Path
from typing import Optional, List
import bleach
from ..core.exceptions import ValidationError
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class InputValidator:
    """Валидация и санитизация входных данных"""
    
    # Разрешенные расширения файлов
    ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.csv'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bUNION\b.*\bSELECT\b)",
    ]
    
    @classmethod
    def validate_file_upload(cls, file_path: Path) -> bool:
        """
        Валидация загружаемого файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если валиден
            
        Raises:
            ValidationError: Если файл невалиден
        """
        # Проверка существования
        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        # Проверка расширения
        if file_path.suffix.lower() not in cls.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Invalid file extension: {file_path.suffix}. "
                f"Allowed: {cls.ALLOWED_EXTENSIONS}"
            )
        
        # Проверка размера
        file_size = file_path.stat().st_size
        if file_size > cls.MAX_FILE_SIZE:
            raise ValidationError(
                f"File too large: {file_size / 1024 / 1024:.2f}MB. "
                f"Max: {cls.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Проверка на исполняемые файлы (по magic bytes)
        if cls._is_executable(file_path):
            raise ValidationError("Executable files are not allowed")
        
        logger.info(f"File validated successfully: {file_path}")
        return True
    
    @staticmethod
    def _is_executable(file_path: Path) -> bool:
        """Проверка на исполняемый файл"""
        with open(file_path, 'rb') as f:
            header = f.read(4)
            # EXE, DLL, etc.
            return header[:2] == b'MZ' or header == b'\x7fELF'
    
    @classmethod
    def sanitize_sql_input(cls, text: str) -> str:
        """
        Защита от SQL injection
        
        Args:
            text: Входной текст
            
        Returns:
            Безопасный текст
        """
        # Проверка на SQL injection паттерны
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {text[:100]}")
                raise ValidationError("Invalid input: SQL injection detected")
        
        # Экранирование спецсимволов
        sanitized = text.replace("'", "''")
        sanitized = sanitized.replace(";", "")
        
        return sanitized
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Очистка от HTML/XSS"""
        return bleach.clean(
            text,
            tags=[],
            strip=True
        )
    
    @classmethod
    def validate_company_name(cls, name: str) -> str:
        """Валидация названия компании"""
        if not name or len(name) < 2:
            raise ValidationError("Company name too short")
        
        if len(name) > 200:
            raise ValidationError("Company name too long")
        
        # Санитизация
        sanitized = cls.sanitize_html(name)
        
        # Проверка на допустимые символы
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z0-9\s\-"\'\.]+$', sanitized):
            raise ValidationError("Company name contains invalid characters")
        
        return sanitized
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> bool:
        """Валидация диапазона дат"""
        from datetime import datetime
        
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            if start > end:
                raise ValidationError("Start date must be before end date")
            
            # Проверка разумности диапазона (не более 10 лет)
            diff = end - start
            if diff.days > 3650:
                raise ValidationError("Date range too large (max 10 years)")
            
            return True
            
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")
