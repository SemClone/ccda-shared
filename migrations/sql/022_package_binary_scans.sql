-- Migration 022: Package Binary Scans
-- Stores binary detection results for packages
--
-- Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
-- All Rights Reserved.

CREATE TABLE IF NOT EXISTS package_binary_scans (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES tracked_packages(id) ON DELETE CASCADE,
    purl VARCHAR(500) NOT NULL,

    -- Scan source
    tarball_url TEXT,
    scan_source VARCHAR(50),  -- 'github_clone', 'tarball_download', 'local'

    -- Results
    binaries_found BOOLEAN DEFAULT FALSE,
    binary_count INTEGER DEFAULT 0,
    binary_files JSONB,  -- [{path, file_type, size_bytes, signature}]
    binary_signatures TEXT[],  -- ['ELF executable', 'Windows executable']

    -- Package metadata from scan
    file_count INTEGER,
    total_size_bytes BIGINT,
    scan_method VARCHAR(50),  -- 'basic', 'osslili', 'binarysniffer'

    -- License info (bonus from scan-tarball)
    license_files JSONB,  -- [{path, spdx_id, confidence}]
    copyrights TEXT[],    -- Copyright strings detected

    -- Metadata
    scanned_at TIMESTAMPTZ DEFAULT NOW(),
    scan_duration_ms INTEGER,
    error_message TEXT,

    UNIQUE(package_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_binary_scans_package ON package_binary_scans(package_id);
CREATE INDEX IF NOT EXISTS idx_binary_scans_found ON package_binary_scans(binaries_found) WHERE binaries_found = TRUE;
CREATE INDEX IF NOT EXISTS idx_binary_scans_date ON package_binary_scans(scanned_at);

-- Add comment for documentation
COMMENT ON TABLE package_binary_scans IS 'Binary detection results from ccda-cli scan-tarball for tracked packages';
COMMENT ON COLUMN package_binary_scans.binary_files IS 'JSON array of detected binary files with path, file_type, size_bytes, signature';
COMMENT ON COLUMN package_binary_scans.binary_signatures IS 'Unique binary signature types found (e.g., ELF executable, Windows executable)';
COMMENT ON COLUMN package_binary_scans.scan_method IS 'Tool used for scanning: basic, osslili, or binarysniffer';
