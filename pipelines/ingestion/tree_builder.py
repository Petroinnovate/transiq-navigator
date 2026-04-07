"""
PageIndex tree builder — adapted from VectifyAI/PageIndex (MIT licence).
https://github.com/VectifyAI/PageIndex

Only the path required by this project is included:
  • No explicit-TOC detection (skip process_toc_with/without_page_numbers)
  • No verification / fix-incorrect-toc retries
  • No OpenAI dependency — all LLM calls route through app.pageindex.llm_adapter (Gemini)
  • Works on a List[str] of text chunks (treated as pages)

Public API
----------
  build_page_index(chunks, add_summaries=False) -> List[dict]
      Builds a hierarchical tree index from a list of text chunks.
      Each node in the tree has:
          title        : section heading
          node_id      : zero-padded sequential id  (e.g. "0003")
          start_index  : 1-based chunk index where section starts
          end_index    : 1-based chunk index where section ends (inclusive)
          summary      : (optional) LLM-generated description
          nodes        : child nodes (same schema, recursive)
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from .llm_adapter import (
    count_tokens,
    extract_json,
    gemini_call,
    gemini_call_async,
    gemini_call_with_finish_reason,
)

logger = logging.getLogger(__name__)

# Defaults that mirror PageIndex config.yaml
_MAX_TOKENS_PER_GROUP  = 20_000   # tokens per page-group sent to LLM
_MAX_PAGE_NUM_PER_NODE = 10       # split node if it spans more pages than this
_MAX_TOKEN_NUM_PER_NODE = 20_000  # split node if it has more tokens than this

_NUMERIC_RE = re.compile(r"\b\d+(?:\.\d+)?(?:%|\s?(?:hrs?|hours?|days?|usd|\$|bbl|psi|barrels?))?\b", re.IGNORECASE)
_KPI_TERM_RE = re.compile(
    r"\b(kpi|efficiency|uptime|downtime|mtbf|mttr|npt|oee|cost|capex|opex|throughput|yield|pressure|temperature|variance|sigma|cpk)\b",
    re.IGNORECASE,
)
_ENTITY_RE = re.compile(r"\b(?:RIG[-_\s]?\d+|PUMP[-_\s]?[A-Z0-9]+|WELL[-_\s]?[A-Z0-9]+|COMPRESSOR[-_\s]?[A-Z0-9]+)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Low-level helpers (ported from PageIndex/pageindex/utils.py)
# ---------------------------------------------------------------------------

def _page_list_to_group_text(
    page_contents: List[str],
    token_lengths: List[int],
    max_tokens: int = _MAX_TOKENS_PER_GROUP,
    overlap_page: int = 1,
) -> List[str]:
    """Merge consecutive pages into groups that fit within max_tokens."""
    total = sum(token_lengths)
    if total <= max_tokens:
        return ["".join(page_contents)]

    subsets: List[str] = []
    current: List[str] = []
    current_tokens = 0

    expected_parts  = math.ceil(total / max_tokens)
    avg_per_part    = math.ceil(((total / expected_parts) + max_tokens) / 2)

    for i, (page_text, page_tokens) in enumerate(zip(page_contents, token_lengths)):
        if current_tokens + page_tokens > avg_per_part:
            subsets.append("".join(current))
            overlap_start = max(i - overlap_page, 0)
            current       = page_contents[overlap_start:i]
            current_tokens = sum(token_lengths[overlap_start:i])
        current.append(page_text)
        current_tokens += page_tokens

    if current:
        subsets.append("".join(current))

    logger.info("_page_list_to_group_text: split into %d groups", len(subsets))
    return subsets


def _convert_physical_index_to_int(data):
    """Convert '<physical_index_X>' strings to int throughout a flat list."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "physical_index" in item:
                v = item["physical_index"]
                if isinstance(v, str):
                    if v.startswith("<physical_index_"):
                        item["physical_index"] = int(
                            v.split("_")[-1].rstrip(">").strip()
                        )
                    elif v.startswith("physical_index_"):
                        item["physical_index"] = int(v.split("_")[-1].strip())
    elif isinstance(data, str):
        if data.startswith("<physical_index_"):
            return int(data.split("_")[-1].rstrip(">").strip())
        elif data.startswith("physical_index_"):
            return int(data.split("_")[-1].strip())
    return data


