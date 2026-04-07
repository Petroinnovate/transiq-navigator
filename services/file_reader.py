"""
File reading utilities for different file types
"""
import os
import pandas as pd
from typing import List, Optional
from core.logging.logger import get_logger

logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. PDF processing will be limited.")


def read_file_content(file_path: str) -> str:
    """
    Read file content based on file type
    
    Args:
        file_path: Path to file
        
    Returns:
        Text content of the file
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.csv':
        return read_csv(file_path)
    elif file_ext in ['.xlsx', '.xls']:
        return read_excel(file_path)
    elif file_ext == '.pdf':
        return read_pdf(file_path)
    else:
        # Try reading as text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'rb') as f:
                content = f.read()
                try:
                    return content.decode('utf-8')
                except:
                    return content.decode('latin-1', errors='ignore')


def read_csv(file_path: str) -> str:
    """Read CSV file and convert to text"""
    try:
        df = pd.read_csv(file_path)
        filename = os.path.basename(file_path)
        
        text = f"CSV file '{filename}': {len(df)} rows, {len(df.columns)} columns\n"
        text += f"Columns: {', '.join(df.columns)}\n\n"
        
        # Add column statistics
        text += "Column statistics:\n"
        for col in df.columns:
            text += f"- {col}: "
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    text += f"numeric, range [{df[col].min()}-{df[col].max()}], "
                    text += f"mean: {df[col].mean():.2f}\n"
                else:
                    unique_vals = df[col].nunique()
                    text += f"text/categorical, {unique_vals} unique values\n"
            except Exception:
                text += "unknown type\n"
        
        # Add data table
        text += "\nData:\n"
        text += df.to_string(max_rows=100)  # Limit rows for large files
        
        return text
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        return f"Error reading CSV file: {str(e)}"


def read_excel(file_path: str) -> str:
    """Read Excel file and convert to text"""
    try:
        df_dict = pd.read_excel(file_path, sheet_name=None)
        filename = os.path.basename(file_path)
        text_parts = []
        
        for sheet_name, df in df_dict.items():
            text = f"Sheet '{sheet_name}' from file '{filename}': {len(df)} rows, {len(df.columns)} columns\n"
            text += f"Columns: {', '.join(df.columns)}\n\n"
            
            # Add column statistics
            text += "Column statistics:\n"
            for col in df.columns:
                text += f"- {col}: "
                try:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        text += f"numeric, range [{df[col].min()}-{df[col].max()}], "
                        text += f"mean: {df[col].mean():.2f}\n"
                    else:
                        unique_vals = df[col].nunique()
                        text += f"text/categorical, {unique_vals} unique values\n"
                except Exception:
                    text += "unknown type\n"
            
            # Add data table
            text += "\nData:\n"
            text += df.to_string(max_rows=100)
            text_parts.append(text)
        
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error reading Excel: {e}")
        return f"Error reading Excel file: {str(e)}"


def read_pdf(file_path: str) -> str:
    """
    Read PDF file and extract all text without page limits.
    Returns complete document text for chunking by downstream processors.
    
    Note: This function extracts text but does NOT apply page limits.
    Chunking is handled by dedicated pdf_chunker module.
    """
    if not PDF_AVAILABLE:
        return "PDF processing not available. Install PyMuPDF (pip install pymupdf)"

    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages = []

        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                text = page.get_text("text")
                pages.append(text)
            except Exception as page_error:
                logger.warning(f"Failed to extract page {page_num + 1}: {page_error}")
                pages.append(f"[Error extracting page {page_num + 1}]")

        doc.close()

        content = "\n\n".join(pages)
        logger.info(f"PDF extraction complete: {total_pages} pages, {len(content):,} characters")
        return content
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return f"Error reading PDF file: {str(e)}"


def get_pdf_metadata(file_path: str) -> dict:
    """
    Extract PDF metadata without reading full content.
    Returns page count, file size, and other metadata.
    """
    if not PDF_AVAILABLE:
        return {"error": "PDF processing not available"}
    
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
        
        file_size = os.path.getsize(file_path)
        
        return {
            "total_pages": total_pages,
            "file_size": file_size,
            "file_path": file_path,
            "file_name": os.path.basename(file_path)
        }
    except Exception as e:
        logger.error(f"Error reading PDF metadata: {e}")
        return {"error": str(e)}


def get_file_chunks_for_dashboard(file_path: str) -> List[str]:
    """
    Get text for dashboard LLM generation.
    
    NOTE: This function is DEPRECATED and kept for backwards compatibility.
    New code should use pdf_chunker module which handles intelligent chunking.
    
    For compatibility, returns full content without hard limits.
    Chunking and context limits are handled by downstream processors.
    """
    content = read_file_content(file_path)
    logger.info(f"Dashboard input prepared: {len(content):,} chars (no hard limit applied)")
    return [content]

