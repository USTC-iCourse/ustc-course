-- Migration script to add search_tokens table for DoS protection
-- Run this SQL script on your database before deploying the search token feature

CREATE TABLE IF NOT EXISTS search_tokens (
    token VARCHAR(64) PRIMARY KEY,
    created_at DATETIME NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address VARCHAR(45),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: Clean up any old tokens (older than 24 hours) on initial setup
-- DELETE FROM search_tokens WHERE created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR);

