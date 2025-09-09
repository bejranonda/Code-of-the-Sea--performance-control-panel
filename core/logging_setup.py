import logging
import os
from datetime import datetime
from typing import Optional


class UnifiedLogger:
    """Centralized logging system for all components"""
    
    def __init__(self, name: str, log_file: str = None, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        self.detailed_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.simple_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(self.simple_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            self.setup_file_handler(log_file)
    
    def setup_file_handler(self, log_file: str):
        """Setup file logging handler"""
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(self.detailed_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not setup file logging to {log_file}: {e}")
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception"""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        if exception:
            self.logger.critical(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.critical(message, extra=kwargs)
    
    def log_startup(self, component: str, version: str = "1.0"):
        """Log component startup"""
        self.info(f"{component} v{version} starting up")
        self.info(f"Python version: {os.sys.version}")
        self.info(f"Working directory: {os.getcwd()}")
    
    def log_shutdown(self, component: str):
        """Log component shutdown"""
        self.info(f"{component} shutting down gracefully")
    
    def log_performance(self, operation: str, duration: float, **metrics):
        """Log performance metrics"""
        metric_str = " ".join([f"{k}={v}" for k, v in metrics.items()])
        self.info(f"PERF: {operation} completed in {duration:.3f}s {metric_str}")
    
    def log_user_action(self, user: str, action: str, resource: str = None, **context):
        """Log user actions for audit trail"""
        resource_str = f" on {resource}" if resource else ""
        context_str = " ".join([f"{k}={v}" for k, v in context.items()])
        self.info(f"USER: {user} performed {action}{resource_str} {context_str}")


def setup_application_logging(app_name: str, log_level: str = "INFO") -> UnifiedLogger:
    """Setup application-wide logging"""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    log_level_int = level_map.get(log_level.upper(), logging.INFO)
    log_file = f"logs/{app_name}.log"
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    logger = UnifiedLogger(app_name, log_file, log_level_int)
    logger.log_startup(app_name)
    
    return logger


def create_service_logger(service_name: str) -> UnifiedLogger:
    """Create logger for individual services"""
    log_file = f"logs/{service_name.lower().replace(' ', '_')}.log"
    return UnifiedLogger(service_name, log_file)


class LoggingMixin:
    """Mixin class to add logging capabilities to any class"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None
    
    @property
    def logger(self) -> UnifiedLogger:
        """Get or create logger for this instance"""
        if not self._logger:
            class_name = self.__class__.__name__
            log_file = f"logs/{class_name.lower()}.log"
            self._logger = UnifiedLogger(class_name, log_file)
        return self._logger
    
    def log_method_call(self, method_name: str, **kwargs):
        """Log method calls for debugging"""
        kwargs_str = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.debug(f"Called {method_name} {kwargs_str}")
    
    def log_state_change(self, from_state: str, to_state: str, reason: str = None):
        """Log state changes"""
        reason_str = f" ({reason})" if reason else ""
        self.logger.info(f"State change: {from_state} -> {to_state}{reason_str}")


def log_function_calls(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = UnifiedLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"{func.__name__} completed successfully in {duration:.3f}s")
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {duration:.3f}s", e)
            raise
    
    return wrapper