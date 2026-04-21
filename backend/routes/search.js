const express = require('express');
const router  = express.Router();
const { pool } = require('../config/database');

// Top stocks to show when search bar is clicked (no query)
const POPULAR_STOCKS = [
  { symbol: 'RELIANCE',   name: 'Reliance Industries',      exchange: 'NSE' },
  { symbol: 'TCS',        name: 'Tata Consultancy Services', exchange: 'NSE' },
  { symbol: 'HDFCBANK',   name: 'HDFC Bank',                exchange: 'NSE' },
  { symbol: 'INFY',       name: 'Infosys',                  exchange: 'NSE' },
  { symbol: 'ICICIBANK',  name: 'ICICI Bank',               exchange: 'NSE' },
  { symbol: 'SBIN',       name: 'State Bank of India',      exchange: 'NSE' },
  { symbol: 'WIPRO',      name: 'Wipro',                    exchange: 'NSE' },
  { symbol: 'ADANIENT',   name: 'Adani Enterprises',        exchange: 'NSE' },
  { symbol: 'TATAMOTORS', name: 'Tata Motors',              exchange: 'NSE' },
  { symbol: 'BAJFINANCE', name: 'Bajaj Finance',            exchange: 'NSE' },
  { symbol: 'AAPL',       name: 'Apple',                    exchange: 'NASDAQ' },
  { symbol: 'MSFT',       name: 'Microsoft',                exchange: 'NASDAQ' },
  { symbol: 'NVDA',       name: 'Nvidia',                   exchange: 'NASDAQ' },
  { symbol: 'TSLA',       name: 'Tesla',                    exchange: 'NASDAQ' },
  { symbol: 'GOOGL',      name: 'Alphabet (Google)',        exchange: 'NASDAQ' },
  { symbol: 'META',       name: 'Meta',                     exchange: 'NASDAQ' },
  { symbol: 'AMZN',       name: 'Amazon',                   exchange: 'NASDAQ' },
];

// Full symbol+name list for fuzzy matching
const ALL_STOCKS = [
  ...POPULAR_STOCKS,
  { symbol: 'HINDUNILVR', name: 'Hindustan Unilever',    exchange: 'NSE' },
  { symbol: 'ITC',        name: 'ITC Limited',           exchange: 'NSE' },
  { symbol: 'KOTAKBANK',  name: 'Kotak Mahindra Bank',   exchange: 'NSE' },
  { symbol: 'AXISBANK',   name: 'Axis Bank',             exchange: 'NSE' },
  { symbol: 'MARUTI',     name: 'Maruti Suzuki',         exchange: 'NSE' },
  { symbol: 'SUNPHARMA',  name: 'Sun Pharma',            exchange: 'NSE' },
  { symbol: 'NTPC',       name: 'NTPC',                  exchange: 'NSE' },
  { symbol: 'ONGC',       name: 'ONGC',                  exchange: 'NSE' },
  { symbol: 'TATASTEEL',  name: 'Tata Steel',            exchange: 'NSE' },
  { symbol: 'JSWSTEEL',   name: 'JSW Steel',             exchange: 'NSE' },
  { symbol: 'TITAN',      name: 'Titan Company',         exchange: 'NSE' },
  { symbol: 'NESTLEIND',  name: 'Nestle India',          exchange: 'NSE' },
  { symbol: 'HCLTECH',    name: 'HCL Technologies',      exchange: 'NSE' },
  { symbol: 'TECHM',      name: 'Tech Mahindra',         exchange: 'NSE' },
  { symbol: 'ULTRACEMCO', name: 'UltraTech Cement',      exchange: 'NSE' },
  { symbol: 'ADANIPORTS', name: 'Adani Ports',           exchange: 'NSE' },
  { symbol: 'ADANIPOWER', name: 'Adani Power',           exchange: 'NSE' },
  { symbol: 'ZOMATO',     name: 'Zomato',                exchange: 'NSE' },
  { symbol: 'PAYTM',      name: 'Paytm',                 exchange: 'NSE' },
  { symbol: 'NYKAA',      name: 'Nykaa',                 exchange: 'NSE' },
  { symbol: 'INDIGO',     name: 'IndiGo Airlines',       exchange: 'NSE' },
  { symbol: 'IRCTC',      name: 'IRCTC',                 exchange: 'NSE' },
  { symbol: 'DRREDDY',    name: "Dr Reddy's",            exchange: 'NSE' },
  { symbol: 'CIPLA',      name: 'Cipla',                 exchange: 'NSE' },
  { symbol: 'APOLLOHOSP', name: 'Apollo Hospitals',      exchange: 'NSE' },
  { symbol: 'NFLX',       name: 'Netflix',               exchange: 'NASDAQ' },
  { symbol: 'AMD',        name: 'AMD',                   exchange: 'NASDAQ' },
  { symbol: 'INTC',       name: 'Intel',                 exchange: 'NASDAQ' },
  { symbol: 'UBER',       name: 'Uber',                  exchange: 'NYSE' },
  { symbol: 'JPM',        name: 'JPMorgan Chase',        exchange: 'NYSE' },
  { symbol: 'BAC',        name: 'Bank of America',       exchange: 'NYSE' },
  { symbol: 'GS',         name: 'Goldman Sachs',         exchange: 'NYSE' },
  { symbol: 'COIN',       name: 'Coinbase',              exchange: 'NASDAQ' },
  { symbol: 'PLTR',       name: 'Palantir',              exchange: 'NASDAQ' },
  { symbol: 'SHOP',       name: 'Shopify',               exchange: 'NYSE' },
];

