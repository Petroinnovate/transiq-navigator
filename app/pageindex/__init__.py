"""
app.pageindex — PageIndex integration for TransIQ.

Adapted from VectifyAI/PageIndex (MIT licence).
https://github.com/VectifyAI/PageIndex

Only the parts required by this project are included:
  • tree_builder : build a hierarchical tree index from text chunks (using Gemini)
  • tree_search  : reasoning-based retrieval through the tree (using Gemini)
  • llm_adapter  : Gemini wrappers replacing the original OpenAI calls
"""

from .tree_builder import build_page_index
from .tree_search import search_tree

__all__ = ["build_page_index", "search_tree"]
