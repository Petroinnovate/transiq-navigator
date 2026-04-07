"""
PageIndex tree search — reasoning-based retrieval through the hierarchical tree.

Implements Step 2 of the PageIndex framework:
  "Perform reasoning-based retrieval through tree search"

The algorithm
-------------
1. Present root-level section titles + summaries to Gemini.
2. Gemini selects the most relevant branch(es) for the query.
3. Navigate into selected branches (get children).
4. Repeat until leaf nodes are reached.
5. Return the raw chunk texts for all selected nodes.

Public API
----------
  search_tree(query, tree, chunks, top_k=5) -> List[str]
      Returns a list of text chunks that are most relevant to the query.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .llm_adapter import extract_json, gemini_call

logger = logging.getLogger(__name__)

_MAX_DEPTH          = 4     # Maximum tree traversal depth
_MAX_BRANCHES       = 3     # Maximum branches selected per level
_SUMMARY_PREVIEW_LEN = 300  # Characters of summary/text used in LLM prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_preview(node: Dict) -> str:
    """One-line description of a node for the LLM prompt."""
    node_id  = node.get("node_id", "?")
    title    = node.get("title", "Untitled")
    summary  = node.get("summary", "")
    section_path = node.get("section_path", "")
    signals = node.get("signals", {}) if isinstance(node.get("signals"), dict) else {}
    numeric_hits = signals.get("numeric_hits", 0)
    kpi_hits = signals.get("kpi_hits", 0)
    entity_hints = signals.get("entity_hints", [])
    entity_preview = ", ".join(entity_hints[:3]) if isinstance(entity_hints, list) else ""
    preview  = summary[:_SUMMARY_PREVIEW_LEN] if summary else ""
    meta = f" nums={numeric_hits} kpis={kpi_hits}"
    if entity_preview:
        meta += f" entities=[{entity_preview}]"
    if section_path and section_path != title:
        meta += f" path={section_path}"
    if preview:
        return f"[{node_id}] {title} ({meta}) — {preview}"
    return f"[{node_id}] {title} ({meta})"


def _tokenize_query(query: str) -> List[str]:
    return [t for t in json.dumps(query).lower().replace('"', '').split() if len(t) >= 3]


def _query_entity_hints(query: str) -> List[str]:
    hints: List[str] = []
    for token in query.replace(',', ' ').split():
        u = token.upper()
        if u.startswith("RIG") or u.startswith("PUMP") or u.startswith("WELL") or u.startswith("COMPRESSOR"):
            hints.append(u)
    return hints


def _score_node_for_query(node: Dict, query: str) -> float:
    """Deterministic section-aware pre-ranking before LLM branch selection."""
    title = str(node.get("title", "")).lower()
    summary = str(node.get("summary", "")).lower()
    path = str(node.get("section_path", "")).lower()
    blob = " ".join([title, summary, path])

    score = 0.0
    for term in _tokenize_query(query):
        if term in title:
            score += 3.0
        if term in path:
            score += 1.5
        if term in summary:
            score += 1.0

    signals = node.get("signals", {}) if isinstance(node.get("signals"), dict) else {}
    numeric_hits = float(signals.get("numeric_hits", 0) or 0)
    kpi_hits = float(signals.get("kpi_hits", 0) or 0)
    entity_hints = signals.get("entity_hints", []) if isinstance(signals.get("entity_hints"), list) else []

    q = query.lower()
    numeric_intent = any(k in q for k in ["kpi", "metric", "%", "variance", "trend", "sigma", "cpk", "cost", "hours", "downtime"])
    if numeric_intent:
        score += min(3.0, numeric_hits / 10.0) + min(2.0, kpi_hits / 8.0)

    if entity_hints:
        q_entities = _query_entity_hints(query)
        for qe in q_entities:
            if any(qe in eh.upper() for eh in entity_hints):
                score += 3.0

    return score


def _pre_rank_nodes(query: str, nodes: List[Dict], shortlist: int = 8) -> List[Dict]:
    if len(nodes) <= shortlist:
        return nodes
    scored = sorted(nodes, key=lambda n: _score_node_for_query(n, query), reverse=True)
    return scored[:shortlist]


def _select_relevant_nodes(
    query: str,
    nodes: List[Dict],
    max_select: int = _MAX_BRANCHES,
) -> List[str]:
    """
    Use Gemini to select the most relevant node_ids from a list of siblings.
    Returns a list of node_id strings.
    """
    if not nodes:
        return []

    if len(nodes) == 1:
        return [nodes[0]["node_id"]]

    candidate_nodes = _pre_rank_nodes(query, nodes, shortlist=max(6, max_select * 3))
    sections_text = "\n".join(_node_preview(n) for n in candidate_nodes)

    prompt = (
        "You are navigating a document's table-of-contents tree to find "
        "the sections most relevant to a user's query.\n\n"
        f"Query: {query}\n\n"
        "Available sections (format: [node_id] Title — Summary):\n"
        f"{sections_text}\n\n"
        f"Select up to {max_select} node_ids that are most relevant to the query.\n"
        "Rules:\n"
        "  - Only return node_ids from the list above.\n"
        "  - Return fewer if fewer are relevant.\n"
        "  - Respond ONLY with a JSON array of strings, e.g. [\"0001\", \"0003\"].\n"
        "  - Do not include any explanation."
    )

    response  = gemini_call(prompt)
    parsed    = extract_json(response)

    if isinstance(parsed, list):
        allowed_ids = {str(n.get("node_id")) for n in candidate_nodes}
        filtered = [str(x) for x in parsed if str(x) in allowed_ids]
        if filtered:
            return filtered[:max_select]

    # Fallback: deterministic top-ranked shortlist when LLM fails
    logger.warning("_select_relevant_nodes: LLM returned unexpected format: %s", response[:200])
    return [n.get("node_id") for n in candidate_nodes[:max_select] if n.get("node_id")]


def _get_chunk_text(node: Dict, chunks: List[str]) -> str:
    """Extract raw text for a node's page range from the chunks list."""
    s = node.get("start_index")
    e = node.get("end_index")
    if s is None or e is None or not chunks:
        return ""
    # Convert 1-based indices to 0-based Python slice
    return "\n\n".join(chunks[s - 1 : e])


