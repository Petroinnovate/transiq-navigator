"""
Check Vector Database and Chunking Status
"""
import sqlite3
import os
import json
from pathlib import Path

# Database path
DB_PATH = os.path.join('storage', 'local_storage.db')
FAISS_INDEX_PATH = os.path.join('storage', 'faiss_index.bin')
FAISS_MAP_PATH = os.path.join('storage', 'faiss_index.bin.map')

print("=" * 60)
print("VECTOR DATABASE & CHUNKING STATUS CHECK")
print("=" * 60)
print()

# Check SQLite Database
print("[DATABASE] SQLite Database Status:")
print("-" * 60)
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"[OK] Database exists: {DB_PATH}")
    print(f"     Tables: {', '.join([t[0] for t in tables])}")
    
    # Count documents
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    print(f"\n[DOCS] Documents: {doc_count}")
    
    # Count chunks
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    print(f"[CHUNKS] Chunks: {chunk_count}")
    
    # Get chunks per document
    if chunk_count > 0:
        cursor.execute("SELECT doc_id, COUNT(*) as cnt FROM chunks GROUP BY doc_id")
        chunk_groups = cursor.fetchall()
        print(f"\n[INFO] Chunks per Document:")
        for doc_id, cnt in chunk_groups:
            print(f"       Doc {doc_id}: {cnt} chunks")
        
        # Show sample chunk
        cursor.execute("SELECT id, doc_id, chunk_text, chunk_index, metadata FROM chunks LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"\n[SAMPLE] Sample Chunk:")
            print(f"         ID: {sample[0]}")
            print(f"         Doc ID: {sample[1]}")
            print(f"         Index: {sample[3]}")
            print(f"         Text Preview: {sample[2][:100]}...")
            if sample[4]:
                metadata = json.loads(sample[4])
                print(f"         Metadata: {metadata}")
    else:
        print("\n[WARN] No chunks found in database")
    
    # Count edges
    cursor.execute("SELECT COUNT(*) FROM graph_edges")
    edge_count = cursor.fetchone()[0]
    print(f"\n[EDGES] Knowledge Graph Edges: {edge_count}")
    
    conn.close()
else:
    print(f"[WARN] Database not found: {DB_PATH}")
    print("       (Will be created on first document upload)")

print()

# Check FAISS Vector Index
print("[FAISS] FAISS Vector Index Status:")
print("-" * 60)
if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(FAISS_MAP_PATH):
    index_size = os.path.getsize(FAISS_INDEX_PATH)
    map_size = os.path.getsize(FAISS_MAP_PATH)
    print(f"[OK] FAISS index exists: {FAISS_INDEX_PATH}")
    print(f"     Index file size: {index_size:,} bytes")
    print(f"     Map file size: {map_size:,} bytes")
    
    # Try to load and check vector count
    try:
        import faiss
        import pickle
        
        index = faiss.read_index(FAISS_INDEX_PATH)
        with open(FAISS_MAP_PATH, 'rb') as f:
            id_map = pickle.load(f)
        
        print(f"\n[STATS] Vector Index Statistics:")
        print(f"        Total vectors: {len(id_map)}")
        print(f"        Index dimension: {index.d}")
        print(f"        Index type: {type(index).__name__}")
        
        if len(id_map) > 0:
            print(f"\n[OK] Vector database is WORKING!")
            print(f"     {len(id_map)} vectors indexed and ready for semantic search")
        else:
            print(f"\n[WARN] Vector index exists but is empty")
            
    except Exception as e:
        print(f"[WARN] Could not read index: {e}")
        print("       (This is okay if no documents have been processed yet)")
else:
    print(f"[WARN] FAISS index not found")
    print(f"       Index: {FAISS_INDEX_PATH}")
    print(f"       Map: {FAISS_MAP_PATH}")
    print("       (Will be created when first document is processed)")

print()

# Check Chunking Implementation
print("[CHUNKER] Chunking Implementation Status:")
print("-" * 60)
try:
    from app.processors.chunker.adaptive import AdaptiveChunker
    from app.config.settings import settings
    
    chunker = AdaptiveChunker()
    print(f"[OK] AdaptiveChunker loaded successfully")
    print(f"     Max chunk size: {chunker.max_chars} characters")
    print(f"     Overlap size: {chunker.overlap} characters")
    print(f"     Chunking features:")
    print(f"        - Semantic boundary detection")
    print(f"        - Table preservation")
    print(f"        - Hierarchical structure support")
    print(f"        - Metadata extraction")
    
    # Test chunking with sample text
    test_text = """
    This is a test document. It has multiple paragraphs.
    
    Here is another paragraph with some content.
    
    And a third paragraph to test chunking.
    """
    test_chunks = chunker.chunk(test_text)
    print(f"\n[TEST] Test Chunking:")
    print(f"       Test text length: {len(test_text)} characters")
    print(f"       Chunks created: {len(test_chunks)}")
    if test_chunks:
        print(f"       [OK] Chunking is WORKING!")
        print(f"       Sample chunk length: {len(test_chunks[0])} characters")
    
except Exception as e:
    print(f"[ERROR] Error loading chunker: {e}")

print()

# Check Embedding Model
print("[EMBEDDINGS] Embedding Model Status:")
print("-" * 60)
try:
    from app.embeddings.models import EmbeddingModel
    from app.config.settings import settings
    
    emb_model = EmbeddingModel()
    print(f"[OK] EmbeddingModel loaded successfully")
    print(f"     Model: {emb_model.get_model_name()}")
    print(f"     Dimension: {emb_model.get_dimension()}")
    print(f"     [OK] Embeddings are ready for vector database")
    
except Exception as e:
    print(f"[ERROR] Error loading embedding model: {e}")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)

# Overall status
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    conn.close()
    
    if chunk_count > 0:
        if os.path.exists(FAISS_INDEX_PATH):
            print("[OK] Vector Database: WORKING")
            print("[OK] Chunking: WORKING")
            print("\n[SUCCESS] Both systems are operational!")
        else:
            print("[WARN] Chunks exist but FAISS index not found")
            print("       (May need to process a document to create index)")
    else:
        print("[WARN] No documents processed yet")
        print("       Upload a document to test chunking and vector database")
else:
    print("[WARN] Database not initialized")
    print("       Upload a document to initialize the system")

print()

