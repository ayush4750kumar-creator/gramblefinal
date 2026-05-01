const express = require('express');
const router  = express.Router();

const CACHE = new Map();
const TTL   = 15_000;

const NSE_SYMBOLS = new Set([
  'RELIANCE','TCS','HDFCBANK','INFY','ICICIBANK','SBIN','WIPRO','ADANIENT',
  'TATAMOTORS','BAJFINANCE','HINDUNILVR','ITC','KOTAKBANK','AXISBANK','MARUTI',
  'SUNPHARMA','NTPC','ONGC','TATASTEEL','JSWSTEEL','TITAN','NESTLEIND','HCLTECH',
  'TECHM','ULTRACEMCO','ADANIPORTS','ADANIPOWER','ZOMATO','PAYTM','NYKAA',
  'INDIGO','IRCTC','DRREDDY','CIPLA','APOLLOHOSP','BAJAJFINSV','POWERGRID',
  'COALINDIA','DIVISLAB','EICHERMOT','HEROMOTOCO','BPCL','BRITANNIA','SHREECEM',
]);

function isIndianSymbol(symbol) {
  return NSE_SYMBOLS.has(symbol.toUpperCase());
}

async function fetchYahooPrice(symbol) {
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
      if (!meta || !meta.regularMarketPrice) continue;
      const price     = meta.regularMarketPrice;
      const prevClose = meta.chartPreviousClose || meta.previousClose || price;
      const change    = price - prevClose;
      const changePct = prevClose ? (change / prevClose) * 100 : 0;
      const currency  = meta.currency || 'USD';
      return { price, change, changePct, currency };
    } catch (_) {}
  }
  return null;
}

function fmt(price, currency) {
  if (currency === 'INR') return `₹${price.toLocaleString('en-IN', { minimumFractionDigits:2, maximumFractionDigits:2 })}`;
  return `$${price.toLocaleString('en-US', { minimumFractionDigits:2, maximumFractionDigits:2 })}`;
}

router.get('/', async (req, res) => {
  const raw     = (req.query.symbols || req.query.symbol || '').toUpperCase();
  const symbols = [...new Set(raw.split(',').map(s => s.trim()).filter(Boolean))].slice(0, 20);
  if (!symbols.length) return res.status(400).json({ success: false, error: 'symbols required' });

  const now = Date.now();
  const results = {};
  const toFetch = [];

  for (const sym of symbols) {
    const cached = CACHE.get(sym);
    if (cached && now - cached.updatedAt < TTL) results[sym] = cached;
    else toFetch.push(sym);
  }

  await Promise.all(toFetch.map(async sym => {
    const data = await fetchYahooPrice(sym);
    if (data) {
      const entry = { price:data.price, change:data.change, changePct:data.changePct, currency:data.currency, formatted:fmt(data.price,data.currency), isUp:data.change>=0, updatedAt:now };
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
