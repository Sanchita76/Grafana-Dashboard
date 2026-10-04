CREATE TABLE IF NOT EXISTS access_logs (
    ts           TIMESTAMPTZ NOT NULL,
    ip           TEXT,
    method       TEXT,
    path         TEXT,
    protocol     TEXT,
    status       INTEGER,
    status_class TEXT,        -- '2xx', '3xx', '4xx', '5xx'
    bytes        BIGINT,
    referrer     TEXT,
    user_agent   TEXT,
    browser      TEXT,
    os           TEXT,
    device       TEXT,
    traffic_type TEXT         -- 'human', 'bot', 'unknown'
);
CREATE INDEX IF NOT EXISTS idx_access_ts ON access_logs (ts);
CREATE INDEX IF NOT EXISTS idx_access_status ON access_logs (status);
CREATE INDEX IF NOT EXISTS idx_access_ip ON access_logs (ip);