def _validate_and_truncate(
    toc: List[Dict], page_list_length: int, start_index: int = 1
) -> List[Dict]:
    """Remove TOC items whose physical_index exceeds document length."""
    max_allowed = page_list_length + start_index - 1
    for item in toc:
        if item.get("physical_index") is not None:
            if item["physical_index"] > max_allowed:
                logger.warning(
                    "Removed '%s' (physical_index %d > max %d)",
                    item.get("title"), item["physical_index"], max_allowed,
                )
                item["physical_index"] = None
    return toc


def _add_preface_if_needed(data: List[Dict]) -> List[Dict]:
    """Insert a Preface node if the first section does not start at chunk 1."""
    if data and data[0].get("physical_index") is not None and data[0]["physical_index"] > 1:
        data.insert(0, {"structure": "0", "title": "Preface", "physical_index": 1})
    return data


def _list_to_tree(flat: List[Dict]) -> List[Dict]:
    """Convert a flat [{structure, title, start_index, end_index}, ...] into a tree."""

    def _parent_structure(s):
        if not s:
            return None
        parts = str(s).split(".")
        return ".".join(parts[:-1]) if len(parts) > 1 else None

    nodes: Dict[str, Dict] = {}
    roots: List[Dict] = []

    for item in flat:
        structure = item.get("structure")
        node = {
            "title":       item.get("title"),
            "start_index": item.get("start_index"),
            "end_index":   item.get("end_index"),
            "nodes":       [],
        }
        nodes[structure] = node
        parent = _parent_structure(structure)
        if parent and parent in nodes:
            nodes[parent]["nodes"].append(node)
        else:
            roots.append(node)

    def _clean(node):
        if not node["nodes"]:
            del node["nodes"]
        else:
            for child in node["nodes"]:
                _clean(child)
        return node

    return [_clean(n) for n in roots]


def _post_processing(flat: List[Dict], end_physical_index: int) -> List[Dict]:
    """
    Assign start_index / end_index to every item in the flat TOC list,
    then build the hierarchical tree.
    """
    for i, item in enumerate(flat):
        item["start_index"] = item.get("physical_index")
        if i < len(flat) - 1:
            # Use next item's physical_index as end
            item["end_index"] = flat[i + 1]["physical_index"]
        else:
            item["end_index"] = end_physical_index

    tree = _list_to_tree(flat)
    if tree:
        return tree

    # Fallback: return flat list cleaned up
    for node in flat:
        node.pop("appear_start", None)
        node.pop("physical_index", None)
    return flat


def _structure_to_list(structure) -> List[Dict]:
    """Flatten tree back to a list (depth-first)."""
    if isinstance(structure, dict):
        nodes = [structure]
        if "nodes" in structure:
            nodes.extend(_structure_to_list(structure["nodes"]))
        return nodes
    elif isinstance(structure, list):
        result = []
        for item in structure:
            result.extend(_structure_to_list(item))
        return result
    return []


def _write_node_id(data, node_id: int = 0) -> int:
    """Assign sequential zero-padded node_ids depth-first."""
    if isinstance(data, dict):
        data["node_id"] = str(node_id).zfill(4)
        node_id += 1
        if "nodes" in data:
            node_id = _write_node_id(data["nodes"], node_id)
    elif isinstance(data, list):
        for item in data:
            node_id = _write_node_id(item, node_id)
    return node_id


def _add_node_text(node, page_list: List[Tuple[str, int]]):
    """Attach raw text for each node's page range."""
    if isinstance(node, dict):
        s = node.get("start_index")
        e = node.get("end_index")
        if s is not None and e is not None:
            node["text"] = "".join(p[0] for p in page_list[s - 1 : e])
        if "nodes" in node:
            _add_node_text(node["nodes"], page_list)
    elif isinstance(node, list):
        for item in node:
            _add_node_text(item, page_list)


def _annotate_node_signals(node, parent_titles: Optional[List[str]] = None):
    """Attach section-aware, numeric, KPI and entity hints for reasoning retrieval."""
    if parent_titles is None:
        parent_titles = []

    if isinstance(node, dict):
        title = node.get("title", "")
        text = node.get("text", "")
        title_tokens = title[:300]
        body = (text or "")[:20_000]
        combined = f"{title_tokens}\n{body}"

        entities = sorted(set(m.group(0) for m in _ENTITY_RE.finditer(combined)))[:20]
        node["signals"] = {
            "numeric_hits": len(_NUMERIC_RE.findall(combined)),
            "kpi_hits": len(_KPI_TERM_RE.findall(combined)),
            "entity_hints": entities,
        }
        path_parts = parent_titles + ([title] if title else [])
        node["section_path"] = " > ".join(path_parts)

        children = node.get("nodes", [])
        if children:
            for child in children:
                _annotate_node_signals(child, path_parts)
    elif isinstance(node, list):
        for item in node:
            _annotate_node_signals(item, parent_titles)


