-- ============================================
-- TransIQ Backend - Supabase Schema
-- Vector Storage for Document Chunks
-- ============================================

-- Enable pgvector extension (run this first as superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- DOCUMENTS TABLE
-- Stores metadata about uploaded documents
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL, -- pdf, xlsx, csv, etc.
    file_size INTEGER NOT NULL, -- in bytes
    original_file_path TEXT, -- Path in Supabase Storage
    total_chunks INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processing', -- processing, completed, failed
    metadata JSONB DEFAULT '{}', -- Additional metadata (page count, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT valid_status CHECK (status IN ('processing', 'completed', 'failed'))
);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_status ON documents(status);


-- ============================================
-- DOCUMENT_CHUNKS TABLE
-- Stores text chunks with vector embeddings
-- ============================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL, -- Order of chunk in document
    embedding VECTOR(384), -- Sentence-transformers all-MiniLM-L6-v2 = 384 dimensions
    -- For OpenAI text-embedding-3-small use VECTOR(1536)
    -- For Google's embedding models, adjust dimension accordingly
    
    metadata JSONB DEFAULT '{}', -- {page_num, section, source_type, etc}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_chunk_per_document UNIQUE(document_id, chunk_index)
);

-- Indexes for efficient querying
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_chunk_index ON document_chunks(chunk_index);

-- Vector similarity search index (IMPORTANT for performance)
-- Using IVFFlat for approximate nearest neighbor search
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Alternative: HNSW index (better accuracy, slower inserts)
-- CREATE INDEX idx_chunks_embedding ON document_chunks 
-- USING hnsw (embedding vector_cosine_ops);


-- ============================================
-- INSIGHTS TABLE
-- Traceability-first insights storage
-- ============================================
CREATE TABLE IF NOT EXISTS insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    insight_id TEXT NOT NULL,
    insight_text TEXT,
    insight_type TEXT,
    source_pages INT[] NOT NULL,
    source_chunks INT[] DEFAULT '{}',
    supporting_groups TEXT[] DEFAULT '{}',
    group_title TEXT,
    section_title TEXT,
    confidence FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_insight_per_document UNIQUE(document_id, insight_id),
    CONSTRAINT check_source_pages_not_empty CHECK (array_length(source_pages, 1) > 0)
);

CREATE INDEX idx_insights_document_id ON insights(document_id);
CREATE INDEX idx_insights_insight_id ON insights(insight_id);
CREATE INDEX idx_insights_source_pages_gin ON insights USING GIN (source_pages);
CREATE INDEX idx_insights_metadata_gin ON insights USING GIN (metadata);


-- ============================================
-- RIG_SUMMARIES TABLE
-- Aggregation-layer summaries for final synthesis
-- ============================================
CREATE TABLE IF NOT EXISTS rig_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    rig_id TEXT NOT NULL,
    rig_title TEXT,
    source_pages INT[] NOT NULL,
    source_section_ids TEXT[] DEFAULT '{}',
    summary TEXT,
    findings JSONB DEFAULT '[]',
    kpis JSONB DEFAULT '[]',
    risks JSONB DEFAULT '[]',
    confidence FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_rig_summary_per_document UNIQUE(document_id, rig_id),
    CONSTRAINT check_rig_source_pages_not_empty CHECK (array_length(source_pages, 1) > 0)
);

CREATE INDEX idx_rig_summaries_document_id ON rig_summaries(document_id);
CREATE INDEX idx_rig_summaries_rig_id ON rig_summaries(rig_id);
CREATE INDEX idx_rig_summaries_source_pages_gin ON rig_summaries USING GIN (source_pages);


-- ============================================
-- STORAGE BUCKET
-- For storing original uploaded files
-- ============================================
-- Run this in Supabase Dashboard or via API:
-- INSERT INTO storage.buckets (id, name, public) 
-- VALUES ('documents', 'documents', false);

-- Storage policies (RLS)
-- Allow authenticated users to upload their own files
CREATE POLICY "Users can upload their own documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Allow users to read their own files
CREATE POLICY "Users can read their own documents"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Allow users to delete their own files
CREATE POLICY "Users can delete their own documents"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);


