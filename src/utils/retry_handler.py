import asyncio
import functools
import random
from typing import Callable, TypeVar, Any
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,)
):
    """
    Декоратор для retry с exponential backoff
    
    Args:
        max_retries: Максимальное количество попыток
        base_delay: Начальная задержка в секундах
        max_delay: Максимальная задержка
        exponential_base: База для экспоненты
        jitter: Добавлять случайный jitter
        exceptions: Tuple исключений для retry
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        async def api_call():
            return await client.call()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        logger.error(
                            f"All {max_retries} retries failed for {func.__name__}",
                            exc_info=True
                        )
                        raise
                    
                    # Вычисление задержки
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Добавление jitter
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}. "
                        f"Retrying in {delay:.2f}s. Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        logger.error(
                            f"All {max_retries} retries failed for {func.__name__}",
                            exc_info=True
                        )
                        raise
                    
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed. "
                        f"Retrying in {delay:.2f}s. Error: {str(e)}"
                    )
                    
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        # Определение async или sync
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Специализированные retry декораторы
def retry_on_api_error(max_retries: int = 3):
    """Retry для API ошибок (429, 500, 503)"""
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=2.0,
        max_delay=120.0,
        exceptions=(
            ConnectionError,
            TimeoutError,
            # Добавить API-specific исключения
        )
    )


def retry_on_db_error(max_retries: int = 2):
    """Retry для database ошибок"""
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=0.5,
        max_delay=5.0,
        exceptions=(
            # Database specific exceptions
        )
    )
