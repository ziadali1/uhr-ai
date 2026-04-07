-- Phase 4: Hybrid Search Index migration
-- Run once in Supabase SQL Editor (Dashboard > SQL Editor > New query)

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create search_index table
CREATE TABLE IF NOT EXISTS search_index (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT,
    source_name TEXT,
    entities TEXT,
    content_vector vector(1536),
    document_family TEXT,
    collection_date TEXT,
    document_subtype TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Index for fast user_id filtering
CREATE INDEX IF NOT EXISTS search_index_user_id_idx
    ON search_index (user_id);

-- 4. IVFFlat index for approximate vector similarity (cosine)
--    lists=100 is appropriate for up to ~1M rows
CREATE INDEX IF NOT EXISTS search_index_vector_idx
    ON search_index USING ivfflat (content_vector vector_cosine_ops)
    WITH (lists = 100);

-- 5. GIN index for Portuguese full-text search
CREATE INDEX IF NOT EXISTS search_index_fts_idx
    ON search_index USING gin(to_tsvector('portuguese', content));

-- 6. Hybrid search function (vector similarity + full-text via RRF)
--    Called via: client.rpc("hybrid_search", {...})
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(1536),
    user_filter TEXT,
    top_k INT DEFAULT 3,
    rrf_k INT DEFAULT 60
)
RETURNS TABLE(
    id TEXT,
    source_name TEXT,
    content TEXT,
    combined_score FLOAT
)
LANGUAGE SQL
STABLE
AS $$
    WITH vector_ranked AS (
        SELECT
            si.id,
            ROW_NUMBER() OVER (ORDER BY si.content_vector <=> query_embedding) AS rank
        FROM search_index si
        WHERE si.user_id = user_filter
          AND si.content_vector IS NOT NULL
        LIMIT 20
    ),
    fts_ranked AS (
        SELECT
            si.id,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank(
                    to_tsvector('portuguese', si.content),
                    plainto_tsquery('portuguese', query_text)
                ) DESC
            ) AS rank
        FROM search_index si
        WHERE si.user_id = user_filter
          AND to_tsvector('portuguese', si.content)
              @@ plainto_tsquery('portuguese', query_text)
        LIMIT 20
    ),
    rrf_combined AS (
        SELECT
            COALESCE(v.id, f.id) AS id,
            COALESCE(1.0 / (rrf_k + v.rank), 0.0)
            + COALESCE(1.0 / (rrf_k + f.rank), 0.0) AS score
        FROM vector_ranked v
        FULL OUTER JOIN fts_ranked f ON v.id = f.id
    )
    SELECT si.id, si.source_name, si.content, rrf.score AS combined_score
    FROM rrf_combined rrf
    JOIN search_index si ON si.id = rrf.id
    ORDER BY rrf.score DESC
    LIMIT top_k;
$$;

-- 7. Full-text-only fallback (used when no query_embedding provided)
CREATE OR REPLACE FUNCTION fts_search(
    query_text TEXT,
    user_filter TEXT,
    top_k INT DEFAULT 3
)
RETURNS TABLE(
    id TEXT,
    source_name TEXT,
    content TEXT,
    combined_score FLOAT
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        si.id,
        si.source_name,
        si.content,
        ts_rank(
            to_tsvector('portuguese', si.content),
            plainto_tsquery('portuguese', query_text)
        )::FLOAT AS combined_score
    FROM search_index si
    WHERE si.user_id = user_filter
      AND to_tsvector('portuguese', si.content)
          @@ plainto_tsquery('portuguese', query_text)
    ORDER BY combined_score DESC
    LIMIT top_k;
$$;