// GET /api/search/suggest?q=hdfc
router.get('/suggest', async (req, res) => {
  const q = (req.query.q || '').trim().toLowerCase();

  // No query — return popular stocks
  if (!q) {
    return res.json({ success: true, data: POPULAR_STOCKS, popular: true });
  }

  // Filter by symbol or name match
  const matches = ALL_STOCKS.filter(s =>
    s.symbol.toLowerCase().includes(q) ||
    s.name.toLowerCase().includes(q)
  ).slice(0, 8);

  // Also check if we have news for these symbols in DB
  if (matches.length > 0) {
    const symbols = matches.map(m => m.symbol);
    try {
      const result = await pool.query(
        `SELECT symbol, COUNT(*) as count
         FROM articles
         WHERE symbol = ANY($1)
           AND published_at >= NOW() - INTERVAL '7 days'
           AND is_ready = true
         GROUP BY symbol`,
        [symbols]
      );
      const counts = {};
      result.rows.forEach(r => { counts[r.symbol] = parseInt(r.count); });
      matches.forEach(m => { m.article_count = counts[m.symbol] || 0; });
    } catch (_) {}
  }

  res.json({ success: true, data: matches, popular: false });
});

// GET /api/search/news?symbol=RELIANCE  — get news for a symbol, trigger fetch if sparse
router.get('/news', async (req, res) => {
  const symbol = (req.query.symbol || '').toUpperCase().trim();
  if (!symbol) return res.status(400).json({ success: false, error: 'Symbol required' });

  try {
    const result = await pool.query(
      `SELECT id, symbol, title, url, source, tag_source_name,
              published_at, summary_60w, full_text, image_url,
              tag_feed, tag_category, sentiment_label, sentiment_reason
       FROM articles
       WHERE symbol = $1
         AND published_at >= NOW() - INTERVAL '7 days'
         AND (is_duplicate IS NULL OR is_duplicate = false)
         AND is_ready = true
       ORDER BY published_at DESC
       LIMIT 30`,
      [symbol]
    );

    const news    = result.rows;
    const fetching = news.length < 5;

    // Trigger background fetch if sparse
    if (fetching) {
      const { spawn } = require('child_process');
      const path = require('path');
      const proc = spawn('python3',
        [path.join(__dirname, '../../agents/agentWatchlist.py'), '--symbol', symbol],
        { detached: true, stdio: 'ignore' }
      );
      proc.unref();
    }

    res.json({ success: true, data: news, fetching });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
