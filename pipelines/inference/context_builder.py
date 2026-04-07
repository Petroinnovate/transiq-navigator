"""
Minimal context builder for Stage 1 prompt reduction.

V1 behavior:
- Split content into blocks using double newlines
- Score blocks using simple keyword and pattern checks
- Select merged groups of neighboring high-signal blocks
- Build final output from full blocks only
- Stop before exceeding max_output_chars
"""
from __future__ import annotations

from typing import List, Set, Tuple


_UNIT_MARKERS = ["%", "$", "bbl", "psi", "mcf", "ft", "hrs", "days"]
_ANOMALY_WORDS = ["defect", "downtime", "variance", "failure"]
_TOP_BLOCK_COUNT = 14
_MIN_BLOCK_SCORE = 2
_MAX_GROUP_CHARS = 3000
_COVERAGE_BUDGET_RATIO = 0.50


def split_into_blocks(content: str) -> List[str]:
    blocks = []
    for block in content.split("\n\n"):
        cleaned = block.strip()
        if cleaned:
            blocks.append(cleaned)
    return blocks


def normalize_block(block: str) -> str:
    return " ".join(block.lower().split())


def score_block(block: str) -> int:
    lowered = block.lower()
    score = 0

    if any(char.isdigit() for char in block):
        score += 2

    if any(unit in lowered for unit in _UNIT_MARKERS):
        score += 2

    if any(word in lowered for word in _ANOMALY_WORDS):
        score += 2

    if len(block) > 50:
        score += 1

    return score


def _has_digits(block: str) -> bool:
    return any(char.isdigit() for char in block)


def _has_weak_signal(block: str) -> bool:
    return len(block) >= 80 or ":" in block or "- " in block


def _neighbor_allowed(index: int, blocks: List[str], scores: List[int]) -> bool:
    return scores[index] >= 1 or _has_digits(blocks[index]) or _has_weak_signal(blocks[index])


def _group_char_length(indexes: List[int], blocks: List[str]) -> int:
    return len("\n\n".join(blocks[index] for index in indexes))


def _build_candidate_group(anchor_index: int, blocks: List[str], scores: List[int]) -> List[int]:
    group = {anchor_index}
    if anchor_index - 1 >= 0 and _neighbor_allowed(anchor_index - 1, blocks, scores):
        group.add(anchor_index - 1)
    if anchor_index + 1 < len(blocks) and _neighbor_allowed(anchor_index + 1, blocks, scores):
        group.add(anchor_index + 1)
    return sorted(group)


def _merge_selected_groups(groups: List[List[int]], blocks: List[str]) -> List[List[int]]:
    merged_groups: List[List[int]] = []

    for group in sorted(groups, key=lambda candidate: candidate[0]):
        if not merged_groups:
            merged_groups.append(group)
            continue

        previous = merged_groups[-1]
        if set(previous).isdisjoint(group):
            merged_groups.append(group)
            continue

        merged = sorted(set(previous).union(group))
        if _group_char_length(merged, blocks) <= _MAX_GROUP_CHARS:
            merged_groups[-1] = merged
            continue

        merged_groups.append(group)

    return merged_groups


def _dedupe_blocks(blocks: List[str]) -> List[str]:
    deduped_blocks: List[str] = []
    seen_blocks: Set[str] = set()

    for block in blocks:
        normalized = normalize_block(block)
        if normalized in seen_blocks:
            continue
        seen_blocks.add(normalized)
        deduped_blocks.append(block)

    return deduped_blocks


def _best_anchor_from_group(group_indexes: List[int], scores: List[int]) -> int:
    return max(group_indexes, key=lambda index: (scores[index], -index))


def _group_overlaps(group_indexes: List[int], covered_indexes: Set[int]) -> bool:
    return any(index in covered_indexes for index in group_indexes)


def select_blocks(blocks: List[str], max_output_chars: int = 150000) -> str:
    if not blocks:
        return ""

    scores = [score_block(block) for block in blocks]
    anchors = [index for index, score in enumerate(scores) if score >= _MIN_BLOCK_SCORE]

    # === Phase 5: secondary anchors for numeric blocks ===
    for index, score in enumerate(scores):
        if score == 1 and any(char.isdigit() for char in blocks[index]):
            if index not in anchors:
                anchors.append(index)
    anchors.sort()

    if not anchors:
        first_block = blocks[0]
        return first_block if len(first_block) <= max_output_chars else ""

    group_data: List[Tuple[List[int], int, int, float]] = []
    for anchor_index in anchors:
        candidate_indexes = _build_candidate_group(anchor_index, blocks, scores)
        group_score = max(scores[index] for index in candidate_indexes)
        group_chars = max(_group_char_length(candidate_indexes, blocks), 1)
        group_efficiency = group_score / group_chars
        group_data.append((candidate_indexes, group_score, group_chars, group_efficiency))

    group_data.sort(key=lambda item: (-item[3], -item[1], item[2]))

    selected_groups: List[List[int]] = []
    selected_group_keys: Set[Tuple[int, ...]] = set()
    covered_indexes: Set[int] = set()
    total_chars = 0
    coverage_budget = int(max_output_chars * _COVERAGE_BUDGET_RATIO)

    for candidate_indexes, _, group_chars, _ in group_data:
        if len(selected_groups) >= _TOP_BLOCK_COUNT:
            break
        if total_chars + group_chars > coverage_budget:
            continue
        if _group_overlaps(candidate_indexes, covered_indexes):
            continue

        selected_groups.append(candidate_indexes)
        selected_group_keys.add(tuple(candidate_indexes))
        covered_indexes.update(candidate_indexes)
        total_chars += group_chars

    for candidate_indexes, _, group_chars, _ in group_data:
        if len(selected_groups) >= _TOP_BLOCK_COUNT:
            break
        if tuple(candidate_indexes) in selected_group_keys:
            continue
        if total_chars + group_chars > max_output_chars:
            continue

        selected_groups.append(candidate_indexes)
        selected_group_keys.add(tuple(candidate_indexes))
        total_chars += group_chars

    if not selected_groups and group_data:
        fallback_group = group_data[0][0]
        selected_groups.append([_best_anchor_from_group(fallback_group, scores)])

    merged_groups = _merge_selected_groups(selected_groups, blocks)
    flattened_indexes: List[int] = []
    seen_indexes: Set[int] = set()

    for group in merged_groups:
        for index in group:
            if index in seen_indexes:
                continue
            seen_indexes.add(index)
            flattened_indexes.append(index)

    final_blocks = [blocks[index] for index in flattened_indexes]
    return "\n\n".join(_dedupe_blocks(final_blocks))


def build_context(content: str, max_output_chars: int = 150000) -> str:
    blocks = split_into_blocks(content)
    target_budget = min(max_output_chars, int(len(content) * 0.80))
    return select_blocks(blocks, max_output_chars=target_budget)
