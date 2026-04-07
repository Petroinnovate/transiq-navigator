import time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.file_reader import read_file_content
from pipelines.processing.chunking.adaptive import AdaptiveChunker

pdf = './storage/uploads/71889348-21d3-4f91-90b3-80cf22f5dd1d.pdf'
t0 = time.time()
text = read_file_content(pdf)
print(f'read_file: {time.time()-t0:.3f}s  ({len(text):,} chars)')

chunker = AdaptiveChunker()
t1 = time.time()
chunks_data = chunker.chunk_with_metadata(text)
print(f'chunking:  {time.time()-t1:.3f}s  ({len(chunks_data)} chunks)')

from services.vector_store.embeddings.embedding_model import EmbeddingModel
chunks = [c['text'] for c in chunks_data]
emb = EmbeddingModel()
t2 = time.time()
embeddings = emb.embed(chunks, show_progress=False)
print(f'embedding: {time.time()-t2:.3f}s  ({len(chunks)} chunks)')
print(f'TOTAL (no LLM): {time.time()-t0:.2f}s')
