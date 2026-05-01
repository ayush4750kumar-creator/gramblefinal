// backend/routes/price.js
// Add to your Express app: app.use('/api/price', require('./routes/price'));

const express = require('express');
const router  = express.Router();

const CACHE = new Map(); // symbol → { price, change, changePct, currency, updatedAt }
const TTL   = 15_000;   // 15s cache

async function fetchYahooPrice(symbol) {
  // For NSE stocks Yahoo uses ".NS" suffix, BSE uses ".BO"
  // We try raw symbol first (works for US stocks), then .NS
  const trySymbols = isIndianSymbol(symbol)
    ? [`${symbol}.NS`, `${symbol}.BO`]
    : [symbol];

  for (const ySym of trySymbols) {
    try {
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ySym)}?interval=1m&range=1d`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
        signal:  AbortSignal.timeout(5000),
      });
      if (!res.ok) continue;
      const data = await res.json();
      const meta = data?.chart?.result?.[0]?.meta;
      if (!meta) continue;

      const price     = meta.regularMarketPrice;
      const prevClose = meta.chartPreviousClose || meta.previousClose || price;
      const change    = price - prevClose;
      const changePct = prevClose ? (change / prevClose) * 100 : 0;
      const currency  = meta.currency || (isIndianSymbol(symbol) ? 'INR' : 'USD');

      return { price, change, changePct, currency, symbol: ySym };
    } catch (_) {}
  }
  return null;
}

function isIndianSymbol(symbol) {
  // Heuristic: symbols without dots that aren't well-known US tickers
  const US_TICKERS = new Set(['AAPL','MSFT','NVDA','TSLA','GOOGL','META','AMZN','NFLX','AMD','INTC','UBER','JPM','BAC','GS','COIN','PLTR','SHOP']);
  return !US_TICKERS.has(symbol.toUpperCase()) && !symbol.includes('.');
}

function fmt(price, currency) {
  if (currency === 'INR') return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// GET /api/price?symbols=RELIANCE,AAPL,TSLA
router.get('/', async (req, res) => {
  const raw     = (req.query.symbols || req.query.symbol || '').toUpperCase();
  const symbols = [...new Set(raw.split(',').map(s => s.trim()).filter(Boolean))].slice(0, 20);

  if (!symbols.length) return res.status(400).json({ success: false, error: 'symbols required' });

  const now     = Date.now();
  const results = {};
  const toFetch = [];

  for (const sym of symbols) {
    const cached = CACHE.get(sym);
    if (cached && now - cached.updatedAt < TTL) {
      results[sym] = cached;
    } else {
      toFetch.push(sym);
    }
  }

  // Parallel fetch for uncached symbols
  await Promise.all(toFetch.map(async sym => {
    const data = await fetchYahooPrice(sym);
    if (data) {
      const entry = {
        price:      data.price,
        change:     data.change,
        changePct:  data.changePct,
        currency:   data.currency,
        formatted:  fmt(data.price, data.currency),
        isUp:       data.change >= 0,
        updatedAt:  now,
      };
      CACHE.set(sym, entry);
      results[sym] = entry;
    } else {
      results[sym] = null;
    }
  }));

  res.setHeader('Cache-Control', 'public, s-maxage=15');
  res.json({ success: true, data: results });
});

module.exports = router;