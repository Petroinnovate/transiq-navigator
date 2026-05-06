"""
Prompt Performance Logger - Track prompt execution metrics for optimization
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from core.logging.logger import get_logger
from services.db import get_db_context
from services.db.models import PromptExecution

logger = get_logger(__name__)


class PromptLogger:
    """
    Logger for prompt execution performance tracking
    
    Features:
    - Track latency, token usage, cost
    - Track output metrics (KPI count, chart count)
    - Store in database for analytics
    - Optional JSON file backup
    """
    
    def __init__(self, log_to_db: bool = True, log_to_file: bool = False, log_dir: Optional[Path] = None):
        """
        Initialize prompt logger
        
        Args:
            log_to_db: Store logs in database
            log_to_file: Also store logs in JSON files (backup)
            log_dir: Directory for JSON log files (defaults to logs/prompts/)
        """
        self.log_to_db = log_to_db
        self.log_to_file = log_to_file
        
        if log_to_file:
            if log_dir is None:
                # Auto-detect log directory
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                self.log_dir = project_root / "logs" / "prompts"
            else:
                self.log_dir = Path(log_dir)
            
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Prompt logger initialized (file backup: {self.log_dir})")
        else:
            self.log_dir = None
    
    def log_execution(
        self,
        execution_id: str,
        prompt_name: str,
        prompt_version: str,
        latency_ms: float,
        success: bool = True,
        doc_id: Optional[str] = None,
        user_id: Optional[str] = None,
        kpi_count: Optional[int] = None,
        chart_count: Optional[int] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a prompt execution
        
        Args:
            execution_id: Unique execution ID (e.g., task_id or UUID)
            prompt_name: Name of the prompt used
            prompt_version: Version of the prompt used
            latency_ms: Execution time in milliseconds
            success: Whether execution succeeded
            doc_id: Document ID being processed
            user_id: User ID who initiated the request
            kpi_count: Number of KPIs extracted
            chart_count: Number of charts generated
            tokens_used: Number of LLM tokens consumed
            cost: Estimated cost in USD
            error_message: Error message if failed
            metadata: Additional metrics (e.g., quality scores)
        """
        log_entry = {
            "id": execution_id,
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
            "doc_id": doc_id,
            "user_id": user_id,
            "latency_ms": int(latency_ms),
            "tokens_used": tokens_used,
            "cost": int(cost * 100) if cost else None,  # Store in cents
            "kpi_count": kpi_count,
            "chart_count": chart_count,
            "success": 1 if success else 0,
            "error_message": error_message,
            "exec_metadata": metadata,  # Renamed column
            "created_at": datetime.utcnow()
        }
        
        # Log to database
        if self.log_to_db:
            try:
                self._save_to_db(log_entry)
            except Exception as e:
                logger.error(f"Failed to save prompt execution to database: {e}")
        
        # Log to file (backup)
        if self.log_to_file:
            try:
                self._save_to_file(log_entry)
            except Exception as e:
                logger.error(f"Failed to save prompt execution to file: {e}")
        
        # Log summary
        status = "✅" if success else "❌"
        logger.info(
            f"{status} Prompt '{prompt_name}' v{prompt_version} executed in {latency_ms:.0f}ms "
            f"(KPIs: {kpi_count or 0}, Charts: {chart_count or 0})"
        )
    
    def _save_to_db(self, log_entry: Dict[str, Any]):
        """Save log entry to database"""
        try:
            with get_db_context() as db:
                execution = PromptExecution(**log_entry)
                db.add(execution)
                db.commit()
                logger.debug(f"Saved prompt execution {log_entry['id']} to database")
        except Exception as e:
            logger.error(f"Database save error: {e}")
            raise
    
    def _save_to_file(self, log_entry: Dict[str, Any]):
        """Save log entry to JSON file (daily rotation)"""
        try:
            # Create daily log file
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"prompt_executions_{date_str}.jsonl"
            
            # Append to JSONL file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            logger.debug(f"Saved prompt execution to {log_file}")
        except Exception as e:
            logger.error(f"File save error: {e}")
            raise
    
    def get_performance_stats(
        self,
        prompt_name: str,
        prompt_version: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a prompt
        
        Args:
            prompt_name: Name of the prompt
            prompt_version: Specific version (or None for all versions)
            hours: Time window in hours
            
        Returns:
            Dictionary with performance stats
        """
        try:
            with get_db_context() as db:
                # Calculate time threshold
                time_threshold = datetime.utcnow() - timedelta(hours=hours)
                
                # Build query
                query = db.query(PromptExecution).filter(
                    PromptExecution.prompt_name == prompt_name,
                    PromptExecution.created_at >= time_threshold
                )
                
                if prompt_version:
                    query = query.filter(PromptExecution.prompt_version == prompt_version)
                
                executions = query.all()
                
                if not executions:
                    return {"error": "No executions found", "count": 0}
                
                # Calculate statistics
                latencies = [e.latency_ms for e in executions]
                kpi_counts = [e.kpi_count for e in executions if e.kpi_count is not None]
                success_count = sum(1 for e in executions if e.success == 1)
                
                stats = {
                    "prompt_name": prompt_name,
                    "prompt_version": prompt_version or "all",
                    "time_window_hours": hours,
                    "total_executions": len(executions),
                    "success_rate": success_count / len(executions),
                    "latency": {
                        "avg_ms": sum(latencies) / len(latencies),
                        "min_ms": min(latencies),
                        "max_ms": max(latencies),
                        "p50_ms": sorted(latencies)[len(latencies) // 2],
                        "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)]
                    },
                    "kpis": {
                        "avg_count": sum(kpi_counts) / len(kpi_counts) if kpi_counts else 0,
                        "min_count": min(kpi_counts) if kpi_counts else 0,
                        "max_count": max(kpi_counts) if kpi_counts else 0
                    }
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {"error": str(e)}


# Global singleton instance
_global_logger: Optional[PromptLogger] = None


def get_prompt_logger() -> PromptLogger:
    """Get or create global PromptLogger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = PromptLogger(log_to_db=True, log_to_file=False)
    return _global_logger


def log_prompt_execution(
    execution_id: str,
    prompt_name: str,
    prompt_version: str,
    latency_ms: float,
    **kwargs
):
    """
    Convenience function to log prompt execution
    
    Args:
        execution_id: Unique execution ID
        prompt_name: Name of the prompt
        prompt_version: Version of the prompt
        latency_ms: Execution time in milliseconds
        **kwargs: Additional metrics (kpi_count, chart_count, etc.)
    """
    logger_instance = get_prompt_logger()
    logger_instance.log_execution(
        execution_id=execution_id,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        latency_ms=latency_ms,
        **kwargs
    )
