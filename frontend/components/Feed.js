import { useEffect, useState, useRef, useCallback } from 'react';
import StockAnalysis from './StockAnalysis';

const SENTIMENT = {
  bullish:  { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  bearish:  { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  positive: { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  negative: { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  neutral:  { bg:'#f3f4f6', color:'#6b7280', label:'Neutral', arrow:'●' },
};

const PLACEHOLDER  = 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80';
const API          = 'https://gramblefinal-production.up.railway.app/api/news';
const SEARCH_API   = 'https://gramblefinal-production.up.railway.app/api/search';
const PAGE_SIZE    = 200;
const AUTO_REFRESH = 60 * 1000;
const PRICE_API    = 'https://gramblefinal-production.up.railway.app/api/price';

const EXCHANGE_TABS = [
  { key:'NSE',    label:'NSE',    color:'#7c3aed' },
  { key:'BSE',    label:'BSE',    color:'#ea580c' },
  { key:'NASDAQ', label:'NASDAQ', color:'#2563eb' },
  { key:'NYSE',   label:'NYSE',   color:'#16a34a' },
];
const EXCHANGE_SOURCES = {
  NSE:    ['nse','nse_announcements','nse india','nseindia','economic times','moneycontrol','livemint','business standard','ndtv','financial express','zeebiz'],
  BSE:    ['bse','bse_announcements','bombay','hindu business','cnbctv18'],
  NASDAQ: ['nasdaq','techcrunch','the verge','wired','reuters','bloomberg','cnbc','marketwatch'],
  NYSE:   ['nyse','wall street','wsj','ap news','financial times','seeking alpha','yahoo finance'],
};
const BAD_KEYWORDS = ['wrestlemania','wwe','cricket','ipl','bollywood','celebrity'];
const ALL_EXCHANGE_SOURCES = Object.values(EXCHANGE_SOURCES).flat();

function isHindi(text) {
  if (!text) return false;
  return (text.match(/[\u0900-\u097F]/g)||[]).length / text.length > 0.2;
}
function isVader(text) {
  if (!text) return true;
  return text.toLowerCase().includes('vader') || text.toLowerCase().includes('compound score');
}
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '';
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 0) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  return `${Math.floor(diff/86400)}d ago`;
}
function filterGlobal(data) {
  return data.filter(a => {
    const src = [(a.source||''),(a.tag_source_name||''),(a.agent_source||'')].join(' ').toLowerCase();
    return !ALL_EXCHANGE_SOURCES.some(s => src.includes(s))
      && !isHindi(a.title)
      && !BAD_KEYWORDS.some(k => (a.title||'').toLowerCase().includes(k));
  });
}

function useIsMobile() {
  const [m, setM] = useState(false);
  useEffect(() => {
    const check = () => setM(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  return m;
}

function viewToHash(view) {
  if (!view || view === 'feed') return '';
  if (view?.type === 'stock' || view?.type === 'stock-news') return view.symbol;
  return '';
}
function hashToView(hash) {
  const h = (hash||'').replace(/^#/,'').trim();
  if (!h) return 'feed';
  return { type: 'stock-news', symbol: h.toUpperCase() };
}

const btnStyle = {
  display:'flex', alignItems:'center', justifyContent:'center', gap:6,
  fontSize:13, fontWeight:600, padding:'10px 0', borderRadius:20,
  textDecoration:'none', flex:1, background:'#e0f2fe', color:'#0284c7',
  border:'1.5px solid #bae6fd', cursor:'pointer',
};

function WatchlistToast({ symbol }) {
  return (
    <div style={{ position:'fixed', bottom:32, left:'50%', transform:'translateX(-50%)', background:'#1e2433', color:'#fff', padding:'12px 24px', borderRadius:12, fontSize:14, fontWeight:600, zIndex:9999, boxShadow:'0 4px 20px rgba(0,0,0,0.2)', display:'flex', alignItems:'center', gap:10 }}>
      <span style={{ color:'#34d399' }}>✓</span> {symbol} added to watchlist
    </div>
  );
}

function NewArticlesPill({ count, onClick }) {
  return (
    <div onClick={onClick} style={{ position:'sticky', top:8, zIndex:20, display:'flex', justifyContent:'center', marginBottom:8, cursor:'pointer' }}>
      <div style={{ background:'#2563eb', color:'#fff', fontSize:13, fontWeight:700, padding:'8px 20px', borderRadius:20, boxShadow:'0 4px 16px rgba(37,99,235,0.35)', display:'flex', alignItems:'center', gap:8, userSelect:'none' }}>
        ↑ {count} new article{count > 1 ? 's' : ''} — tap to load
      </div>
    </div>
  );
}

function Spinner({ size=36 }) {
  return (
    <>
      <div style={{ width:size, height:size, border:'3px solid #e5e7eb', borderTop:'3px solid #2563eb', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

function MobileNewsCard({ a, price, watchlist, setView, onWatchlistClick }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle   = (a.title||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const cleanSummary = (a.summary_60w||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const summary      = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason       = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;
  const isCompany    = !!a.symbol && a.symbol !== 'MARKET';
  const isWatchlisted = watchlist?.find(w => w.symbol === a.symbol);
  return (
    <div style={{ background:'#fff', borderRadius:16, marginBottom:14, overflow:'hidden', boxShadow:'0 1px 4px rgba(0,0,0,0.08)' }}>
      <div style={{ width:'100%', height:200, position:'relative', overflow:'hidden' }}>
        <img src={a.image_url||PLACEHOLDER} alt="" style={{ width:'100%', height:'100%', objectFit:'cover' }} onError={e=>{ e.target.src=PLACEHOLDER; }} />
        <div style={{ position:'absolute', bottom:10, left:10, background:'rgba(0,0,0,0.65)', color:'#fff', fontSize:10, fontWeight:700, padding:'4px 10px', borderRadius:6 }}>
          <div style={{ fontSize:9, opacity:0.8 }}>{a.tag_category?.toUpperCase()||'MARKET'}</div>
          <div>{a.symbol||'Global News'}</div>
        </div>
        {s && <div style={{ position:'absolute', top:10, left:10, background:s.color, color:'#fff', fontSize:10, fontWeight:700, padding:'4px 10px', borderRadius:6 }}>{s.arrow} {s.label.toUpperCase()}</div>}
        {price && <div style={{ position:'absolute', bottom:10, right:10, background:'rgba(0,0,0,0.65)', color:'#fff', fontSize:10, fontWeight:700, padding:'4px 8px', borderRadius:6, fontFamily:'monospace', lineHeight:1.4, display:'flex', flexDirection:'column', alignItems:'flex-end' }}><span>{price.formatted}</span><span style={{ color: price.isUp ? '#4ade80' : '#f87171' }}>{price.isUp?'+':''}{price.changePct.toFixed(2)}%</span></div>}
        {isCompany && <button onClick={()=>onWatchlistClick(a.symbol)} style={{ position:'absolute', top:10, right:10, background: isWatchlisted?'#2563eb':'rgba(255,255,255,0.92)', border:'none', borderRadius:8, padding:'6px 12px', fontSize:11, fontWeight:700, color: isWatchlisted?'#fff':'#374151', cursor:'pointer' }}>{isWatchlisted?'✓ Watchlisted':'+ Watchlist'}</button>}
      </div>
      <div style={{ padding:'12px 14px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:10 }}>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{timeAgo(a.published_at)}</span>
          <span style={{ fontSize:11, color:'#c4c4c4' }}>·</span>
          <span style={{ fontSize:11, color:'#9ca3af', fontWeight:600 }}>{a.tag_source_name||a.source}</span>
        </div>
        <div style={{ display:'flex', gap:8, marginBottom:10 }}>
          <a href={a.url} target="_blank" rel="noreferrer" style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', gap:5, padding:'10px', borderRadius:10, background:'#f0f9ff', color:'#0284c7', fontSize:13, fontWeight:600, textDecoration:'none', border:'1px solid #bae6fd' }}>Read Article ↗</a>
          {isCompany && (
            <button
              onClick={() => setView({ type:'stock', symbol:a.symbol, companyName:a.companyName||a.symbol, sentiment:a.sentiment_label })}
              style={{ flex:1, padding:'10px', borderRadius:10, background:'#f0f9ff', color:'#0284c7', fontSize:13, fontWeight:600, border:'1px solid #bae6fd', cursor:'pointer' }}
            >
              Stock Analysis →
            </button>
          )}
        </div>
        <div style={{ fontSize:15, fontWeight:700, color:'#111', lineHeight:1.5, marginBottom:8 }}>{cleanTitle}</div>
        {summary && <div style={{ fontSize:13, color:'#4b5563', lineHeight:1.65, marginBottom:8 }}>{summary}</div>}
        {reason && s && <div style={{ fontSize:12, fontStyle:'italic', background:s.bg, color:s.color, padding:'8px 12px', borderRadius:8, lineHeight:1.6 }}>{reason}</div>}
      </div>
    </div>
  );
}

function NewsCard({ a, price, onWatchlist, watchlist, setView, onWatchlistClick }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle   = (a.title||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const cleanSummary = (a.summary_60w||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const summary      = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason       = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;
  const isCompany    = !!a.symbol && a.symbol !== 'MARKET';
  const isWatchlisted = watchlist?.find(w => w.symbol === a.symbol);
  return (
    <div style={{ background:'#fff', borderRadius:14, border:'1px solid #e5e7eb', boxShadow:'0 2px 8px rgba(0,0,0,0.06)', marginBottom:16, overflow:'hidden' }}>
      <div style={{ width:'100%', height:180, position:'relative', overflow:'hidden' }}>
        <img src={a.image_url||PLACEHOLDER} alt="" style={{ width:'100%', height:'100%', objectFit:'cover' }} onError={e=>{ e.target.src=PLACEHOLDER; }} />
        {s && <div style={{ position:'absolute', top:12, left:12, background:s.color, color:'#fff', fontSize:11, fontWeight:700, padding:'4px 10px', borderRadius:6 }}>{s.arrow} {s.label.toUpperCase()}</div>}
        {price && <div style={{ position:'absolute', bottom:10, right:10, background:'rgba(0,0,0,0.65)', color:'#fff', fontSize:10, fontWeight:700, padding:'4px 8px', borderRadius:6, fontFamily:'monospace', lineHeight:1.4, display:'flex', flexDirection:'column', alignItems:'flex-end' }}><span>{price.formatted}</span><span style={{ color: price.isUp ? '#4ade80' : '#f87171' }}>{price.isUp?'+':''}{price.changePct.toFixed(2)}%</span></div>}
        {isCompany && <button onClick={()=>onWatchlistClick(a.symbol)} style={{ position:'absolute', top:12, right:12, background: isWatchlisted?'#2563eb':'rgba(255,255,255,0.92)', border:'1px solid #e5e7eb', borderRadius:6, padding:'4px 10px', fontSize:11, fontWeight:600, color: isWatchlisted?'#fff':'#374151', cursor:'pointer', transition:'all 0.2s' }}>{isWatchlisted?'✓ Watchlisted':'+ Watchlist'}</button>}
      </div>
      <div style={{ padding:'14px 16px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:10, flexWrap:'wrap' }}>
          <span style={{ fontSize:11, fontWeight:700, background:'#f3f4f6', color:'#374151', padding:'2px 8px', borderRadius:4 }}>{a.symbol||'Global News'}</span>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{a.tag_source_name||a.source}</span>
          <span style={{ fontSize:11, color:'#c4c4c4' }}>·</span>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{timeAgo(a.published_at)}</span>
        </div>
        <div style={{ display:'flex', gap:10, marginBottom:12 }}>
          <a href={a.url} target="_blank" rel="noreferrer" style={btnStyle} onMouseEnter={e=>e.currentTarget.style.background='#bae6fd'} onMouseLeave={e=>e.currentTarget.style.background='#e0f2fe'}>Read Article <span style={{ fontSize:15 }}>↗</span></a>
          {isCompany && (
            <button
              onClick={() => setView({ type:'stock', symbol:a.symbol, companyName:a.companyName||a.symbol, sentiment:a.sentiment_label })}
              style={btnStyle}
              onMouseEnter={e=>e.currentTarget.style.background='#bae6fd'}
              onMouseLeave={e=>e.currentTarget.style.background='#e0f2fe'}
            >
              Stock Analysis <span style={{ fontSize:14 }}>→</span>
            </button>
          )}
        </div>
        <div style={{ fontSize:15, fontWeight:700, color:'#111', lineHeight:1.5, marginBottom:8 }}>{cleanTitle}</div>
        {summary && <div style={{ fontSize:13, color:'#4b5563', lineHeight:1.65, marginBottom:8 }}>{summary}</div>}
        {reason && s && <div style={{ fontSize:12, fontStyle:'italic', background:s.bg, color:s.color, padding:'8px 12px', borderRadius:8, lineHeight:1.6 }}>{reason}</div>}
      </div>
    </div>
  );
}

function FetchingScreen({ symbol }) {
  const [dots, setDots] = useState('');
  useEffect(() => {
    const t = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 400);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'70%', gap:16 }}>
      <div style={{ fontSize:28, fontWeight:800, color:'#111' }}>{symbol}</div>
      <Spinner size={40} />
      <div style={{ fontSize:14, color:'#6b7280', fontWeight:500 }}>Fetching news{dots}</div>
    </div>
  );
}

function MobileHeader({ feedTitle, articleCount, isStockNews, isStockDash, view, setView, watchlist, onWatchlistClick, loading }) {
  const inWatchlist = (isStockNews || isStockDash) && watchlist?.find(w => w.symbol === view.symbol);
  const hasFullName = (isStockNews || isStockDash) && view.companyName && view.companyName !== view.symbol;

  return (
    <div style={{ background:'#fff', padding:'14px 16px 12px', borderBottom:'1px solid #f0f0f0', position:'sticky', top:0, zIndex:10 }}>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        {view !== 'feed' && (
          <button onClick={()=>setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:20, color:'#374151', padding:0, lineHeight:1, flexShrink:0 }}>←</button>
        )}

        {/* Non-stock pages: show feed title + count */}
        {!isStockNews && !isStockDash && (
          <>
            <div style={{ fontSize:22, fontWeight:800, color:'#111', letterSpacing:'-0.3px' }}>{feedTitle}</div>
            {!loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:4 }}>{articleCount} articles</span>}
          </>
        )}

        {/* Stock pages: show full company name + ticker symbol */}
        {(isStockNews || isStockDash) && (
          <div style={{ display:'flex', flexDirection:'column', justifyContent:'center', flex:1, minWidth:0 }}>
            <div style={{ fontSize:16, fontWeight:800, color:'#111', lineHeight:1.2, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>
              {hasFullName ? view.companyName : view.symbol}
            </div>
            {hasFullName && (
              <div style={{ fontSize:11, color:'#9ca3af', fontWeight:600, fontFamily:'monospace' }}>{view.symbol}</div>
            )}
          </div>
        )}

        {(isStockNews || isStockDash) && (
          <div style={{ display:'flex', gap:6, flexShrink:0 }}>
            <button onClick={()=>onWatchlistClick(view.symbol)} style={{ padding:'7px 12px', borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer', background: inWatchlist?'#2563eb':'#f3f4f6', color: inWatchlist?'#fff':'#374151', border:'none' }}>
              {inWatchlist?'✓ Watched':'+ Watch'}
            </button>
            {isStockNews && (
              <button
                onClick={()=>setView({ type:'stock', symbol:view.symbol, companyName:view.companyName, sentiment:view.sentiment })}
                style={{ padding:'7px 12px', borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer', background:'#2563eb', color:'#fff', border:'none' }}
              >
                Stock Analysis →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function useFeedPrices(articles) {
  const [prices, setPrices] = useState({});
  const timerRef = useRef(null);
  useEffect(() => {
    const symbols = [...new Set(articles.map(a=>a.symbol).filter(s=>s&&s!=='MARKET'))].slice(0,30);
    if (!symbols.length) return;
    const fetch_ = async () => {
      try {
        const res  = await fetch(`${PRICE_API}?symbols=${symbols.join(',')}`);
        const data = await res.json();
        if (data.success) setPrices(data.data);
      } catch (_) {}
    };
    fetch_();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(fetch_, 30000);
    return () => clearInterval(timerRef.current);
  }, [articles.map(a=>a.symbol).join(',')]); // eslint-disable-line
  return prices;
}

export default function Feed({ user, view, setView, onWatchlist, watchlist }) {
  const [articles,    setArticles]    = useState([]);
  const [newArticles, setNewArticles] = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [fetching,    setFetching]    = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore,     setHasMore]     = useState(true);
  const [page,        setPage]        = useState(1);
  const [exchangeTab, setExchangeTab] = useState('NSE');
  const [toast,       setToast]       = useState(null);

  const toastTimer   = useRef(null);
  const pollTimer    = useRef(null);
  const pollCount    = useRef(0);
  const refreshTimer = useRef(null);
  const latestDate   = useRef(null);
  const loaderRef    = useRef(null);
  const scrollRef    = useRef(null);
  const isMobile     = useIsMobile();

  const isStockDash  = view?.type === 'stock';
  const isStockNews  = view?.type === 'stock-news';
  const isStock      = isStockDash || isStockNews;
  const isExchange   = view === 'World Exchange';

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/,'').trim();
    if (hash) {
      const restored = hashToView(hash);
      if (restored !== 'feed') setView(restored);
    }
  }, []); // eslint-disable-line

  useEffect(() => {
    const hash = viewToHash(view);
    if (!hash) history.replaceState(null, '', window.location.pathname.split('#')[0] || '/');
    else history.replaceState(null, '', '#' + hash);
  }, [view]);

  const handleWatchlistClick = (symbol) => {
    onWatchlist?.(symbol);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(symbol);
    toastTimer.current = setTimeout(() => setToast(null), 2500);
  };

  const buildUrl = useCallback((pg = 1) => {
    if (isStock)    return `${API}?limit=100&symbol=${view.symbol}`;
    if (isExchange) return `${API}?limit=100&page=${pg}`;
    if (view !== 'feed') return `${API}?limit=${PAGE_SIZE}&page=${pg}&category=${encodeURIComponent(view)}`;
    return `${API}?limit=${PAGE_SIZE}&page=${pg}`;
  }, [isStock, isExchange, view]);

  const stopRefresh = () => { if (refreshTimer.current) { clearInterval(refreshTimer.current); refreshTimer.current = null; } };
  const startRefresh = useCallback((currentView) => {
    stopRefresh();
    refreshTimer.current = setInterval(async () => {
      try {
        let fresh = [];
        if (currentView?.type === 'stock' || currentView?.type === 'stock-news') {
          const d = await fetch(`${API}?limit=100&symbol=${currentView.symbol}`).then(r=>r.json());
          fresh = d.data || [];
        } else {
          const d = await fetch(`${API}?limit=${PAGE_SIZE}`).then(r=>r.json());
          fresh = filterGlobal(d.data || []);
        }
        if (!fresh.length || !latestDate.current) return;
        const newer = fresh.filter(a => new Date(a.published_at) > new Date(latestDate.current));
        if (newer.length > 0) setNewArticles(newer);
      } catch (_) {}
    }, AUTO_REFRESH);
  }, []);

  const loadNewArticles = () => {
    if (!newArticles.length) return;
    setArticles(prev => {
      const ids = new Set(prev.map(a=>a.id));
      const merged = [...newArticles.filter(a=>!ids.has(a.id)), ...prev]
        .sort((a,b) => new Date(b.published_at) - new Date(a.published_at));
      latestDate.current = merged[0]?.published_at || latestDate.current;
      return merged;
    });
    setNewArticles([]);
    window.scrollTo({ top:0, behavior:'smooth' });
  };

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore || isStock) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const d = await fetch(buildUrl(nextPage)).then(r=>r.json());
      let more = d.data || [];
      if (!isExchange) more = filterGlobal(more);
      if (!more.length) { setHasMore(false); }
      else {
        setArticles(prev => {
          const ids = new Set(prev.map(a=>a.id));
          return [...prev, ...more.filter(a=>!ids.has(a.id))];
        });
        setPage(nextPage);
        if (!d.pagination?.hasMore) setHasMore(false);
      }
    } catch (_) {}
    setLoadingMore(false);
  }, [loadingMore, hasMore, isStock, page, buildUrl, isExchange]);

  useEffect(() => {
    if (!loaderRef.current) return;
    const root = isMobile ? scrollRef.current : null;
    const obs = new IntersectionObserver(
      entries => { if (entries[0].isIntersecting) loadMore(); },
      { threshold:0.1, root }
    );
    obs.observe(loaderRef.current);
    return () => obs.disconnect();
  }, [loadMore, isMobile]);

  const stopPolling = () => { if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null; } };
  const startPolling = (sym) => {
    stopPolling();
    pollCount.current = 0;
    pollTimer.current = setInterval(async () => {
      pollCount.current++;
      if (pollCount.current > 12) { stopPolling(); setFetching(false); return; }
      const d = await fetch(`${API}?limit=100&symbol=${sym}`).then(r=>r.json()).catch(()=>({data:[]}));
      const data = d.data || [];
      if (data.length > 0) {
        setArticles(data);
        latestDate.current = data[0]?.published_at;
        setFetching(false);
        stopPolling();
        startRefresh({ type:'stock-news', symbol:sym });
      }
    }, 5000);
  };

  useEffect(() => {
    stopPolling(); stopRefresh();
    setLoading(true); setArticles([]); setNewArticles([]);
    setFetching(false); setPage(1); setHasMore(true);
    latestDate.current = null;

    const timer = setTimeout(async () => {
      if (isStock) {
        const sym = view.symbol;

        // If we don't have a full company name (e.g. navigated via URL hash),
        // fetch it from the search suggest API and patch the view
        if (!view.companyName || view.companyName === sym) {
          fetch(`${SEARCH_API}/suggest?q=${sym}`)
            .then(r => r.json())
            .then(d => {
              if (d.success && d.data?.length) {
                const match = d.data.find(s => s.symbol === sym);
                if (match?.name) {
                  setView(prev => ({ ...prev, companyName: match.name }));
                }
              }
            })
            .catch(() => {});
        }

        const d = await fetch(`${API}?limit=100&symbol=${sym}`).catch(()=>({json:()=>({data:[]})}));
        const data = (await d.json()).data || [];
        setArticles(data);
        latestDate.current = data[0]?.published_at || null;
        setLoading(false);
        if (!data.length) {
          fetch(`${SEARCH_API}/news?symbol=${sym}`).catch(()=>{});
          setFetching(true);
          startPolling(sym);
        } else {
          startRefresh(view);
        }
      } else {
        const d = await fetch(buildUrl(1)).catch(()=>({json:()=>({data:[],pagination:{hasMore:false}})}));
        const json = await d.json();
        let data = json.data || [];
        if (!isExchange) data = filterGlobal(data);
        setArticles(data);
        latestDate.current = data[0]?.published_at || null;
        setHasMore(json.pagination?.hasMore ?? false);
        setLoading(false);
        startRefresh(view);
      }
    }, isStock ? 300 : 0);

    return () => { clearTimeout(timer); stopPolling(); stopRefresh(); };
  }, [view]); // eslint-disable-line

  const filteredExchange = isExchange ? articles.filter(a => {
    const sources = EXCHANGE_SOURCES[exchangeTab] || [];
    return sources.some(s => (a.source||'').toLowerCase().includes(s) || (a.tag_source_name||'').toLowerCase().includes(s));
  }) : [];

  const feedTitle       = isStock ? view.symbol : isExchange ? 'World Exchange' : view === 'feed' ? 'Global Feed' : view;
  const stockFiltered   = isStock ? articles.filter(a=>a.symbol===view.symbol) : articles;
  const displayArticles = isExchange ? filteredExchange : stockFiltered;
  const inWatchlist     = isStock && watchlist?.find(w=>w.symbol===view.symbol);
  const feedPrices      = useFeedPrices(displayArticles);
  const showFetching    = isStock && (loading || (fetching && !displayArticles.length));
  const newPillCount    = isExchange ? 0 : newArticles.length;

  // Whether the view has a proper full company name (different from the ticker)
  const hasFullName = isStock && view.companyName && view.companyName !== view.symbol;

  const loaderDiv = !isStock && !isExchange ? (
    <div ref={loaderRef} style={{ textAlign:'center', padding:'20px 0', color:'#9ca3af', fontSize:13 }}>
      {loadingMore && <Spinner size={24} />}
      {!hasMore && !loading && displayArticles.length > 0 && <span>You're all caught up ✓</span>}
    </div>
  ) : null;

  // ── Mobile ──────────────────────────────────────────────────────────────────
  if (isMobile) {
    return (
      <div style={{ background:'#f3f4f6', minHeight:'100vh', display:'flex', flexDirection:'column' }}>
        {toast && <WatchlistToast symbol={toast} />}
        <MobileHeader
          feedTitle={feedTitle}
          articleCount={displayArticles.length}
          isStockNews={isStockNews}
          isStockDash={isStockDash}
          view={view}
          setView={setView}
          watchlist={watchlist}
          onWatchlistClick={handleWatchlistClick}
          loading={loading}
        />
        {isExchange && (
          <div style={{ display:'flex', gap:8, padding:'10px 12px', overflowX:'auto', background:'#fff', borderBottom:'1px solid #f0f0f0' }}>
            {EXCHANGE_TABS.map(ex=><button key={ex.key} onClick={()=>setExchangeTab(ex.key)} style={{ padding:'6px 16px', borderRadius:20, fontSize:12, fontWeight:700, border:'none', background: exchangeTab===ex.key?ex.color:'#f3f4f6', color: exchangeTab===ex.key?'#fff':'#374151', cursor:'pointer', whiteSpace:'nowrap', flexShrink:0 }}>{ex.label}</button>)}
          </div>
        )}
        <div ref={scrollRef} style={{ flex:1, overflowY:'auto', padding:'12px' }}>
          {newPillCount > 0 && <NewArticlesPill count={newPillCount} onClick={loadNewArticles} />}
          {isStockDash && (
            <StockAnalysis
              symbol={view.symbol}
              companyName={view.companyName || view.symbol}
              sentiment={view.sentiment}
              watchlist={watchlist}
              onWatchlistClick={handleWatchlistClick}
              onBack={() => setView({ type:'stock-news', symbol:view.symbol, companyName:view.companyName })}
            />
          )}
          {!isStockDash && showFetching && <FetchingScreen symbol={view.symbol} />}
          {!isStockDash && loading && !isStock && <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:80, gap:12 }}><Spinner /><div style={{ fontSize:13, color:'#9ca3af' }}>Loading news...</div></div>}
          {!isStockDash && !showFetching && !loading && !displayArticles.length && <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:80, gap:12 }}><div style={{ fontSize:44 }}>📭</div><div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No news found</div></div>}
          {!isStockDash && !showFetching && displayArticles.map(a=><MobileNewsCard key={a.id} a={a} price={feedPrices[a.symbol]} watchlist={watchlist} setView={setView} onWatchlistClick={handleWatchlistClick} />)}
          {loaderDiv}
        </div>
      </div>
    );
  }

  // ── Desktop ──────────────────────────────────────────────────────────────────
  return (
    <main style={{ background:'#f3f4f6', borderRadius:12, padding:0, overflowY:'hidden', display:'flex', flexDirection:'column' }}>
      {toast && <WatchlistToast symbol={toast} />}

      {/* ── Top bar ── */}
      <div style={{ display:'flex', alignItems:'center', gap:10, padding:'16px 12px 14px', borderBottom:'1px solid #e5e7eb', flexShrink:0, background:'#fff', borderRadius:'12px 12px 0 0' }}>
        {view !== 'feed' && (
          <button onClick={()=>setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:18, color:'#6b7280', padding:0, flexShrink:0 }}>←</button>
        )}

        {/* Non-stock pages: show feed title + article count */}
        {!isStock && (
          <>
            <div style={{ fontSize:20, fontWeight:700, color:'#111' }}>{feedTitle}</div>
            {!loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:8 }}>{displayArticles.length} articles</span>}
          </>
        )}

        {/* Stock pages: show full company name + ticker below it */}
        {isStock && (
          <div style={{ display:'flex', flexDirection:'column', justifyContent:'center' }}>
            <div style={{ fontSize:19, fontWeight:800, color:'#111', lineHeight:1.2 }}>
              {hasFullName ? view.companyName : view.symbol}
            </div>
            {hasFullName && (
              <div style={{ fontSize:12, color:'#9ca3af', fontWeight:600, fontFamily:'monospace', marginTop:1 }}>
                {view.symbol}
              </div>
            )}
          </div>
        )}

        {/* Stock news view: watchlist + analysis buttons */}
        {isStockNews && (
          <div style={{ marginLeft:'auto', display:'flex', gap:8, alignItems:'center' }}>
            <button
              onClick={()=>handleWatchlistClick(view.symbol)}
              style={{ padding:'6px 14px', borderRadius:8, fontSize:13, fontWeight:600, cursor:'pointer', background: inWatchlist?'#2563eb':'#eff6ff', color: inWatchlist?'#fff':'#2563eb', border:'1px solid #bfdbfe', transition:'all 0.2s' }}
            >
              {inWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
            </button>
            <button
              onClick={() => setView({ type:'stock', symbol:view.symbol, companyName:view.companyName, sentiment:view.sentiment })}
              style={{ padding:'6px 16px', borderRadius:8, fontSize:13, fontWeight:700, cursor:'pointer', background:'#2563eb', color:'#fff', border:'none', display:'flex', alignItems:'center', gap:6 }}
            >
              Stock Analysis →
            </button>
          </div>
        )}

        {/* Stock dashboard view: only watchlist button */}
        {isStockDash && (
          <button
            onClick={()=>handleWatchlistClick(view.symbol)}
            style={{ marginLeft:'auto', padding:'6px 16px', borderRadius:8, fontSize:13, fontWeight:600, cursor:'pointer', background: inWatchlist?'#2563eb':'#eff6ff', color: inWatchlist?'#fff':'#2563eb', border:'1px solid #bfdbfe', transition:'all 0.2s' }}
          >
            {inWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
          </button>
        )}
      </div>

      {isExchange && (
        <div style={{ display:'flex', gap:8, padding:'12px 12px 0' }}>
          {EXCHANGE_TABS.map(ex=><button key={ex.key} onClick={()=>setExchangeTab(ex.key)} style={{ padding:'6px 18px', borderRadius:20, fontSize:12, fontWeight:700, border: exchangeTab===ex.key?'none':'1.5px solid #e5e7eb', background: exchangeTab===ex.key?ex.color:'#fff', color: exchangeTab===ex.key?'#fff':'#374151', cursor:'pointer' }}>{ex.label}</button>)}
        </div>
      )}

      <div style={{ overflowY:'auto', padding:'12px', flex:1 }}>
        {newPillCount > 0 && <NewArticlesPill count={newPillCount} onClick={loadNewArticles} />}
        {isStockDash && (
          <StockAnalysis
            symbol={view.symbol}
            companyName={view.companyName || view.symbol}
            sentiment={view.sentiment}
            watchlist={watchlist}
            onWatchlistClick={handleWatchlistClick}
            onBack={() => setView({ type:'stock-news', symbol:view.symbol, companyName:view.companyName })}
          />
        )}
        {!isStockDash && showFetching && <FetchingScreen symbol={view.symbol} />}
        {!isStockDash && loading && !isStock && <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:60, gap:12 }}><Spinner /><div style={{ fontSize:13, color:'#9ca3af' }}>Loading news...</div></div>}
        {!isStockDash && !showFetching && !loading && !displayArticles.length && <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:60, gap:12 }}><div style={{ fontSize:44 }}>📭</div><div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No news found</div></div>}
        {!isStockDash && !showFetching && displayArticles.map(a=><NewsCard key={a.id} a={a} price={feedPrices[a.symbol]} onWatchlist={onWatchlist} watchlist={watchlist} setView={setView} onWatchlistClick={handleWatchlistClick} />)}
        {loaderDiv}
      </div>
    </main>
  );
}