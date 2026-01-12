import pytest
from pathlib import Path

from src.utils.validators import InputValidator
from src.core.exceptions import ValidationError


class TestInputValidator:
    """Unit tests для InputValidator"""
    
    def test_validate_file_upload_success(self, sample_pdf_path):
        """Успешная валидация файла"""
        assert InputValidator.validate_file_upload(sample_pdf_path) is True
    
    def test_validate_file_upload_invalid_extension(self, temp_dir):
        """Ошибка при неверном расширении"""
        invalid_file = temp_dir / "test.exe"
        invalid_file.touch()
        
        with pytest.raises(ValidationError, match="Invalid file extension"):
            InputValidator.validate_file_upload(invalid_file)
    
    def test_validate_file_upload_too_large(self, temp_dir):
        """Ошибка при превышении размера"""
        large_file = temp_dir / "large.pdf"
        
        # Создание файла > 10MB
        with open(large_file, 'wb') as f:
            f.write(b'0' * (11 * 1024 * 1024))
        
        with pytest.raises(ValidationError, match="File too large"):
            InputValidator.validate_file_upload(large_file)
    
    def test_sanitize_sql_input_valid(self):
        """Валидный SQL input"""
        text = "SELECT * FROM users WHERE id = 1"
        
        with pytest.raises(ValidationError, match="SQL injection"):
            InputValidator.sanitize_sql_input(text)
    
    def test_sanitize_sql_input_injection(self):
        """Обнаружение SQL injection"""
        malicious = "1' OR '1'='1"
        
        with pytest.raises(ValidationError, match="SQL injection"):
            InputValidator.sanitize_sql_input(malicious)
    
    def test_validate_company_name_success(self):
        """Валидное название компании"""
        name = "ООО Тестовая Компания"
        assert InputValidator.validate_company_name(name) == name
    
    def test_validate_company_name_too_short(self):
        """Слишком короткое название"""
        with pytest.raises(ValidationError, match="too short"):
            InputValidator.validate_company_name("А")
    
    def test_validate_company_name_invalid_chars(self):
        """Невалидные символы"""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_company_name("Test <script>")
