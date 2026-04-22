const express = require('express');
const router  = express.Router();
const { pool } = require('../config/database');
const { authMiddleware } = require('../middleware/auth');
const { spawn } = require('child_process');
const path = require('path');

// GET /api/watchlist  — get user's watchlist + latest article count per symbol
router.get('/', authMiddleware, async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT w.symbol, w.added_at,
              COUNT(a.id) AS article_count,
              MAX(a.published_at) AS latest_article
       FROM watchlists w
       LEFT JOIN articles a ON a.symbol = w.symbol
         AND a.published_at >= NOW() - INTERVAL '7 days'
         AND (a.is_duplicate IS NULL OR a.is_duplicate = false)
         AND a.is_ready = true
       WHERE w.user_id = $1
       GROUP BY w.symbol, w.added_at
       ORDER BY w.added_at DESC`,
      [req.user.id]
    );
    res.json({ success: true, data: result.rows });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// POST /api/watchlist  — add stock to watchlist
router.post('/', authMiddleware, async (req, res) => {
  const { symbol } = req.body;
  if (!symbol) return res.status(400).json({ success: false, error: 'Symbol required' });

  const sym = symbol.toUpperCase().trim();

  try {
    // Add to watchlist
    await pool.query(
      `INSERT INTO watchlists (user_id, symbol) VALUES ($1, $2) ON CONFLICT DO NOTHING`,
      [req.user.id, sym]
    );

    // Return any existing news immediately
    const newsResult = await pool.query(
      `SELECT id, symbol, title, url, source, tag_source_name,
              published_at, summary_60w, full_text, image_url,
              tag_feed, tag_category, sentiment_label, sentiment_reason
       FROM articles
       WHERE symbol = $1
         AND published_at >= NOW() - INTERVAL '7 days'
         AND (is_duplicate IS NULL OR is_duplicate = false)
         AND is_ready = true
       ORDER BY published_at DESC
       LIMIT 20`,
      [sym]
    );

    // Always trigger a fresh fetch for this symbol — no conditions
    triggerWatchlistFetch(sym);

    res.json({
      success: true,
      symbol:   sym,
      news:     newsResult.rows,
      fetching: true,
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// DELETE /api/watchlist/:symbol  — remove from watchlist
router.delete('/:symbol', authMiddleware, async (req, res) => {
  try {
    await pool.query(
      'DELETE FROM watchlists WHERE user_id = $1 AND symbol = $2',
      [req.user.id, req.params.symbol.toUpperCase()]
    );
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// GET /api/watchlist/news  — get all news for user's watchlist symbols
router.get('/news', authMiddleware, async (req, res) => {
  try {
    const watchResult = await pool.query(
      'SELECT symbol FROM watchlists WHERE user_id = $1', [req.user.id]
    );
    const symbols = watchResult.rows.map(r => r.symbol);
    if (!symbols.length) return res.json({ success: true, data: [] });

    const result = await pool.query(
      `SELECT id, symbol, title, url, source, tag_source_name,
              published_at, summary_60w, full_text, image_url,
              tag_feed, tag_category, sentiment_label, sentiment_reason
       FROM articles
       WHERE symbol = ANY($1)
         AND published_at >= NOW() - INTERVAL '7 days'
         AND (is_duplicate IS NULL OR is_duplicate = false)
         AND is_ready = true
       ORDER BY published_at DESC
       LIMIT 200`,
      [symbols]
    );
    res.json({ success: true, data: result.rows, symbols });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Background fetch — always triggers for the symbol, no conditions
function triggerWatchlistFetch(symbol) {
  const agentPath = path.join(__dirname, '../../agents/agentWatchlist.py');
  const proc = spawn('python3', [agentPath, '--symbol', symbol], {
    detached: true,
    stdio:    ['ignore', 'pipe', 'pipe'],
  });

  proc.stdout?.on('data', d => console.log(`[agentWatchlist][${symbol}] ${d.toString().trim()}`));
  proc.stderr?.on('data', d => console.error(`[agentWatchlist][${symbol}] ERROR: ${d.toString().trim()}`));
  proc.unref();
  console.log(`🔄 Triggered watchlist fetch for ${symbol}`);
}

module.exports = router;