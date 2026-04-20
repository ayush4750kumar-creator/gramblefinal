const express = require('express');
const router = express.Router();
const { pool } = require('../config/database');

router.get('/', async (req, res) => {
  try {
    const page      = parseInt(req.query.page)  || 1;
    const limit     = parseInt(req.query.limit) || 1200;
    const symbol    = req.query.symbol    || null;
    const sentiment = req.query.sentiment || null;
    const category  = req.query.category  || null;
    const feed      = req.query.feed      || null;
    const offset    = (page - 1) * limit;

    const params = [];
    let p = 1;
    let where = `WHERE a.published_at >= NOW() - INTERVAL '30 days'
                   AND a.title IS NOT NULL
                   AND (a.is_duplicate IS NULL OR a.is_duplicate = false)
                   AND a.is_ready = true`;

    if (symbol)    { where += ` AND a.symbol = $${p++}`;           params.push(symbol.toUpperCase()); }
    if (sentiment) { where += ` AND a.sentiment_label = $${p++}`;  params.push(sentiment); }
    if (category)  { where += ` AND a.tag_category = $${p++}`;     params.push(category); }
    if (feed)      { where += ` AND a.tag_feed = $${p++}`;         params.push(feed); }

    const result = await pool.query(`
      SELECT id, symbol, title, url, source, tag_source_name,
             published_at, summary_60w, full_text, image_url,
             tag_feed, tag_category, tag_after_hours,
             sentiment_label, sentiment_reason, agent_source
      FROM articles a
      ${where}
      ORDER BY a.published_at DESC
      LIMIT $${p++} OFFSET $${p++}
    `, [...params, limit, offset]);

    const countResult = await pool.query(
      `SELECT COUNT(*) as count FROM articles a ${where}`, params
    );
    const total = parseInt(countResult.rows[0]?.count || 0);

    res.json({
      success: true,
      data: result.rows,
      pagination: { page, limit, total, hasMore: offset + limit < total }
    });
  } catch (err) {
    console.error('GET /news error:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

router.get('/:id', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM articles WHERE id = $1', [req.params.id]);
    const article = result.rows[0];
    if (!article) return res.status(404).json({ success: false, error: 'Not found' });
    res.json({ success: true, data: article });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
