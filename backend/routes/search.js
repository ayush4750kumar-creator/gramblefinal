const express = require('express');
const router   = express.Router();
const { pool } = require('../config/database');

const recentTriggers = new Map();
const PIPELINE_URL   = process.env.PIPELINE_URL || 'https://resplendent-surprise.up.railway.app';

async function triggerPipeline(symbol) {
  const now  = Date.now();
  const last = recentTriggers.get(symbol);
  if (last && now - last < 30_000) {
    console.log(`⏭  Skipping pipeline for ${symbol} — triggered ${Math.round((now - last) / 1000)}s ago`);
    return;
  }
  recentTriggers.set(symbol, now);
  console.log(`🔥 Triggering search pipeline for ${symbol} → ${PIPELINE_URL}`);
  fetch(`${PIPELINE_URL}/trigger-search?symbol=${encodeURIComponent(symbol)}`, {
    signal: AbortSignal.timeout(5000),
  }).then(r => {
    console.log(`[pipeline][${symbol}] trigger-search response: ${r.status}`);
  }).catch(e => {
    console.error(`[pipeline][${symbol}] trigger-search failed: ${e.message}`);
  });
}

async function waitForArticles(symbol, minCount = 5, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await pool.query(
      `SELECT COUNT(*) as count FROM articles
       WHERE symbol = $1
         AND published_at >= NOW() - INTERVAL '7 days'
         AND (is_duplicate IS NULL OR is_duplicate = false)
         AND is_ready = true`,
      [symbol]
    );
    const count = parseInt(result.rows[0].count);
    if (count >= minCount) return count;
    await new Promise(r => setTimeout(r, 1500));
  }
  return 0;
}

