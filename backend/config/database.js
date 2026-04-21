const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function initDB() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS articles (
      id              SERIAL PRIMARY KEY,
      symbol          TEXT,
      title           TEXT NOT NULL,
      url             TEXT UNIQUE,
      source          TEXT,
      tag_source_name TEXT,
      published_at    TIMESTAMPTZ,
      full_text       TEXT,
      tag_feed        TEXT DEFAULT 'global',
      tag_category    TEXT DEFAULT 'news',
      tag_after_hours INTEGER DEFAULT 0,
      agent_source    TEXT,
      sentiment_label TEXT,
      sentiment_reason TEXT,
      summary_60w     TEXT,
      is_duplicate    BOOLEAN DEFAULT false,
      is_ready        BOOLEAN DEFAULT false,
      image_url       TEXT,
      created_at      TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS users (
      id            SERIAL PRIMARY KEY,
      email         TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      display_name  TEXT,
      created_at    TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS watchlists (
      id         SERIAL PRIMARY KEY,
      user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      symbol     TEXT NOT NULL,
      added_at   TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(user_id, symbol)
    );

    CREATE INDEX IF NOT EXISTS idx_articles_symbol      ON articles(symbol);
    CREATE INDEX IF NOT EXISTS idx_articles_published   ON articles(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_articles_sentiment   ON articles(sentiment_label);
    CREATE INDEX IF NOT EXISTS idx_watchlists_user      ON watchlists(user_id);
    CREATE INDEX IF NOT EXISTS idx_watchlists_symbol    ON watchlists(symbol);
  `);
  console.log('✅ Database ready');
}

module.exports = { pool, initDB };