"""
Base chunker interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseChunker(ABC):
    """Abstract base class for text chunkers"""
    
    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[str]:
        """
        Split text into chunks
        
        Args:
            text: Input text to chunk
            **kwargs: Chunking parameters
            
        Returns:
            List of text chunks
        """
        pass
    
    @abstractmethod
    def chunk_with_metadata(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata
        
        Args:
            text: Input text to chunk
            **kwargs: Chunking parameters
            
        Returns:
            List of dictionaries with 'text' and 'metadata' keys
        """
        pass

