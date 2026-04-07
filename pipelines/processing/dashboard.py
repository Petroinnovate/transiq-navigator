"""
Dashboard Generator - Generates DMAIC Six Sigma dashboards using LLM
"""
import json
import re
import time
import uuid
from typing import List, Dict, Any, Optional
from services.llm.factory import LLMFactory
from core.config.settings import settings
from core.logging.logger import get_logger
from pipelines.prompts import load_prompt, log_prompt_execution

logger = get_logger(__name__)


class DashboardGenerator:
    """
    Generates comprehensive DMAIC Six Sigma dashboards from document content
    
    Features:
    - Dynamic prompt loading with versioning
    - A/B testing support for prompt optimization
    - Performance tracking with execution metrics
    """
    
    def __init__(
        self,
        provider_name: Optional[str] = None,
        prompt_version: str = "latest",
        use_ab_test: bool = False
    ):
        """
        Initialize dashboard generator
        
        Args:
            provider_name: LLM provider name (defaults to configured provider)
            prompt_version: Prompt version to use ("latest", "stable", or specific like "1.0.0")
            use_ab_test: Enable A/B testing if configured
        """
        self.llm = LLMFactory.get_provider(provider_name)
        self.prompt_version = prompt_version
        self.use_ab_test = use_ab_test
        logger.info(
            f"Initialized DashboardGenerator with provider: {self.llm.get_model_info()['provider']}, "
            f"prompt_version: {prompt_version}, ab_test: {use_ab_test}"
        )
    
    def generate_dashboard(
        self,
        text_chunks: List[str],
        file_name: str = "document",
        doc_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate DMAIC Six Sigma dashboard from document chunks
        
        Args:
            text_chunks: List of text chunks from document
            file_name: Name of the file being processed
            doc_id: Document ID for tracking (optional)
            user_id: User ID for tracking (optional)
            
        Returns:
            Dashboard data dictionary
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        success = False
        kpi_count = 0
        chart_count = 0
        error_message = None
        
        try:
            # Join all chunks - use full document for Grok/modern LLMs with larger context windows
            # Previously limited to 28K for Gemini free-tier, but Grok supports 200K+ context
            full_content = "\n\n".join(text_chunks)
            # Use up to 200K characters for better coverage of large documents
            combined_content = full_content[:200_000]

            # Load prompt dynamically using prompt versioning system
            logger.info(f"Loading prompt 'dashboard' version '{self.prompt_version}' (A/B: {self.use_ab_test})")
            prompt = load_prompt(
                prompt_name="dashboard",
                version=self.prompt_version,
                use_ab_test=self.use_ab_test,
                content=combined_content,
                num_chunks=len(text_chunks)
            )
            
            # Get actual prompt version used (may differ if A/B testing)
            # For logging, we'll extract version from prompt loader later
            
            # Generate dashboard using LLM
            logger.info("Generating dashboard using LLM...")
            response = self.llm.generate_json(prompt)
            
            # Parse and validate response
            dashboard_data = self._parse_dashboard_response(response, file_name)
            
            # Extract metrics for logging
            if "dashboard" in dashboard_data:
                kpi_count = len(dashboard_data["dashboard"].get("kpis", []))
                chart_count = len(dashboard_data["dashboard"].get("charts", []))
            
            success = True
            logger.info(f"Dashboard generated successfully (KPIs: {kpi_count}, Charts: {chart_count})")
            
            return dashboard_data
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Dashboard generation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return fallback dashboard
            return self._get_fallback_dashboard(file_name, error_message)
        
        finally:
            # Log prompt execution performance
            latency_ms = (time.time() - start_time) * 1000
            
            try:
                log_prompt_execution(
                    execution_id=execution_id,
                    prompt_name="dashboard",
                    prompt_version=self.prompt_version,
                    latency_ms=latency_ms,
                    success=success,
                    doc_id=doc_id,
                    user_id=user_id,
                    kpi_count=kpi_count,
                    chart_count=chart_count,
                    error_message=error_message,
                    metadata={
                        "file_name": file_name,
                        "num_chunks": len(text_chunks),
                        "content_length": len(combined_content),
                        "total_content_length": len(full_content),
                        "ab_test_enabled": self.use_ab_test
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log prompt execution: {log_error}")
    
    def _parse_dashboard_response(self, response: Any, file_name: str) -> Dict[str, Any]:
        """Parse LLM response into dashboard format"""
        try:
            # Handle different response formats
            if isinstance(response, dict):
                # Check if response already has dashboard wrapper
                if "dashboard" in response:
                    dashboard_data = response["dashboard"]
                else:
                    # Wrap response in dashboard structure
                    dashboard_data = response
                
                # Ensure required fields exist
                if "title" not in dashboard_data:
                    dashboard_data["title"] = f"Analytics Dashboard - {file_name}"
                if "description" not in dashboard_data:
                    dashboard_data["description"] = f"Comprehensive analysis of {file_name}"
                
                # Ensure arrays exist
                if "kpis" not in dashboard_data:
                    dashboard_data["kpis"] = []
                if "charts" not in dashboard_data:
                    dashboard_data["charts"] = []
                if "tables" not in dashboard_data:
                    dashboard_data["tables"] = []
                if "optimizationSuggestions" not in dashboard_data:
                    dashboard_data["optimizationSuggestions"] = []
                # Run deterministic Six Sigma engine on KPIs
                try:
                    from pipelines.evaluation.six_sigma import run_six_sigma
                    kpis_for_sigma = dashboard_data.get("kpis", [])
                    if kpis_for_sigma:
                        dashboard_data["sixSigma"] = run_six_sigma(kpis_for_sigma)
                        logger.info("Six Sigma engine: injected deterministic analysis (%d KPIs)", len(kpis_for_sigma))
                    else:
                        logger.info("Six Sigma engine: skipped — no KPIs available")
                except Exception as ss_err:
                    logger.warning("Six Sigma engine failed, using fallback: %s", ss_err)

                if "sixSigma" not in dashboard_data:
                    dashboard_data["sixSigma"] = {
                        "dmaic": {
                            "define": "Analysis in progress",
                            "measure": "Metrics being calculated",
                            "analyze": "Patterns being identified",
                            "improve": "Recommendations being generated",
                            "control": "Monitoring strategies being developed"
                        },
                        "sigmaLevel": "N/A",
                        "defectRate": "N/A",
                        "processCapability": "Unknown",
                        "rootCauses": []
                    }
                if "insights" not in dashboard_data:
                    dashboard_data["insights"] = {
                        "summary": "Analysis completed",
                        "trends": [],
                        "alerts": [],
                        "recommendations": []
                    }
                
                return {"dashboard": dashboard_data}
            
            elif isinstance(response, str):
                # Try to parse JSON string
                json_match = re.search(r"(\{.*\})", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    parsed = json.loads(json_str)
                    return self._parse_dashboard_response(parsed, file_name)
            
            # Fallback
            return self._get_fallback_dashboard(file_name, "Invalid response format")
            
        except Exception as e:
            logger.error(f"Error parsing dashboard response: {e}")
            return self._get_fallback_dashboard(file_name, str(e))
    
    def _get_fallback_dashboard(self, file_name: str, error: str = "") -> Dict[str, Any]:
        """Return fallback dashboard structure"""
        # Check if it's a quota/rate limit error
        is_quota_error = '429' in str(error) or 'quota' in str(error).lower() or 'RESOURCE_EXHAUSTED' in str(error)
        
        if is_quota_error:
            title = f"Queued: {file_name}"
            description = f"API quota exceeded. Document '{file_name}' uploaded successfully and queued for analysis. Dashboard will be generated when quota resets."
            define_msg = "Document uploaded and stored. Analysis queued pending API quota reset."
        else:
            title = f"Analytics Dashboard - {file_name}"
            description = f"Analysis of {file_name}" + (f" - {error[:150]}" if error else "")
            define_msg = f"Analysis in progress. {error if error else 'Processing document...'}"
        
        return {
            "dashboard": {
                "title": title,
                "description": description,
                "sixSigma": {
                    "dmaic": {
                        "define": define_msg,
                        "measure": "Metrics being calculated",
                        "analyze": "Patterns being identified",
                        "improve": "Recommendations being generated",
                        "control": "Monitoring strategies being developed"
                    },
                    "sigmaLevel": "N/A",
                    "defectRate": "N/A",
                    "processCapability": "Unknown",
                    "rootCauses": []
                },
                "kpis": [],
                "charts": [],
                "tables": [],
                "optimizationSuggestions": [],
                "insights": {
                    "summary": "Dashboard generation in progress",
                    "trends": [],
                    "alerts": [],
                    "recommendations": []
                }
            }
        }