def _remove_node_text(data):
    if isinstance(data, dict):
        data.pop("text", None)
        if "nodes" in data:
            _remove_node_text(data["nodes"])
    elif isinstance(data, list):
        for item in data:
            _remove_node_text(item)
    return data


async def _generate_node_summary(node: Dict, model: str = None) -> str:
    text = node.get("text", "")[:8000]  # cap context
    prompt = (
        "You are given a part of a document. "
        "Generate a concise one-paragraph description of the main points covered.\n\n"
        f"Document Text:\n{text}\n\n"
        "Directly return the description, nothing else."
    )
    return await gemini_call_async(prompt)


async def _generate_summaries(structure, model: str = None):
    """Add 'summary' field to every node concurrently."""
    nodes = _structure_to_list(structure)
    # Only nodes that have text
    nodes_with_text = [n for n in nodes if n.get("text")]
    if not nodes_with_text:
        return structure

    tasks    = [_generate_node_summary(n, model) for n in nodes_with_text]
    summaries = await asyncio.gather(*tasks)
    for node, summary in zip(nodes_with_text, summaries):
        node["summary"] = summary
    return structure


# ---------------------------------------------------------------------------
# Core LLM-based TOC generation (ported from PageIndex/pageindex/page_index.py)
# ---------------------------------------------------------------------------

def _generate_toc_init(part: str) -> List[Dict]:
    """Ask Gemini to extract a flat TOC from the first page group."""
    prompt = (
        "You are an expert in extracting hierarchical tree structures.\n"
        "Your task is to generate the tree structure (table of contents) of the document.\n\n"
        "Rules:\n"
        "- 'structure' is the numeric hierarchy: first section = '1', "
        "  first subsection = '1.1', second subsection = '1.2', etc.\n"
        "- 'title' is the original heading text (fix spacing only).\n"
        "- The text contains tags <physical_index_X> … <physical_index_X> "
        "  marking the start/end of page X. Extract 'physical_index' as "
        "  the start page of each section, keeping '<physical_index_X>' format.\n\n"
        "Response format (JSON array, nothing else):\n"
        "[\n"
        "  {\"structure\": \"1\", \"title\": \"Section Title\", "
        "\"physical_index\": \"<physical_index_X>\"},\n"
        "  ...\n"
        "]\n\n"
        f"Given text:\n{part}"
    )
    response, finish_reason = gemini_call_with_finish_reason(prompt)
    result = extract_json(response)
    if not isinstance(result, list):
        logger.warning("_generate_toc_init: unexpected result type %s", type(result))
        result = []
    return result


def _generate_toc_continue(toc_content: List[Dict], part: str) -> List[Dict]:
    """Extend an existing flat TOC with content from the next page group."""
    prompt = (
        "You are an expert in extracting hierarchical tree structures.\n"
        "You are given the tree structure of a previous part and the text of the current part.\n"
        "Continue the tree structure to include the current part.\n\n"
        "Rules (same as before):\n"
        "- 'structure' uses numeric hierarchy (1, 1.1, 1.2, 2, ...).\n"
        "- Keep the '<physical_index_X>' format for physical_index.\n"
        "- Directly return the ADDITIONAL entries only (not the previous ones).\n\n"
        "Response format (JSON array, nothing else):\n"
        "[\n"
        "  {\"structure\": \"X\", \"title\": \"...\", "
        "\"physical_index\": \"<physical_index_X>\"},\n"
        "  ...\n"
        "]\n\n"
        f"Given text:\n{part}\n\n"
        f"Previous tree structure:\n{json.dumps(toc_content, indent=2)}"
    )
    response, _ = gemini_call_with_finish_reason(prompt)
    result = extract_json(response)
    if not isinstance(result, list):
        return []
    return result


