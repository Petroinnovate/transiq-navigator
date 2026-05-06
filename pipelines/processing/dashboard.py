"""
Dashboard Generator - Generates DMAIC Six Sigma dashboards using LLM

Supports:
- Synchronous generation (original)
- Async generation with semantic chunk ranking (embedding-based)
- **SSE streaming** — yields dashboard sections progressively
- Hierarchical summarization to reduce token size and hallucination
- Token-safe context builder with fallback strategies
"""
import asyncio
import hashlib
import json
import re
import time
import uuid
from typing import AsyncIterator, List, Dict, Any, Optional, Tuple
from services.llm.factory import LLMFactory
from core.config.settings import settings
from core.logging.logger import get_logger
from services.llm.prompts import load_prompt, log_prompt_execution

import numpy as np

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Context selection constants
# ---------------------------------------------------------------------------
_MAX_CONTEXT_CHARS = 50_000        # ~12K tokens — safe for most LLMs
_DASHBOARD_QUERY = (
    "financial performance, risks, KPIs, trends, operational insights, "
    "key metrics, anomalies, summary, cost, revenue, production efficiency, "
    "defect rate, sigma level, root cause analysis, recommendations, "
    "ROP, NPT, drilling, wellbore, mud weight, bit depth, casing, "
    "WOB, torque, standpipe pressure, flow rate, hole depth, stuck pipe"
)
# Bounded cache for ranked chunk indices keyed by content hash.
# TTL=3600s (1 hour), maxsize=500 entries — prevents unbounded memory growth.
try:
    from cachetools import TTLCache
    _ranked_cache: Dict[str, List[int]] = TTLCache(maxsize=500, ttl=3600)