async function yahooSearch(q) {
  try {
    const url = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=6&newsCount=0&listsCount=0`;
    const res  = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' },
      signal:  AbortSignal.timeout(4000),
    });
    const data = await res.json();
    const quotes = (data?.quotes || []).filter(q =>
      q.symbol && (q.shortname || q.longname) && ['EQUITY', 'ETF'].includes(q.quoteType)
    );
    return quotes.map(q => ({
      symbol:        q.symbol,
      name:          q.shortname || q.longname || q.symbol,
      exchange:      q.exchDisp  || q.exchange  || 'UNKNOWN',
      article_count: 0,
    }));
  } catch (e) {
    console.error('Yahoo search error:', e.message);
    return [];
  }
}

const POPULAR_STOCKS = [
  { symbol: 'RELIANCE',   name: 'Reliance Industries',       exchange: 'NSE' },
  { symbol: 'TCS',        name: 'Tata Consultancy Services', exchange: 'NSE' },
  { symbol: 'HDFCBANK',   name: 'HDFC Bank',                 exchange: 'NSE' },
  { symbol: 'INFY',       name: 'Infosys',                   exchange: 'NSE' },
  { symbol: 'ICICIBANK',  name: 'ICICI Bank',                exchange: 'NSE' },
  { symbol: 'SBIN',       name: 'State Bank of India',       exchange: 'NSE' },
  { symbol: 'WIPRO',      name: 'Wipro',                     exchange: 'NSE' },
  { symbol: 'ADANIENT',   name: 'Adani Enterprises',         exchange: 'NSE' },
  { symbol: 'TATAMOTORS', name: 'Tata Motors',               exchange: 'NSE' },
  { symbol: 'BAJFINANCE', name: 'Bajaj Finance',             exchange: 'NSE' },
  { symbol: 'AAPL',       name: 'Apple',                     exchange: 'NASDAQ' },
  { symbol: 'MSFT',       name: 'Microsoft',                 exchange: 'NASDAQ' },
  { symbol: 'NVDA',       name: 'Nvidia',                    exchange: 'NASDAQ' },
  { symbol: 'TSLA',       name: 'Tesla',                     exchange: 'NASDAQ' },
  { symbol: 'GOOGL',      name: 'Alphabet (Google)',         exchange: 'NASDAQ' },
  { symbol: 'META',       name: 'Meta',                      exchange: 'NASDAQ' },
  { symbol: 'AMZN',       name: 'Amazon',                    exchange: 'NASDAQ' },
];

const ALL_STOCKS = [
  ...POPULAR_STOCKS,
  { symbol: 'HINDUNILVR', name: 'Hindustan Unilever',  exchange: 'NSE' },
  { symbol: 'ITC',        name: 'ITC Limited',         exchange: 'NSE' },
  { symbol: 'KOTAKBANK',  name: 'Kotak Mahindra Bank', exchange: 'NSE' },
  { symbol: 'AXISBANK',   name: 'Axis Bank',           exchange: 'NSE' },
  { symbol: 'MARUTI',     name: 'Maruti Suzuki',       exchange: 'NSE' },
  { symbol: 'SUNPHARMA',  name: 'Sun Pharma',          exchange: 'NSE' },
  { symbol: 'NTPC',       name: 'NTPC',                exchange: 'NSE' },
  { symbol: 'ONGC',       name: 'ONGC',                exchange: 'NSE' },
  { symbol: 'TATASTEEL',  name: 'Tata Steel',          exchange: 'NSE' },
  { symbol: 'JSWSTEEL',   name: 'JSW Steel',           exchange: 'NSE' },
  { symbol: 'TITAN',      name: 'Titan Company',       exchange: 'NSE' },
  { symbol: 'NESTLEIND',  name: 'Nestle India',        exchange: 'NSE' },
  { symbol: 'HCLTECH',    name: 'HCL Technologies',    exchange: 'NSE' },
  { symbol: 'TECHM',      name: 'Tech Mahindra',       exchange: 'NSE' },
  { symbol: 'ULTRACEMCO', name: 'UltraTech Cement',    exchange: 'NSE' },
  { symbol: 'ADANIPORTS', name: 'Adani Ports',         exchange: 'NSE' },
  { symbol: 'ADANIPOWER', name: 'Adani Power',         exchange: 'NSE' },
  { symbol: 'ZOMATO',     name: 'Zomato',              exchange: 'NSE' },
  { symbol: 'PAYTM',      name: 'Paytm',               exchange: 'NSE' },
  { symbol: 'NYKAA',      name: 'Nykaa',               exchange: 'NSE' },
  { symbol: 'INDIGO',     name: 'IndiGo Airlines',     exchange: 'NSE' },
  { symbol: 'IRCTC',      name: 'IRCTC',               exchange: 'NSE' },
  { symbol: 'DRREDDY',    name: "Dr Reddy's",          exchange: 'NSE' },
  { symbol: 'CIPLA',      name: 'Cipla',               exchange: 'NSE' },
  { symbol: 'APOLLOHOSP', name: 'Apollo Hospitals',    exchange: 'NSE' },
  { symbol: 'NFLX',       name: 'Netflix',             exchange: 'NASDAQ' },
  { symbol: 'AMD',        name: 'AMD',                 exchange: 'NASDAQ' },
  { symbol: 'INTC',       name: 'Intel',               exchange: 'NASDAQ' },
  { symbol: 'UBER',       name: 'Uber',                exchange: 'NYSE' },
  { symbol: 'JPM',        name: 'JPMorgan Chase',      exchange: 'NYSE' },
  { symbol: 'BAC',        name: 'Bank of America',     exchange: 'NYSE' },
  { symbol: 'GS',         name: 'Goldman Sachs',       exchange: 'NYSE' },
  { symbol: 'COIN',       name: 'Coinbase',            exchange: 'NASDAQ' },
  { symbol: 'PLTR',       name: 'Palantir',            exchange: 'NASDAQ' },
  { symbol: 'SHOP',       name: 'Shopify',             exchange: 'NYSE' },
];

router.get('/suggest', async (req, res) => {
  const q = (req.query.q || '').trim().toLowerCase();

  if (!q) {
    return res.json({ success: true, data: POPULAR_STOCKS, popular: true });
  }

  let matches = ALL_STOCKS.filter(s =>
    s.symbol.toLowerCase().includes(q) ||
    s.name.toLowerCase().includes(q)
  ).slice(0, 8);

  if (matches.length === 0) {
    matches = await yahooSearch(q);
  }

  if (matches.length === 0) {
    matches = [{
      symbol:        q.toUpperCase(),
      name:          q.toUpperCase(),
      exchange:      'UNKNOWN',
      article_count: 0,
    }];
  }

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

  res.json({ success: true, data: matches, popular: false });
});

router.get('/news', async (req, res) => {
  const symbol = (req.query.symbol || '').toUpperCase().trim();
  if (!symbol) return res.status(400).json({ success: false, error: 'Symbol required' });

  console.log(`🔍 /api/search/news hit for: ${symbol}`);

  try {
    const existing = await pool.query(
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

    console.log(`📊 Found ${existing.rows.length} existing articles for ${symbol}`);

    triggerPipeline(symbol);

    if (existing.rows.length < 5) {
      console.log(`⏳ Only ${existing.rows.length} articles — waiting for pipeline...`);
      await waitForArticles(symbol, 5, 15000);

      const fresh = await pool.query(
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
      return res.json({ success: true, data: fresh.rows, fetching: false });
    }

    res.json({ success: true, data: existing.rows, fetching: false });

  } catch (err) {
    console.error(`/api/search/news error: ${err.message}`);
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
