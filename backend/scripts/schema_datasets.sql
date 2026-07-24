-- datasets table: metadata for all analysis datasets (demo + user uploaded)
-- Stored in MySQL (business metadata), separate from DuckDB (analysis data)

CREATE TABLE IF NOT EXISTS datasets (
    id              VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    source_type     VARCHAR(32) NOT NULL,
    status          VARCHAR(32) DEFAULT 'ready',
    table_name      VARCHAR(128) NOT NULL UNIQUE,
    session_id      VARCHAR(64),
    row_count       INT DEFAULT 0,
    column_count    INT DEFAULT 0,
    columns_meta    JSON,
    profile_meta    JSON,
    original_file   VARCHAR(500),
    file_size_bytes BIGINT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_datasets_session (session_id),
    INDEX idx_datasets_status (status),
    INDEX idx_datasets_source (source_type)
);