except ImportError:
    # Fallback: plain dict with manual size cap
    _ranked_cache: Dict[str, List[int]] = {}


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
            # Semantic top-k selection + token-safe context builder
            selected = self._select_context_chunks(text_chunks, max_chunks=20)
            combined_content = self._build_context(selected, max_chars=_MAX_CONTEXT_CHARS)

            # Load prompt dynamically using prompt versioning system
            logger.info(
                f"Loading prompt 'dashboard' version '{self.prompt_version}' (A/B: {self.use_ab_test}), "
                f"context: {len(combined_content):,} chars from {len(selected)}/{len(text_chunks)} chunks"
            )
            prompt = load_prompt(
                prompt_name="dashboard",
                version=self.prompt_version,
                use_ab_test=self.use_ab_test,
                content=combined_content,
                num_chunks=len(selected)
            )
            
            # Generate dashboard using LLM
            logger.info("Generating dashboard using LLM...")
            response = self.llm.generate_json(prompt)
            
            # Parse and validate response
            dashboard_data = self._parse_dashboard_response(response, file_name, chunks=text_chunks)
            
            # Extract metrics for logging
            if "dashboard" in dashboard_data:
                kpi_count = len(dashboard_data["dashboard"].get("kpis", []))
                chart_count = len(dashboard_data["dashboard"].get("charts", []))
            
            # ── 3-tier validation: AI → cache → heuristic ──
            if self._is_empty_dashboard(dashboard_data):
                logger.warning("Gemini failed → using fallback")
                cached = self._get_cached_dashboard(doc_id)
                if cached and not self._is_empty_dashboard(cached):
                    logger.info("Using cached dashboard (previous successful AI run)")
                    dashboard_data = cached
                elif text_chunks:
                    logger.info("Cache miss → generating heuristic dashboard")
                    dashboard_data = self._generate_heuristic_dashboard(text_chunks, file_name)
                # re-extract metrics after fallback
                if "dashboard" in dashboard_data:
                    kpi_count = len(dashboard_data["dashboard"].get("kpis", []))
                    chart_count = len(dashboard_data["dashboard"].get("charts", []))

            success = True
            logger.info(f"Dashboard generated successfully (KPIs: {kpi_count}, Charts: {chart_count})")

            # Cache valid result for future fallback lookups
            if not self._is_empty_dashboard(dashboard_data):
                self._cache_dashboard(doc_id, dashboard_data)

            return self._validate_dashboard(dashboard_data)
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Dashboard generation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._validate_dashboard(
                self._get_fallback_dashboard(file_name, error_message, chunks=text_chunks, doc_id=doc_id)
            )
        
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
                        "selected_chunks": len(selected) if 'selected' in dir() else 0,
                        "content_length": len(combined_content),
                        "mode": "semantic_context_aware",
                        "ab_test_enabled": self.use_ab_test
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log prompt execution: {log_error}")

    # ------------------------------------------------------------------
    # Async + context-aware dashboard generation (optimized path)
    # ------------------------------------------------------------------

    async def agenerate_dashboard(
        self,
        chunks: List[str],
        file_name: str = "document",
        doc_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_context_chunks: int = 20,
    ) -> Dict[str, Any]:
        """
        Generate dashboard using semantic chunk ranking + token-safe context.

        Pipeline:
        1. Semantic ranking — embed dashboard query + chunks, cosine top-k
        2. Optional hierarchical summary for very large selections
        3. Build structured context (summary + key chunks) within token budget
        4. Send compact, high-signal prompt to LLM

        Token usage reduced ~60-80% vs full-document approach.
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        success = False
        kpi_count = 0
        chart_count = 0
        error_message = None
        selected_content = ""
        n_selected = 0

        try:
            # Step 1: Semantic top-k selection (embedding-based with keyword fallback)
            selected = await asyncio.to_thread(
                self._select_context_chunks, chunks, max_context_chunks,
            )
            n_selected = len(selected)

            # Step 2: For large selections, generate a hierarchical summary
            summary = None
            if len("\n".join(selected)) > _MAX_CONTEXT_CHARS:
                summary = await self._hierarchical_summarize(selected)

            # Step 3: Build token-safe context
            selected_content = self._build_context(
                selected, max_chars=_MAX_CONTEXT_CHARS, summary=summary,
            )

            # Step 4: Load prompt and generate
            prompt = load_prompt(
                prompt_name="dashboard",
                version=self.prompt_version,
                use_ab_test=self.use_ab_test,
                content=selected_content,
                num_chunks=n_selected,
            )

            response = await asyncio.wait_for(
                asyncio.to_thread(self.llm.generate_json, prompt),
                timeout=180,
            )

            dashboard_data = self._parse_dashboard_response(response, file_name, chunks=chunks)

            if "dashboard" in dashboard_data:
                kpi_count = len(dashboard_data["dashboard"].get("kpis", []))
                chart_count = len(dashboard_data["dashboard"].get("charts", []))

            # ── 3-tier validation: AI → cache → heuristic ──
            if self._is_empty_dashboard(dashboard_data):
                logger.warning("Gemini failed → using fallback")
                cached = self._get_cached_dashboard(doc_id)
                if cached and not self._is_empty_dashboard(cached):
                    logger.info("Using cached dashboard (previous successful AI run)")
                    dashboard_data = cached
                elif chunks:
                    logger.info("Cache miss → generating heuristic dashboard")
                    dashboard_data = self._generate_heuristic_dashboard(chunks, file_name)
                # re-extract metrics after fallback
                if "dashboard" in dashboard_data:
                    kpi_count = len(dashboard_data["dashboard"].get("kpis", []))
                    chart_count = len(dashboard_data["dashboard"].get("charts", []))

            success = True
            logger.info(
                f"Async dashboard generated (KPIs: {kpi_count}, Charts: {chart_count}, "
                f"context: {len(selected_content):,} chars from {n_selected}/{len(chunks)} chunks)"
            )

            # Cache valid result for future fallback lookups
            if not self._is_empty_dashboard(dashboard_data):
                self._cache_dashboard(doc_id, dashboard_data)

            return self._validate_dashboard(dashboard_data)

        except asyncio.TimeoutError:
            error_message = "Dashboard LLM call timed out after 180s"
            logger.error(error_message)
            return self._validate_dashboard(
                self._get_fallback_dashboard(file_name, error_message, chunks=chunks, doc_id=doc_id)
            )
        except Exception as e:
            error_message = str(e)
            logger.error(f"Async dashboard error: {e}")
            return self._validate_dashboard(
                self._get_fallback_dashboard(file_name, error_message, chunks=chunks, doc_id=doc_id)
            )
        finally:
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
                        "num_chunks": len(chunks),
                        "selected_chunks": n_selected,
                        "context_length": len(selected_content),
                        "mode": "semantic_context_aware",
                    },
                )
            except Exception as log_error:
                logger.warning(f"Failed to log prompt execution: {log_error}")

    # ------------------------------------------------------------------
    # SSE streaming — progressive dashboard delivery
    # ------------------------------------------------------------------

    async def agenerate_dashboard_stream(
        self,
        chunks: List[str],
        file_name: str = "document",
        doc_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_context_chunks: int = 20,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate dashboard and yield sections progressively via SSE.

        Stages emitted:
            1. context_ready  — chunk selection done, LLM call starting
            2. kpis           — KPIs extracted
            3. charts         — charts/tables ready
            4. insights       — insights + recommendations
            5. sixSigma       — deterministic Six Sigma analysis
            6. complete       — full dashboard assembled

        The LLM is called ONCE (unchanged cost).  Sections are parsed
        from the single response and yielded in priority order so the
        frontend can render KPIs within ~1-2s of the LLM returning.
        """
        start_time = time.time()

        # ── 1. Context preparation ───────────────────────────────────
        try:
            selected = await asyncio.to_thread(
                self._select_context_chunks, chunks, max_context_chunks,
            )
        except Exception as exc:
            yield {"stage": "error", "error": f"Context selection failed: {exc}"}
            return

        summary = None
        if len("\n".join(selected)) > _MAX_CONTEXT_CHARS:
            try:
                summary = await self._hierarchical_summarize(selected)
            except Exception:
                pass

        selected_content = self._build_context(
            selected, max_chars=_MAX_CONTEXT_CHARS, summary=summary,
        )

        yield {
            "stage": "context_ready",
            "data": {
                "chunks_selected": len(selected),
                "chunks_total": len(chunks),
                "context_chars": len(selected_content),
            },
        }

        # ── 2. LLM call ─────────────────────────────────────────────
        try:
            prompt = load_prompt(
                prompt_name="dashboard",
                version=self.prompt_version,
                use_ab_test=self.use_ab_test,
                content=selected_content,
                num_chunks=len(selected),
            )

            response = await asyncio.wait_for(
                asyncio.to_thread(self.llm.generate_json, prompt),
                timeout=180,
            )
        except asyncio.TimeoutError:
            yield {"stage": "error", "error": "Dashboard LLM call timed out after 180s"}
            return
        except Exception as exc:
            yield {"stage": "error", "error": f"LLM generation failed: {exc}"}
            return

        # ── 3. Parse response ────────────────────────────────────────
        parsed = self._parse_dashboard_response(response, file_name, chunks=selected)
        dashboard = parsed.get("dashboard", {})

        # ── 4. Yield sections in priority order ──────────────────────

        # KPIs — highest priority, fastest to render
        kpis = dashboard.get("kpis", [])
        yield {
            "stage": "kpis",
            "data": {
                "title": dashboard.get("title", f"Analytics Dashboard - {file_name}"),
                "description": dashboard.get("description", ""),
                "kpis": kpis,
            },
        }

        # Charts + Tables
        charts = dashboard.get("charts", [])
        tables = dashboard.get("tables", [])
        if charts or tables:
            yield {
                "stage": "charts",
                "data": {"charts": charts, "tables": tables},
            }

        # Insights + Recommendations
        insights = dashboard.get("insights", {})
        suggestions = dashboard.get("optimizationSuggestions", [])
        yield {
            "stage": "insights",
            "data": {"insights": insights, "optimizationSuggestions": suggestions},
        }

        # Six Sigma (deterministic, runs after LLM)
        six_sigma = dashboard.get("sixSigma", {})
        yield {
            "stage": "sixSigma",
            "data": {"sixSigma": six_sigma},
        }

        # ── 5. Complete — full assembled payload ─────────────────────
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Streamed dashboard for {doc_id or file_name} in {elapsed_ms}ms "
            f"(KPIs: {len(kpis)}, Charts: {len(charts)})"
        )

        yield {
            "stage": "complete",
            "data": {"dashboard": dashboard, "elapsed_ms": elapsed_ms},
        }

    def _select_context_chunks(self, chunks: List[str], max_chunks: int = 20) -> List[str]:
        """
        Select the most informative chunks for dashboard generation.

        Strategy (layered):
        1. Semantic ranking — embed a dashboard-needs query + all chunks,
           rank by cosine similarity.  Fast (~50ms local SentenceTransformer).
        2. Keyword fallback — if embedding fails, score by analytics-keyword
           density (no external dependency).
        3. Always include first + last chunk (intro/conclusion bias).

        Returns chunks in original document order for coherent reading.
        """
        if len(chunks) <= max_chunks:
            return chunks

        # Check ranked-chunk cache (keyed by content hash of joined chunks)
        cache_key = hashlib.sha256("||".join(chunks).encode("utf-8")).hexdigest()[:24]
        if cache_key in _ranked_cache:
            cached_indices = _ranked_cache[cache_key][:max_chunks]
            cached_indices.sort()
            return [chunks[i] for i in cached_indices]

        # ---------- Try semantic ranking first ----------
        try:
            ranked_indices = self._semantic_rank_chunks(chunks, max_chunks)
            # Evict oldest entries if fallback dict exceeds cap
            if len(_ranked_cache) >= 500 and not hasattr(_ranked_cache, 'ttl'):
                oldest_keys = list(_ranked_cache.keys())[:100]
                for k in oldest_keys:
                    _ranked_cache.pop(k, None)
            _ranked_cache[cache_key] = ranked_indices
            ranked_indices_sorted = sorted(ranked_indices)
            return [chunks[i] for i in ranked_indices_sorted]
        except Exception as e:
            logger.warning(f"Semantic ranking failed, using keyword fallback: {e}")

        # ---------- Keyword-density fallback ----------
        return self._keyword_rank_chunks(chunks, max_chunks)

    # ------------------------------------------------------------------
    # Semantic ranking (embedding-based)
    # ------------------------------------------------------------------

    def _semantic_rank_chunks(
        self, chunks: List[str], top_k: int = 20,
    ) -> List[int]:
        """
        Rank chunks by cosine similarity to a dashboard-needs query.

        Uses the same SentenceTransformer model as the embedding pipeline
        so representations are consistent.  Runs locally — no Qdrant needed.
        """
        from services.vector_store.indexing.vector_storage import get_vector_service

        svc = get_vector_service()
        query_emb = np.array(svc.generate_query_embedding(_DASHBOARD_QUERY))

        # Batch embed all chunks (local model, ~50ms for 20 chunks)
        chunk_embs = np.array(svc.generate_embeddings_batch(chunks, show_progress=False))

        # Cosine similarity (vectorised)
        norms = np.linalg.norm(chunk_embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # avoid div-by-zero
        chunk_embs_normed = chunk_embs / norms
        query_norm = np.linalg.norm(query_emb)
        if query_norm == 0:
            raise ValueError("Query embedding is zero vector")
        query_emb_normed = query_emb / query_norm

        scores = chunk_embs_normed @ query_emb_normed  # shape (N,)

        # Positional bias: slight boost for first/last chunks
        scores[0] += 0.05
        scores[-1] += 0.05

        # Top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k].tolist()
        logger.debug(
            f"Semantic ranking: top scores = "
            f"{[f'{scores[i]:.3f}' for i in top_indices[:5]]}"
        )
        return top_indices

    # ------------------------------------------------------------------
    # Keyword-density fallback (no external deps)
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_rank_chunks(chunks: List[str], max_chunks: int = 20) -> List[str]:
        """Score chunks by analytics-keyword density. Deterministic fallback."""
        keywords = {
            "kpi", "metric", "target", "actual", "variance", "trend", "forecast",
            "risk", "cost", "revenue", "production", "efficiency", "defect",
            "sigma", "yield", "throughput", "downtime", "safety", "compliance",
            "budget", "roi", "margin", "utilization", "capacity", "rate",
            "improvement", "reduction", "increase", "decrease", "total", "average",
            "summary", "conclusion", "recommendation", "finding", "result",
            "table", "chart", "figure", "analysis", "overview", "performance",
            # Drilling / oil & gas domain
            "rop", "npt", "drilling", "wellbore", "casing", "mud", "torque",
            "wob", "bit", "depth", "hole", "stuck", "pipe", "bha", "rig",
            "spud", "cement", "liner", "completion", "circulation", "pressure",
            "standpipe", "annular", "weight", "flow", "pump", "hse", "bop",
            "footage", "barrel", "personnel", "incident", "jarring",
        }
        scored: List[Tuple[int, float, str]] = []
        for i, chunk in enumerate(chunks):
            lower = chunk.lower()
            words = set(re.findall(r'\b\w+\b', lower))
            score = len(words & keywords) + 0.3 * len(re.findall(r'\b\d+\.?\d*\b', chunk))
            if i == 0 or i == len(chunks) - 1:
                score += 5
            scored.append((i, score, chunk))

        scored.sort(key=lambda x: x[1], reverse=True)
        selected = scored[:max_chunks]
        selected.sort(key=lambda x: x[0])
        return [s[2] for s in selected]

    # ------------------------------------------------------------------
    # Context builder — structured, token-safe
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(
        chunks: List[str],
        max_chars: int = _MAX_CONTEXT_CHARS,
        summary: Optional[str] = None,
    ) -> str:
        """
        Build a structured, token-safe context string for the LLM.

        Format:
            DOCUMENT SUMMARY:
            <summary if available>

            KEY CONTEXT:
            [Section 1] <chunk text>
            ---
            [Section 2] <chunk text>
            ...

        Truncates intelligently at chunk boundaries to stay within max_chars.
        """
        parts: List[str] = []
        budget = max_chars

        if summary:
            header = f"DOCUMENT SUMMARY:\n{summary}\n\nKEY CONTEXT:\n"
            parts.append(header)
            budget -= len(header)
        else:
            parts.append("KEY CONTEXT:\n")
            budget -= len("KEY CONTEXT:\n")

        for idx, chunk in enumerate(chunks):
            section_label = f"[Section {idx + 1}]"
            entry = f"{section_label} {chunk}"
            if len(entry) > budget:
                # Fit as much of this last chunk as possible
                if budget > len(section_label) + 100:
                    entry = f"{section_label} {chunk[:budget - len(section_label) - 4]}..."
                    parts.append(entry)
                break
            parts.append(entry)
            budget -= len(entry) + 5  # account for separator
            if budget <= 0:
                break

        return "\n\n---\n\n".join(parts)

    async def _hierarchical_summarize(self, chunks: List[str]) -> str:
        """
        Summarize chunks hierarchically for very large documents.
        Splits chunks into groups, summarizes each group, then merges.
        """
        group_size = 5
        groups = [chunks[i:i + group_size] for i in range(0, len(chunks), group_size)]

        async def _summarize_group(group: List[str]) -> str:
            text = "\n\n".join(group)
            prompt = (
                "Summarize the following document section, preserving ALL numerical data, "
                "KPIs, metrics, findings, and recommendations. Keep tables and figures referenced.\n\n"
                f"{text[:30_000]}\n\n"
                "Provide a concise but data-rich summary (max 2000 words)."
            )
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(self.llm.generate, prompt),
                    timeout=30,
                )
                return result
            except Exception as e:
                logger.warning(f"Group summarization failed: {e}")
                return text[:5000]  # fallback: truncate

        summaries = await asyncio.gather(*[_summarize_group(g) for g in groups])
        return "\n\n---\n\n".join(summaries)

    def _parse_dashboard_response(self, response: Any, file_name: str, chunks: Optional[List[str]] = None) -> Dict[str, Any]:
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
                    from features.six_sigma import run_six_sigma
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
                    return self._parse_dashboard_response(parsed, file_name, chunks=chunks)
            
            # Fallback
            return self._get_fallback_dashboard(file_name, "Invalid response format", chunks=chunks)
            
        except Exception as e:
            logger.error(f"Error parsing dashboard response: {e}")
            return self._get_fallback_dashboard(file_name, str(e), chunks=chunks)
    
    # ------------------------------------------------------------------
    # Dashboard cache — retrieves last successful dashboard from SQLite
    # ------------------------------------------------------------------

    @staticmethod
    def _get_cached_dashboard(doc_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Look up the last successfully generated dashboard for this doc_id
        from SQLite.  Returns the dashboard dict or None on miss.
        """
        if not doc_id:
            return None
        try:
            import sqlite3 as _sqlite3
            from core.config.settings import settings as _settings
            db_path = _settings.DATABASE_URL.replace('sqlite:///', '')
            conn = _sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                'SELECT dashboard_data FROM documents WHERE id = ?', (doc_id,)
            )
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                cached = json.loads(row[0])
                # Must be a dict with a populated "dashboard" key
                if isinstance(cached, dict):
                    db = cached.get("dashboard", cached)
                    if isinstance(db, dict) and len(db.get("kpis", [])) > 0:
                        logger.info(
                            f"Cache HIT for doc_id={doc_id}: "
                            f"{len(db.get('kpis',[]))} KPIs, "
                            f"{len(db.get('charts',[]))} charts"
                        )
                        if "dashboard" in cached:
                            return cached
                        return {"dashboard": db}
            logger.debug(f"Cache MISS for doc_id={doc_id}")
        except Exception as exc:
            logger.warning(f"Dashboard cache lookup failed: {exc}")
        return None

    @staticmethod
    def _cache_dashboard(doc_id: Optional[str], dashboard_data: Dict[str, Any]) -> None:
        """
        Write a valid (non-empty) dashboard result to SQLite so future
        fallback lookups can retrieve it.  Skips write if doc_id is None
        or dashboard is empty.
        """
        if not doc_id:
            return
        if DashboardGenerator._is_empty_dashboard(dashboard_data):
            return
        try:
            import sqlite3 as _sqlite3
            from core.config.settings import settings as _settings
            db_path = _settings.DATABASE_URL.replace('sqlite:///', '')
            conn = _sqlite3.connect(db_path)
            conn.execute(
                "UPDATE documents SET dashboard_data = ? WHERE id = ?",
                (json.dumps(dashboard_data), doc_id),
            )
            conn.commit()
            conn.close()
            db = dashboard_data.get("dashboard", dashboard_data)
            logger.info(
                f"Cache WRITE for doc_id={doc_id}: "
                f"{len(db.get('kpis',[]))} KPIs, "
                f"{len(db.get('charts',[]))} charts"
            )
        except Exception as exc:
            logger.warning(f"Dashboard cache write failed: {exc}")

    # ------------------------------------------------------------------
    # Deterministic fallback engine — guarantees non-empty dashboard
    # ------------------------------------------------------------------

    @staticmethod
    def _is_empty_dashboard(dashboard_data: Dict[str, Any]) -> bool:
        """Return True if AI-generated dashboard has no meaningful content."""
        if not dashboard_data or "dashboard" not in dashboard_data:
            return True
        db = dashboard_data["dashboard"]
        has_kpis = len(db.get("kpis", [])) > 0
        has_charts = len(db.get("charts", [])) > 0
        has_tables = len(db.get("tables", [])) > 0
        return not (has_kpis or has_charts or has_tables)

    @staticmethod
    def _validate_dashboard(dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final contract gate — guarantees the returned dashboard has non-empty
        kpis and charts.  If either is missing, injects minimal placeholders
        so the frontend never receives an unrenderable payload.
        """
        if not dashboard_data or "dashboard" not in dashboard_data:
            dashboard_data = {"dashboard": {}}
        db = dashboard_data["dashboard"]

        if "kpis" not in db or len(db["kpis"]) == 0:
            db["kpis"] = [{
                "id": "kpi-validate-1",
                "title": "Document Status",
                "value": "Processing",
                "unit": "",
                "change": "N/A",
                "changeType": "neutral",
                "icon": "Activity",
                "color": "#3b82f6",
            }]

        if "charts" not in db or len(db["charts"]) == 0:
            db["charts"] = [{
                "id": "chart-validate-1",
                "type": "bar",
                "title": "Status Overview",
                "size": "medium",
                "data": [{"name": k["title"], "value": 1} for k in db["kpis"][:4]],
                "chartConfig": {"value": {"label": "Value", "color": "#3b82f6"}},
            }]

        # Ensure required wrapper keys exist
        db.setdefault("title", "Analytics Dashboard")
        db.setdefault("description", "")
        db.setdefault("tables", [])
        db.setdefault("insights", {"summary": "", "trends": [], "alerts": [], "recommendations": []})
        db.setdefault("sixSigma", {})
        db.setdefault("optimizationSuggestions", [])

        dashboard_data["dashboard"] = db
        return dashboard_data

    @staticmethod
    def _extract_metrics(chunks: List[str]) -> List[Dict[str, Any]]:
        """Extract numeric metrics from raw chunk text using regex patterns."""
        metrics: List[Dict[str, Any]] = []
        seen: set = set()
        all_text = "\n".join(chunks)

        # Pattern 1: Labeled currency — "Revenue: $1,234" or "Total Cost = $45.2M"
        for m in re.finditer(
            r'(?P<label>[A-Z][a-zA-Z\s/]{2,35}?)\s*[:=]\s*\$\s*(?P<value>[\d,]+\.?\d*)\s*(?P<suffix>[BMKbmk])?',
            all_text,
        ):
            label = m.group("label").strip()
            raw = m.group("value").replace(",", "")
            suffix = (m.group("suffix") or "").upper()
            value = float(raw)
            multiplier = {"B": 1e9, "M": 1e6, "K": 1e3}.get(suffix, 1)
            value *= multiplier
            key = label.lower()
            if key not in seen:
                seen.add(key)
                display = f"${raw}{m.group('suffix') or ''}"
                metrics.append({"label": label, "value": value, "unit": "$", "display": display, "type": "currency"})

        # Pattern 2: Labeled percentage — "Efficiency: 94.5%"
        for m in re.finditer(
            r'(?P<label>[A-Z][a-zA-Z\s/]{2,35}?)\s*[:=]\s*(?P<value>\d+\.?\d*)\s*%',
            all_text,
        ):
            label = m.group("label").strip()
            value = float(m.group("value"))
            key = label.lower()
            if key not in seen:
                seen.add(key)
                metrics.append({"label": label, "value": value, "unit": "%", "display": f"{value}%", "type": "percentage"})

        # Pattern 3: Labeled quantity — "Production: 12,500 units"
        for m in re.finditer(
            r'(?P<label>[A-Z][a-zA-Z\s/]{2,35}?)\s*[:=]\s*(?P<value>[\d,]+\.?\d*)\s+(?P<unit>units?|tons?|hours?|days?|items?|barrels?|MW|GW|kW|pieces?|employees?|workers?|projects?)',
            all_text,
        ):
            label = m.group("label").strip()
            raw = m.group("value").replace(",", "")
            unit = m.group("unit")
            value = float(raw)
            key = label.lower()
            if key not in seen:
                seen.add(key)
                metrics.append({"label": label, "value": value, "unit": unit, "display": f"{m.group('value')} {unit}", "type": "quantity"})

        # Pattern 4: Standalone large currency — "$1,234,567" near keywords
        kw = r'(?:revenue|cost|profit|loss|budget|expense|income|sales|total|net|gross)'
        for m in re.finditer(
            rf'({kw})[\s:]*\$\s*([\d,]+\.?\d*)\s*([BMKbmk])?',
            all_text, re.IGNORECASE,
        ):
            label = m.group(1).strip().title()
            raw = m.group(2).replace(",", "")
            suffix = (m.group(3) or "").upper()
            value = float(raw) * {"B": 1e9, "M": 1e6, "K": 1e3}.get(suffix, 1)
            key = label.lower()
            if key not in seen:
                seen.add(key)
                metrics.append({"label": label, "value": value, "unit": "$", "display": f"${raw}{m.group(3) or ''}", "type": "currency"})

        # Sort: currency → percentage → quantity
        order = {"currency": 0, "percentage": 1, "quantity": 2}
        metrics.sort(key=lambda x: order.get(x["type"], 3))
        return metrics[:20]

    # ------------------------------------------------------------------
    # Domain detection
    # ------------------------------------------------------------------

    _DRILLING_KEYWORDS = {
        "rop", "npt", "drilling", "wellbore", "casing", "mud", "torque",
        "wob", "bit", "bha", "rig", "spud", "cement", "liner", "completion",
        "circulation", "standpipe", "annular", "hole", "stuck", "pipe",
        "jarring", "footage", "bop", "hse", "depth", "pooh", "rih",
        "tripping", "kelly", "rotary", "derrick", "drawworks", "top drive",
        "dogleg", "inclination", "azimuth", "survey", "sidetrack",
    }

    @staticmethod
    def _detect_domain(chunks: List[str]) -> str:
        """Detect document domain from chunk content. Returns 'drilling' or 'general'."""
        all_text_lower = " ".join(chunks).lower()
        words = set(re.findall(r'\b\w+\b', all_text_lower))
        drilling_hits = words & DashboardGenerator._DRILLING_KEYWORDS
        # Threshold: 4+ drilling keywords → drilling domain
        if len(drilling_hits) >= 4:
            logger.info(f"Domain detected: drilling (matched: {drilling_hits})")
            return "drilling"
        return "general"

    # ------------------------------------------------------------------
    # Drilling-domain metric extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_drilling_metrics(chunks: List[str]) -> Dict[str, Any]:
        """Extract drilling-specific metrics (ROP, NPT, depth, mud weight, etc.) from text."""
        all_text = "\n".join(chunks)
        data: Dict[str, Any] = {}

        # ROP — "ROP: 12.4 ft/hr" or "ROP = 15.2" or "rate of penetration 12.4"
        m = re.search(r'(?:ROP|rate\s+of\s+penetration)\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:ft/hr|ft/h)?', all_text, re.IGNORECASE)
        if m:
            data["rop"] = float(m.group(1).replace(",", ""))

        # NPT — "NPT: 8.3%" or "NPT = 120 hrs" or "non.productive.time: 23%"
        m = re.search(r'(?:NPT|non[- ]?productive\s*time)\s*[:=]?\s*([\d,]+\.?\d*)\s*(%|hrs?|hours?)?', all_text, re.IGNORECASE)
        if m:
            val = float(m.group(1).replace(",", ""))
            unit = (m.group(2) or "").strip().lower()
            if unit == "%" or val <= 100:
                data["npt"] = val
                data["npt_unit"] = "%"
            else:
                data["npt"] = val
                data["npt_unit"] = "hrs"

        # Depth — "depth: 23,695 ft" or "current depth 18500"
        m = re.search(r'(?:current\s+)?(?:depth|TD|total\s+depth|measured\s+depth|MD)\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:ft|m)?', all_text, re.IGNORECASE)
        if m:
            data["depth"] = float(m.group(1).replace(",", ""))

        # Mud weight — "mud weight: 92 pcf" or "MW = 12.5 ppg"
        m = re.search(r'(?:mud\s*weight|MW)\s*[:=]?\s*([\d,]+\.?\d*)\s*(pcf|ppg|lb/gal)?', all_text, re.IGNORECASE)
        if m:
            data["mud_weight"] = float(m.group(1).replace(",", ""))
            data["mud_weight_unit"] = m.group(2) or "pcf"

        # WOB — "WOB: 25 klbs" or "weight on bit = 30"
        m = re.search(r'(?:WOB|weight\s+on\s+bit)\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:klbs?|lbs?)?', all_text, re.IGNORECASE)
        if m:
            data["wob"] = float(m.group(1).replace(",", ""))

        # Torque — "torque: 12,500 ft-lbs"
        m = re.search(r'torque\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:ft[- ]?lbs?)?', all_text, re.IGNORECASE)
        if m:
            data["torque"] = float(m.group(1).replace(",", ""))

        # Standpipe pressure — "SPP: 3200 psi"
        m = re.search(r'(?:SPP|standpipe\s*pressure)\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:psi)?', all_text, re.IGNORECASE)
        if m:
            data["spp"] = float(m.group(1).replace(",", ""))

        # Daily footage — "daily footage: 250 ft" or "footage = 400"
        m = re.search(r'(?:daily\s+)?footage\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:ft)?', all_text, re.IGNORECASE)
        if m:
            data["footage"] = float(m.group(1).replace(",", ""))

        # Days since spud — "days since spud: 115"
        m = re.search(r'days?\s*(?:since\s+)?spud\s*[:=]?\s*(\d+)', all_text, re.IGNORECASE)
        if m:
            data["days_spud"] = int(m.group(1))

        # Rig / well identification
        m = re.search(r'(?:rig|rig\s+id)\s*[:=]?\s*([A-Z0-9]{3,10})', all_text, re.IGNORECASE)
        if m:
            data["rig_id"] = m.group(1)

        m = re.search(r'(?:well|well\s+id)\s*[:=]?\s*([A-Z]{2,6}[- ]?\d{2,5})', all_text, re.IGNORECASE)
        if m:
            data["well_id"] = m.group(1)

        # Time-series: look for repeated depth/time pairs as "timeseries"
        timeseries: List[Dict[str, Any]] = []
        for ts_m in re.finditer(
            r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2}).*?(\d+\.?\d*)\s*(?:ft|hr)',
            all_text,
        ):
            timeseries.append({
                "time": f"{ts_m.group(1)}-{ts_m.group(2)}",
                "value": float(ts_m.group(3)),
            })
        if timeseries:
            data["timeseries"] = timeseries[:20]

        return data

    # ------------------------------------------------------------------
    # Heuristic dashboard — drilling-domain aware
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_heuristic_dashboard(chunks: List[str], file_name: str) -> Dict[str, Any]:
        """
        Generate a heuristic dashboard from chunk data.
        Domain-aware: produces drilling-specific KPIs (ROP, NPT) for drilling docs,
        falls back to generic metric extraction for other domains.
        """
        domain = DashboardGenerator._detect_domain(chunks)

        if domain == "drilling":
            data = DashboardGenerator._extract_drilling_metrics(chunks)
            return DashboardGenerator._build_drilling_dashboard(data, file_name)

        # Non-drilling: use generic deterministic extraction
        return DashboardGenerator._generate_deterministic_dashboard(chunks, file_name)

    @staticmethod
    def _build_drilling_dashboard(data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
        """Build drilling-domain dashboard from extracted drilling metrics."""
        rig_id = data.get("rig_id", "N/A")
        well_id = data.get("well_id", "N/A")

        # ── KPIs ──
        kpis: List[Dict[str, Any]] = []
        kpi_defs = [
            ("ROP", data.get("rop"), "ft/hr", "TrendingUp", "#3b82f6"),
            ("NPT", data.get("npt"), data.get("npt_unit", "%"), "AlertTriangle", "#ef4444"),
            ("Hole Depth", data.get("depth"), "ft", "ArrowDown", "#8b5cf6"),
            ("Mud Weight", data.get("mud_weight"), data.get("mud_weight_unit", "pcf"), "Droplets", "#06b6d4"),
            ("WOB", data.get("wob"), "klbs", "Target", "#f59e0b"),
            ("Torque", data.get("torque"), "ft-lbs", "RotateCw", "#ec4899"),
            ("SPP", data.get("spp"), "psi", "Gauge", "#10b981"),
            ("Daily Footage", data.get("footage"), "ft", "BarChart2", "#14b8a6"),
        ]

        for i, (title, value, unit, icon, color) in enumerate(kpi_defs):
            if value is not None:
                display = f"{value:,.1f}" if isinstance(value, float) else str(value)
                change = "+0%"
                change_type = "neutral"
                if title == "NPT" and isinstance(value, (int, float)):
                    if value > 15:
                        change = "High"
                        change_type = "negative"
                    elif value < 5:
                        change = "Low"
                        change_type = "positive"
                kpis.append({
                    "id": f"kpi-drill-{i+1}",
                    "title": title,
                    "value": f"{display} {unit}".strip(),
                    "unit": unit,
                    "change": change,
                    "changeType": change_type,
                    "icon": icon,
                    "color": color,
                })

        # Guarantee at least one KPI even if nothing was extracted
        if not kpis:
            kpis.append({
                "id": "kpi-drill-status",
                "title": "Drilling Status",
                "value": "Active",
                "unit": "",
                "change": "N/A",
                "changeType": "neutral",
                "icon": "Activity",
                "color": "#3b82f6",
            })

        # ── Charts ──
        charts: List[Dict[str, Any]] = []

        # Timeseries chart (if extracted)
        timeseries = data.get("timeseries", [])
        if timeseries:
            charts.append({
                "id": "chart-drill-timeseries",
                "type": "line",
                "title": "Drilling Activity Timeline",
                "size": "large",
                "data": timeseries,
                "chartConfig": {
                    "value": {"label": "Value", "color": "#3b82f6"},
                },
            })

        # KPI summary bar chart
        numeric_kpis = [
            {"name": k["title"], "value": float(re.search(r'[\\d,]+\\.?\\d*', k["value"]).group().replace(",", ""))}
            for k in kpis
            if re.search(r'[\\d,]+\\.?\\d*', str(k.get("value", "")))
        ]
        if not numeric_kpis:
            # Safer extraction
            for k in kpis:
                val_match = re.search(r'[\d,]+\.?\d*', str(k.get("value", "")))
                if val_match:
                    numeric_kpis.append({"name": k["title"], "value": float(val_match.group().replace(",", ""))})

        if numeric_kpis:
            charts.append({
                "id": "chart-drill-kpi-summary",
                "type": "bar",
                "title": "Drilling KPI Summary",
                "size": "large",
                "data": numeric_kpis[:8],
                "chartConfig": {"value": {"label": "Value", "color": "#8b5cf6"}},
            })

        # ── Tables ──
        table_rows = [{"metric": k["title"], "value": k["value"], "unit": k["unit"]} for k in kpis]
        tables: List[Dict[str, Any]] = [{
            "title": "Drilling Parameters Summary",
            "columns": [
                {"title": "Parameter", "dataIndex": "metric", "key": "metric"},
                {"title": "Value", "dataIndex": "value", "key": "value"},
                {"title": "Unit", "dataIndex": "unit", "key": "unit"},
            ],
            "data": table_rows,
        }] if table_rows else []

        rig_label = f"Rig {rig_id}" if rig_id != "N/A" else ""
        well_label = f"Well {well_id}" if well_id != "N/A" else ""
        subtitle = " / ".join(filter(None, [rig_label, well_label]))

        logger.info(
            f"Heuristic drilling dashboard: {len(kpis)} KPIs, {len(charts)} charts, "
            f"{len(tables)} tables ({subtitle or file_name})"
        )

        return {
            "dashboard": {
                "title": f"Operational Summary — {subtitle or file_name}",
                "description": f"Drilling heuristic analysis of {file_name}" + (f" ({subtitle})" if subtitle else "") + " — AI unavailable",
                "kpis": kpis,
                "charts": charts,
                "tables": tables,
                "optimizationSuggestions": [
                    "Re-process with AI for root cause analysis and DMAIC recommendations",
                    "Review NPT events for stuck pipe mitigation" if data.get("npt") and data["npt"] > 10 else "Monitor drilling parameters for anomalies",
                ],
                "sixSigma": {
                    "dmaic": {
                        "define": f"Drilling report '{file_name}' analyzed via heuristic extraction",
                        "measure": f"ROP: {data.get('rop', 'N/A')} ft/hr, NPT: {data.get('npt', 'N/A')}{data.get('npt_unit', '%')}",
                        "analyze": "Pattern-based extraction from drilling report text",
                        "improve": "Re-run with AI for failure mode analysis and recommendations",
                        "control": "Deterministic extraction ensures consistent baseline",
                    },
                    "sigmaLevel": "N/A",
                    "defectRate": "N/A",
                    "processCapability": "Heuristic",
                    "rootCauses": [],
                },
                "insights": {
                    "summary": f"Heuristic drilling analysis: ROP {data.get('rop', 'N/A')} ft/hr, NPT {data.get('npt', 'N/A')}{data.get('npt_unit', '%')}",
                    "trends": [],
                    "alerts": [a for a in [
                        "AI service unavailable — dashboard generated from text extraction",
                        f"High NPT ({data['npt']}{data.get('npt_unit','%')}) detected" if data.get("npt") and data["npt"] > 15 else None,
                    ] if a],
                    "recommendations": [
                        "Re-process document when AI service recovers for enriched analysis",
                        "Review stuck pipe mitigation procedures" if data.get("npt") and data["npt"] > 10 else "Continue monitoring drilling parameters",
                    ],
                },
            }
        }

    @staticmethod
    def _metrics_to_kpis(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert extracted metrics to KPI card format."""
        icons = ["TrendingUp", "DollarSign", "BarChart2", "Activity", "Target", "Percent", "Zap", "Shield"]
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6"]
        kpis: List[Dict[str, Any]] = []
        for i, metric in enumerate(metrics[:8]):
            kpis.append({
                "id": f"kpi-fallback-{i+1}",
                "title": metric["label"],
                "value": metric["display"],
                "unit": metric["unit"],
                "change": "N/A",
                "changeType": "neutral",
                "icon": icons[i % len(icons)],
                "color": colors[i % len(colors)],
            })
        return kpis

    @staticmethod
    def _metrics_to_charts(metrics: List[Dict[str, Any]], kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate charts from extracted metrics."""
        charts: List[Dict[str, Any]] = []

        currency = [m for m in metrics if m["type"] == "currency"]
        if currency:
            charts.append({
                "id": "chart-financial-fallback",
                "type": "bar",
                "title": "Financial Overview",
                "size": "large",
                "data": [{"name": m["label"], "value": m["value"]} for m in currency[:6]],
                "chartConfig": {"value": {"label": "Amount ($)", "color": "#3b82f6"}},
            })

        pct = [m for m in metrics if m["type"] == "percentage"]
        if pct:
            charts.append({
                "id": "chart-percentages-fallback",
                "type": "pie",
                "title": "Performance Metrics",
                "size": "medium",
                "data": [{"name": m["label"], "value": m["value"]} for m in pct[:6]],
                "chartConfig": {"value": {"label": "Percentage", "color": "#10b981"}},
            })

        qty = [m for m in metrics if m["type"] == "quantity"]
        if qty:
            charts.append({
                "id": "chart-quantities-fallback",
                "type": "bar",
                "title": "Operational Metrics",
                "size": "medium",
                "data": [{"name": m["label"], "value": m["value"]} for m in qty[:6]],
                "chartConfig": {"value": {"label": "Value", "color": "#8b5cf6"}},
            })

        # If no typed charts, create a KPI summary chart
        if not charts and kpis:
            numeric_kpis = []
            for kpi in kpis:
                val_match = re.search(r'[\d,]+\.?\d*', str(kpi.get("value", "")))
                if val_match:
                    numeric_kpis.append({"name": kpi["title"], "value": float(val_match.group().replace(",", ""))})
            if numeric_kpis:
                charts.append({
                    "id": "chart-summary-fallback",
                    "type": "bar",
                    "title": "Key Metrics Summary",
                    "size": "large",
                    "data": numeric_kpis[:8],
                    "chartConfig": {"value": {"label": "Value", "color": "#8b5cf6"}},
                })
        return charts

    @staticmethod
    def _metrics_to_tables(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build a summary table from extracted metrics."""
        if not metrics:
            return []
        rows = [{"metric": m["label"], "value": m["display"], "type": m["type"].title()} for m in metrics[:15]]
        return [{
            "title": "Extracted Metrics Summary",
            "columns": [
                {"title": "Metric", "dataIndex": "metric", "key": "metric"},
                {"title": "Value", "dataIndex": "value", "key": "value"},
                {"title": "Type", "dataIndex": "type", "key": "type"},
            ],
            "data": rows,
        }]

    @staticmethod
    def _generate_deterministic_dashboard(chunks: List[str], file_name: str) -> Dict[str, Any]:
        """
        Deterministic fallback: extract KPIs, charts, tables from raw chunk text.
        Guarantees non-empty dashboard even when AI is completely unavailable.
        """
        metrics = DashboardGenerator._extract_metrics(chunks)

        # If no labeled metrics found, generate document statistics
        if not metrics:
            word_count = sum(len(chunk.split()) for chunk in chunks)
            num_sections = len(chunks)
            num_sentences = sum(len(re.findall(r'[.!?]+', chunk)) for chunk in chunks)
            metrics = [
                {"label": "Document Sections", "value": num_sections, "unit": "", "display": str(num_sections), "type": "quantity"},
                {"label": "Word Count", "value": word_count, "unit": "words", "display": f"{word_count:,}", "type": "quantity"},
                {"label": "Sentences", "value": num_sentences, "unit": "", "display": str(num_sentences), "type": "quantity"},
                {"label": "Avg Section Length", "value": round(word_count / max(num_sections, 1)), "unit": "words", "display": f"{round(word_count / max(num_sections, 1)):,}", "type": "quantity"},
            ]

        kpis = DashboardGenerator._metrics_to_kpis(metrics)
        charts = DashboardGenerator._metrics_to_charts(metrics, kpis)
        tables = DashboardGenerator._metrics_to_tables(metrics)

        logger.info(
            f"Deterministic fallback generated: {len(kpis)} KPIs, {len(charts)} charts, {len(tables)} tables "
            f"from {len(metrics)} extracted metrics"
        )

        return {
            "dashboard": {
                "title": f"Analytics Dashboard - {file_name}",
                "description": f"Auto-extracted analysis of {file_name} (deterministic fallback — AI unavailable)",
                "kpis": kpis,
                "charts": charts,
                "tables": tables,
                "optimizationSuggestions": ["Re-process document when AI service is available for richer analysis"],
                "sixSigma": {
                    "dmaic": {
                        "define": f"Document '{file_name}' analyzed via deterministic text extraction",
                        "measure": f"{len(metrics)} metrics extracted from document content",
                        "analyze": "Pattern-based extraction from raw text",
                        "improve": "Re-run with AI for deeper analysis and recommendations",
                        "control": "Deterministic extraction ensures consistent baseline"
                    },
                    "sigmaLevel": "N/A",
                    "defectRate": "N/A",
                    "processCapability": "Deterministic",
                    "rootCauses": []
                },
                "insights": {
                    "summary": f"Deterministic analysis extracted {len(metrics)} metrics from {len(chunks)} document sections",
                    "trends": [],
                    "alerts": ["AI service was unavailable — dashboard generated from text extraction"],
                    "recommendations": ["Re-process document when AI service recovers for enriched analysis"]
                }
            }
        }

    def _get_fallback_dashboard(self, file_name: str, error: str = "", chunks: Optional[List[str]] = None, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Return fallback dashboard — tries cache first, then deterministic extraction."""
        # Tier 1: Try cached dashboard from a previous successful run
        cached = self._get_cached_dashboard(doc_id)
        if cached and not self._is_empty_dashboard(cached):
            logger.info(f"Fallback: using cached dashboard for doc_id={doc_id}")
            return cached

        # Tier 2: Generate meaningful dashboard from raw text
        if chunks and len(chunks) > 0:
            try:
                result = self._generate_heuristic_dashboard(chunks, file_name)
                logger.info(f"Heuristic fallback succeeded for '{file_name}' (error was: {error[:100]})")
                return result
            except Exception as det_err:
                logger.error(f"Heuristic fallback also failed: {det_err}")

        # Last resort: minimal non-empty dashboard with document info
        is_quota_error = '429' in str(error) or 'quota' in str(error).lower() or 'RESOURCE_EXHAUSTED' in str(error)

        if is_quota_error:
            title = f"Queued: {file_name}"
            description = f"API quota exceeded. Document '{file_name}' queued for analysis."
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
                "kpis": [{"id": "kpi-status-1", "title": "Document Status", "value": "Processing", "unit": "", "change": "N/A", "changeType": "neutral", "icon": "Activity", "color": "#3b82f6"}],
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