-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on documents table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Users can only see their own documents
CREATE POLICY "Users can view their own documents"
ON documents FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Users can insert their own documents
CREATE POLICY "Users can insert their own documents"
ON documents FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Users can update their own documents
CREATE POLICY "Users can update their own documents"
ON documents FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can delete their own documents
CREATE POLICY "Users can delete their own documents"
ON documents FOR DELETE
TO authenticated
USING (auth.uid() = user_id);


-- Enable RLS on document_chunks table
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Users can view chunks from their own documents
CREATE POLICY "Users can view chunks from their documents"
ON document_chunks FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM documents 
        WHERE documents.id = document_chunks.document_id 
        AND documents.user_id = auth.uid()
    )
);

-- Users can insert chunks for their own documents
CREATE POLICY "Users can insert chunks for their documents"
ON document_chunks FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM documents 
        WHERE documents.id = document_chunks.document_id 
        AND documents.user_id = auth.uid()
    )
);

-- Users can delete chunks from their own documents
CREATE POLICY "Users can delete chunks from their documents"
ON document_chunks FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM documents 
        WHERE documents.id = document_chunks.document_id 
        AND documents.user_id = auth.uid()
    )
);


-- Enable RLS on insights table
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view insights from their documents"
ON insights FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM documents
        WHERE documents.id = insights.document_id
        AND documents.user_id = auth.uid()
    )
);

CREATE POLICY "Users can insert insights for their documents"
ON insights FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM documents
        WHERE documents.id = insights.document_id
        AND documents.user_id = auth.uid()
    )
);


-- Enable RLS on rig_summaries table
ALTER TABLE rig_summaries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view rig summaries from their documents"
ON rig_summaries FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM documents
        WHERE documents.id = rig_summaries.document_id
        AND documents.user_id = auth.uid()
    )
);

CREATE POLICY "Users can insert rig summaries for their documents"
ON rig_summaries FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM documents
        WHERE documents.id = rig_summaries.document_id
        AND documents.user_id = auth.uid()
    )
);


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to search for similar chunks using vector similarity
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding VECTOR(384),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    chunk_text TEXT,
    chunk_index INTEGER,
    similarity FLOAT,
    metadata JSONB,
    file_name TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id AS chunk_id,
        dc.document_id,
        dc.chunk_text,
        dc.chunk_index,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        dc.metadata,
        d.file_name,
        dc.created_at
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    WHERE 
        (filter_user_id IS NULL OR d.user_id = filter_user_id)
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at on documents
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- ANALYTICS VIEWS (Optional)
-- ============================================

-- View for document statistics per user
CREATE OR REPLACE VIEW user_document_stats AS
SELECT 
    d.user_id,
    COUNT(DISTINCT d.id) AS total_documents,
    COUNT(dc.id) AS total_chunks,
    SUM(d.file_size) AS total_storage_bytes,
    MAX(d.created_at) AS last_upload,
    json_agg(DISTINCT d.file_type) AS file_types_used
FROM documents d
LEFT JOIN document_chunks dc ON dc.document_id = d.id
GROUP BY d.user_id;


-- ============================================
-- SAMPLE QUERIES
-- ============================================

-- Search for similar chunks (example usage)
-- SELECT * FROM search_similar_chunks(
--     '[0.1, 0.2, ..., 0.384]'::vector(384),  -- query embedding
--     0.7,  -- similarity threshold
--     5,    -- max results
--     'user-uuid-here'  -- filter by user
-- );

-- Get all chunks for a document
-- SELECT * FROM document_chunks 
-- WHERE document_id = 'document-uuid-here' 
-- ORDER BY chunk_index;

-- Get document with chunk count
-- SELECT d.*, COUNT(dc.id) as chunk_count
-- FROM documents d
-- LEFT JOIN document_chunks dc ON dc.document_id = d.id
-- WHERE d.user_id = 'user-uuid-here'
-- GROUP BY d.id
-- ORDER BY d.created_at DESC;
