class FinTechAgentException(Exception):
    """Base exception для всего приложения"""
    pass


class ValidationError(FinTechAgentException):
    """Ошибка валидации входных данных"""
    pass


class ProcessingError(FinTechAgentException):
    """Ошибка обработки документа"""
    pass


class VisionAPIError(FinTechAgentException):
    """Ошибка Vision API"""
    pass


class FAISSError(FinTechAgentException):
    """Ошибка FAISS search"""
    pass