def _process_no_toc(
    page_list: List[Tuple[str, int]],
    start_index: int = 1,
) -> List[Dict]:
    """
    Build a flat TOC entirely from the document content (no existing TOC).
    Corresponds to PageIndex's process_no_toc + meta_processor path.
    """
    page_contents  = []
    token_lengths  = []

    for idx, (text, tokens) in enumerate(page_list):
        page_num  = idx + start_index
        page_text = (
            f"<physical_index_{page_num}>\n{text}\n"
            f"<physical_index_{page_num}>\n\n"
        )
        page_contents.append(page_text)
        token_lengths.append(tokens)

    groups = _page_list_to_group_text(page_contents, token_lengths)
    logger.info("_process_no_toc: %d page groups", len(groups))

    toc = _generate_toc_init(groups[0])
    for group in groups[1:]:
        additional = _generate_toc_continue(toc, group)
        toc.extend(additional)

    _convert_physical_index_to_int(toc)
    logger.info("_process_no_toc: flat TOC has %d entries", len(toc))
    return toc


# ---------------------------------------------------------------------------
# Recursive large-node splitting (ported from PageIndex)
# ---------------------------------------------------------------------------

async def _process_large_node_recursively(
    node: Dict,
    page_list: List[Tuple[str, int]],
    max_page_num: int  = _MAX_PAGE_NUM_PER_NODE,
    max_token_num: int = _MAX_TOKEN_NUM_PER_NODE,
):
    """Split nodes that span too many pages/tokens into sub-nodes."""
    s, e = node.get("start_index", 1), node.get("end_index", len(page_list))
    node_pages  = page_list[s - 1 : e]
    token_count = sum(p[1] for p in node_pages)

    if (e - s) > max_page_num and token_count >= max_token_num:
        logger.info(
            "Splitting large node '%s' (pages %d-%d, %d tokens)",
            node.get("title"), s, e, token_count,
        )
        sub_toc = _process_no_toc(node_pages, start_index=s)
        sub_toc = [item for item in sub_toc if item.get("physical_index") is not None]
        sub_toc = _validate_and_truncate(sub_toc, len(node_pages), start_index=s)
        if sub_toc:
            # Don't duplicate the parent title
            if sub_toc[0]["title"].strip() == node["title"].strip():
                sub_toc = sub_toc[1:]
            if sub_toc:
                node["nodes"] = _post_processing(sub_toc, e)
                node["end_index"] = sub_toc[0].get("start_index", s)

    if "nodes" in node and node["nodes"]:
        tasks = [
            _process_large_node_recursively(child, page_list, max_page_num, max_token_num)
            for child in node["nodes"]
        ]
        await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_page_index(
    chunks: List[str],
    add_summaries: bool = False,
) -> List[Dict[str, Any]]:
    """
    Build a PageIndex hierarchical tree from a list of text chunks.

    Parameters
    ----------
    chunks       : list of text strings (treated as pages / logical sections)
    add_summaries: if True, generates an LLM summary for every tree node
                   (makes one extra Gemini call per node — use sparingly)

    Returns
    -------
    List of root-level tree nodes, each with:
        title, node_id, start_index, end_index, [summary], [nodes]
    """
    if not chunks:
        return []

    # Build internal page_list format
    page_list: List[Tuple[str, int]] = [
        (chunk, count_tokens(chunk)) for chunk in chunks
    ]

    # --- Step 1: Build flat TOC via LLM ---
    flat_toc = _process_no_toc(page_list)

    # Remove entries without a valid physical_index
    flat_toc = [item for item in flat_toc if item.get("physical_index") is not None]
    flat_toc = _validate_and_truncate(flat_toc, len(page_list))
    flat_toc = _add_preface_if_needed(flat_toc)

    if not flat_toc:
        logger.warning("build_page_index: LLM returned empty TOC; falling back to single root")
        return [{
            "title":       "Document",
            "node_id":     "0000",
            "start_index": 1,
            "end_index":   len(chunks),
        }]

    # --- Step 2: Convert to hierarchical tree ---
    tree = _post_processing(flat_toc, len(page_list))

    # --- Step 3: Recursively split oversized nodes ---
    async def _split_all():
        tasks = [_process_large_node_recursively(node, page_list) for node in tree]
        await asyncio.gather(*tasks)

    asyncio.run(_split_all())

    # --- Step 4: Annotate nodes ---
    _write_node_id(tree)
    _add_node_text(tree, page_list)
    _annotate_node_signals(tree)

    if add_summaries:
        asyncio.run(_generate_summaries(tree))

    _remove_node_text(tree)

    logger.info(
        "build_page_index: tree has %d root nodes, %d total nodes",
        len(tree),
        len(_structure_to_list(tree)),
    )
    return tree
