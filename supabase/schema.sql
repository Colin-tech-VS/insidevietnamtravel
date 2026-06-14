-- Inside Vietnam Travel — schéma Supabase (PostgreSQL)
-- Exécutable depuis le SQL Editor Supabase si besoin.

CREATE TABLE IF NOT EXISTS page_views (
    id SERIAL PRIMARY KEY,
    path TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    country_code TEXT,
    country_name TEXT,
    city TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS affiliate_clicks (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    target_url TEXT NOT NULL,
    source_page TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revenue (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency TEXT DEFAULT 'EUR',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_kv (
    key TEXT PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pv_created ON page_views(created_at);
CREATE INDEX IF NOT EXISTS idx_clicks_created ON affiliate_clicks(created_at);
CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email);

CREATE TABLE IF NOT EXISTS visitor_profile_snapshots (
    id SERIAL PRIMARY KEY,
    visitor_hash TEXT NOT NULL,
    trip_group TEXT,
    trip_style TEXT,
    trip_duration TEXT,
    cities TEXT,
    interests TEXT,
    path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_vps_created ON visitor_profile_snapshots(created_at);
CREATE INDEX IF NOT EXISTS idx_vps_hash ON visitor_profile_snapshots(visitor_hash);

CREATE TABLE IF NOT EXISTS mai_chat_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    ip_hash TEXT,
    visitor_hash TEXT,
    lang TEXT,
    path TEXT,
    had_profile BOOLEAN NOT NULL DEFAULT FALSE,
    message_length INTEGER DEFAULT 0,
    site_links_count INTEGER DEFAULT 0,
    affiliate_links_count INTEGER DEFAULT 0,
    error_code TEXT,
    question_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mai_created ON mai_chat_events(created_at);
CREATE INDEX IF NOT EXISTS idx_mai_event ON mai_chat_events(event_type);
CREATE INDEX IF NOT EXISTS idx_mai_visitor ON mai_chat_events(visitor_hash);
