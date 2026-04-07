"""
Custom exception classes
"""
from typing import Optional, Dict, Any


class TransIQError(Exception):
    """Base exception for TransIQ application"""
    def __init__(self, message: str, code: str = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code or "TRANSIQ_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class LLMProviderError(TransIQError):
    """Error related to LLM provider operations"""
    def __init__(self, message: str, provider: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="LLM_PROVIDER_ERROR", details=details)
        self.provider = provider


class ProcessingError(TransIQError):
    """Error during document processing"""
    def __init__(self, message: str, document_id: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="PROCESSING_ERROR", details=details)
        self.document_id = document_id


class StorageError(TransIQError):
    """Error related to storage operations"""
    def __init__(self, message: str, storage_type: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="STORAGE_ERROR", details=details)
        self.storage_type = storage_type


class SearchError(TransIQError):
    """Error during search operations"""
    def __init__(self, message: str, query: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="SEARCH_ERROR", details=details)
        self.query = query


class ValidationError(TransIQError):
    """Error in input validation"""
    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details)
        self.field = field