# ---------------------------------------------------------------------------
# Tree traversal
# ---------------------------------------------------------------------------

def _traverse(
    query: str,
    nodes: List[Dict],
    chunks: List[str],
    depth: int = 0,
    max_depth: int = _MAX_DEPTH,
    max_branches: int = _MAX_BRANCHES,
) -> List[str]:
    """
    Recursively traverse the tree, selecting relevant branches at each level.
    Returns collected text chunks from the selected leaf / near-leaf nodes.
    """
    if not nodes or depth >= max_depth:
        return [_get_chunk_text(n, chunks) for n in nodes if _get_chunk_text(n, chunks)]

    selected_ids = _select_relevant_nodes(query, nodes, max_branches)
    logger.info(
        "tree_search depth=%d: selected %d/%d nodes: %s",
        depth, len(selected_ids), len(nodes), selected_ids,
    )

    collected: List[str] = []

    id_to_node = {n.get("node_id"): n for n in nodes}
    for node_id in selected_ids:
        node = id_to_node.get(node_id)
        if node is None:
            continue

        children = node.get("nodes", [])

        if not children:
            # Leaf node — collect its text
            text = _get_chunk_text(node, chunks)
            if text:
                collected.append(text)
        else:
            # Internal node — recurse into children
            sub_results = _traverse(
                query, children, chunks,
                depth=depth + 1,
                max_depth=max_depth,
                max_branches=max_branches,
            )
            collected.extend(sub_results)

            # Also collect the parent's own intro text if it spans unique pages
            first_child_start = children[0].get("start_index", node.get("end_index"))
            intro_end = (first_child_start or 1) - 1
            if (node.get("start_index") or 1) <= intro_end:
                intro_chunks = [
                    chunks[i]
                    for i in range(
                        (node.get("start_index") or 1) - 1,
                        intro_end,
                    )
                    if i < len(chunks)
                ]
                if intro_chunks:
                    collected.append("\n\n".join(intro_chunks))

    return collected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_tree(
    query: str,
    tree: List[Dict[str, Any]],
    chunks: List[str],
    top_k: int = 5,
) -> List[str]:
    """
    Reasoning-based retrieval through the PageIndex tree.

    Parameters
    ----------
    query   : the user's question / analysis intent
    tree    : hierarchical tree returned by build_page_index()
    chunks  : the original text chunks (same order used to build the tree)
    top_k   : maximum number of chunks to return

    Returns
    -------
    List of relevant text chunks (may be fewer than top_k).
    """
    if not tree or not chunks:
        return chunks[:top_k]

    try:
        results = _traverse(query, tree, chunks)
    except Exception as exc:
        logger.error("search_tree traversal failed: %s — falling back to top chunks", exc)
        return chunks[:top_k]

    # Deduplicate while preserving order
    seen: set = set()
    unique: List[str] = []
    for item in results:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)

    return unique[:top_k]
