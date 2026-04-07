"""
GraphRAG Module
Advanced graph-based retrieval and reasoning for TransIQ

Provides:
- Entity resolution and deduplication  
- Knowledge graph construction and querying
- Graph analytics and reasoning
- Multi-hop relationship queries
- Entity linking and disambiguation
"""

from .entity_resolver import EntityResolver
from .graph_engine import KnowledgeGraphEngine
from .graph_analytics import GraphAnalytics
from .facts_to_graph import FactsToGraphConverter

__all__ = [
    "EntityResolver",
    "KnowledgeGraphEngine",
    "GraphAnalytics",
    "FactsToGraphConverter",
]

__version__ = "1.0.0"
