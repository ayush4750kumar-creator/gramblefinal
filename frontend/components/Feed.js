import { useEffect, useState, useRef } from 'react';

const SENTIMENT = {
  bullish:  { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  bearish:  { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  positive: { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  negative: { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  neutral:  { bg:'#f3f4f6', color:'#6b7280', label:'Neutral', arrow:'●' },
};

const PLACEHOLDER = 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80';
const API      = 'https://gramblefinal-production.up.railway.app/api/news';
const SEARCH_API = 'https://gramblefinal-production.up.railway.app/api/search';

const AUTO_REFRESH_INTERVAL = 60 * 1000; // 60 seconds

const EXCHANGE_TABS = [
  { key:'NSE', label:'NSE', color:'#7c3aed' },
  { key:'BSE', label:'BSE', color:'#ea580c' },
  { key:'NASDAQ', label:'NASDAQ', color:'#2563eb' },
  { key:'NYSE', label:'NYSE', color:'#16a34a' },
];
const EXCHANGE_SOURCES = {
  NSE: ['nse','nse_announcements','nse india','nseindia','economic times','moneycontrol','livemint','business standard','ndtv','financial express','zeebiz'],
  BSE: ['bse','bse_announcements','bombay','hindu business','cnbctv18'],
  NASDAQ: ['nasdaq','techcrunch','the verge','wired','reuters','bloomberg','cnbc','marketwatch'],
  NYSE: ['nyse','wall street','wsj','ap news','financial times','seeking alpha','yahoo finance'],
};

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

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  return isMobile;
}

// ── URL hash helpers — persist view across refresh ────────────────────────────
function viewToHash(view) {
  if (!view || view === 'feed') return '';
  if (view?.type === 'stock') return `stock/${view.symbol}`;
  if (typeof view === 'string') return `view/${encodeURIComponent(view)}`;
  return '';
}

function hashToView(hash) {
  const h = hash.replace(/^#/, '');
  if (!h) return 'feed';
  if (h.startsWith('stock/')) return { type: 'stock', symbol: h.replace('stock/', '').toUpperCase() };
  if (h.startsWith('view/')) return decodeURIComponent(h.replace('view/', ''));
  return 'feed';
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

// ── New articles pill ─────────────────────────────────────────────────────────
function NewArticlesPill({ count, onClick }) {
  return (
    <div onClick={onClick} style={{ position:'sticky', top:8, zIndex:20, display:'flex', justifyContent:'center', marginBottom:8, cursor:'pointer' }}>
      <div style={{ background:'#2563eb', color:'#fff', fontSize:13, fontWeight:700, padding:'8px 20px', borderRadius:20, boxShadow:'0 4px 16px rgba(37,99,235,0.35)', display:'flex', alignItems:'center', gap:8, userSelect:'none' }}>
        ↑ {count} new article{count > 1 ? 's' : ''} — tap to load
      </div>
    </div>
  );
}

function MobileNewsCard({ a, watchlist, setView, onWatchlistClick }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle = (a.title||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const cleanSummary = (a.summary_60w||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const summary = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;
  const isCompany = !!a.symbol && a.symbol !== 'MARKET';
  const isWatchlisted = watchlist?.find(w => w.symbol === a.symbol);

  return (
    <div style={{ background:'#fff', borderRadius:16, marginBottom:14, overflow:'hidden', boxShadow:'0 1px 4px rgba(0,0,0,0.08)' }}>
      <div style={{ width:'100%', height:200, position:'relative', overflow:'hidden' }}>
        <img src={a.image_url || PLACEHOLDER} alt="" style={{ width:'100%', height:'100%', objectFit:'cover' }} onError={e => { e.target.src = PLACEHOLDER; }} />
        <div style={{ position:'absolute', bottom:10, left:10, background:'rgba(0,0,0,0.65)', color:'#fff', fontSize:10, fontWeight:700, padding:'4px 10px', borderRadius:6, letterSpacing:0.5 }}>
          <div style={{ fontSize:9, opacity:0.8 }}>{a.tag_category?.toUpperCase() || 'MARKET'}</div>
          <div>{a.symbol || 'Global News'}</div>
        </div>
        {s && (
          <div style={{ position:'absolute', top:10, left:10, background:s.color, color:'#fff', fontSize:10, fontWeight:700, padding:'4px 10px', borderRadius:6 }}>
            {s.arrow} {s.label.toUpperCase()}
          </div>
        )}
        {isCompany && (
          <button onClick={() => onWatchlistClick(a.symbol)} style={{ position:'absolute', top:10, right:10, background: isWatchlisted ? '#2563eb' : 'rgba(255,255,255,0.92)', border:'none', borderRadius:8, padding:'6px 12px', fontSize:11, fontWeight:700, color: isWatchlisted ? '#fff' : '#374151', cursor:'pointer' }}>
            {isWatchlisted ? '✓ Watchlisted' : '+ Watchlist'}
          </button>
        )}
      </div>
      <div style={{ padding:'12px 14px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:10 }}>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{timeAgo(a.published_at)}</span>
          <span style={{ fontSize:11, color:'#c4c4c4' }}>·</span>
          <span style={{ fontSize:11, color:'#9ca3af', fontWeight:600 }}>{a.tag_source_name || a.source}</span>
        </div>
        <div style={{ display:'flex', gap:8, marginBottom:10 }}>
          <a href={a.url} target="_blank" rel="noreferrer" style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', gap:5, padding:'10px', borderRadius:10, background:'#f0f9ff', color:'#0284c7', fontSize:13, fontWeight:600, textDecoration:'none', border:'1px solid #bae6fd' }}>
            Read Article ↗
          </a>
          {isCompany && (
            <button onClick={() => setView({ type:'stock', symbol: a.symbol })} style={{ flex:1, padding:'10px', borderRadius:10, background:'#f0f9ff', color:'#0284c7', fontSize:13, fontWeight:600, border:'1px solid #bae6fd', cursor:'pointer' }}>
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

function NewsCard({ a, onWatchlist, watchlist, setView, onWatchlistClick }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle = (a.title||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const cleanSummary = (a.summary_60w||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
  const summary = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;
  const isCompany = !!a.symbol && a.symbol !== 'MARKET';
  const isWatchlisted = watchlist?.find(w => w.symbol === a.symbol);

  return (
    <div style={{ background:'#fff', borderRadius:14, border:'1px solid #e5e7eb', boxShadow:'0 2px 8px rgba(0,0,0,0.06)', marginBottom:16, overflow:'hidden' }}>
      <div style={{ width:'100%', height:180, position:'relative', overflow:'hidden' }}>
        <img src={a.image_url || PLACEHOLDER} alt="" style={{ width:'100%', height:'100%', objectFit:'cover' }} onError={e => { e.target.src = PLACEHOLDER; }} />
        {s && <div style={{ position:'absolute', top:12, left:12, background:s.color, color:'#fff', fontSize:11, fontWeight:700, padding:'4px 10px', borderRadius:6 }}>{s.arrow} {s.label.toUpperCase()}</div>}
        {isCompany && (
          <button onClick={() => onWatchlistClick(a.symbol)} style={{ position:'absolute', top:12, right:12, background: isWatchlisted ? '#2563eb' : 'rgba(255,255,255,0.92)', border:'1px solid #e5e7eb', borderRadius:6, padding:'4px 10px', fontSize:11, fontWeight:600, color: isWatchlisted ? '#fff' : '#374151', cursor:'pointer', transition:'all 0.2s' }}>
            {isWatchlisted ? '✓ Watchlisted' : '+ Watchlist'}
          </button>
        )}
      </div>
      <div style={{ padding:'14px 16px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:10, flexWrap:'wrap' }}>
          <span style={{ fontSize:11, fontWeight:700, background:'#f3f4f6', color:'#374151', padding:'2px 8px', borderRadius:4 }}>{a.symbol || 'Global News'}</span>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{a.tag_source_name || a.source}</span>
          <span style={{ fontSize:11, color:'#c4c4c4' }}>·</span>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{timeAgo(a.published_at)}</span>
        </div>
        <div style={{ display:'flex', gap:10, marginBottom:12 }}>
          <a href={a.url} target="_blank" rel="noreferrer" style={btnStyle} onMouseEnter={e => e.currentTarget.style.background='#bae6fd'} onMouseLeave={e => e.currentTarget.style.background='#e0f2fe'}>
            Read Article <span style={{ fontSize:15 }}>↗</span>
          </a>
          {isCompany && (
            <button onClick={() => setView({ type:'stock', symbol: a.symbol })} style={btnStyle} onMouseEnter={e => e.currentTarget.style.background='#bae6fd'} onMouseLeave={e => e.currentTarget.style.background='#e0f2fe'}>
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
      <div style={{ fontSize:28, fontWeight:800, color:'#111', letterSpacing:'-0.5px' }}>{symbol}</div>
      <div style={{ width:40, height:40, border:'3px solid #e5e7eb', borderTop:'3px solid #2563eb', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
      <div style={{ fontSize:14, color:'#6b7280', fontWeight:500 }}>Fetching news{dots}</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function MobileHeader({ feedTitle, articleCount, isStock, view, setView, watchlist, onWatchlistClick, loading }) {
  const inWatchlist = isStock && watchlist?.find(w => w.symbol === view.symbol);
  return (
    <div style={{ background:'#fff', padding:'14px 16px 12px', borderBottom:'1px solid #f0f0f0', position:'sticky', top:0, zIndex:10 }}>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        {view !== 'feed' && (
          <button onClick={() => setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:20, color:'#374151', padding:0, lineHeight:1 }}>←</button>
        )}
        <div style={{ fontSize:22, fontWeight:800, color:'#111', letterSpacing:'-0.3px' }}>{feedTitle}</div>
        {!loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:4 }}>{articleCount} articles</span>}
        {isStock && (
          <div style={{ marginLeft:'auto', display:'flex', gap:8 }}>
            <button onClick={() => onWatchlistClick(view.symbol)} style={{ padding:'7px 14px', borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer', background: inWatchlist ? '#2563eb' : '#f3f4f6', color: inWatchlist ? '#fff' : '#374151', border:'none' }}>
              {inWatchlist ? '✓ Watchlisted' : '+ Watchlist'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Feed({ user, view, setView, onWatchlist, watchlist }) {
  const [articles,     setArticles]     = useState([]);
  const [newArticles,  setNewArticles]  = useState([]); // queued new articles to show
  const [loading,      setLoading]      = useState(true);
  const [fetching,     setFetching]     = useState(false);
  const [exchangeTab,  setExchangeTab]  = useState('NSE');
  const [toast,        setToast]        = useState(null);
  const toastTimer     = useRef(null);
  const pollTimer      = useRef(null);
  const pollCount      = useRef(0);
  const refreshTimer   = useRef(null);
  const latestIdRef    = useRef(null); // track newest article id for auto-refresh
  const isMobile       = useIsMobile();

  const isStock    = view?.type === 'stock';
  const isExchange = view === 'World Exchange';

  // ── FIX 1: Persist view in URL hash so page refresh restores it ──────────
  useEffect(() => {
    // On mount — restore view from hash if present
    const hash = window.location.hash;
    if (hash && hash !== '#') {
      const restored = hashToView(hash);
      if (restored && restored !== 'feed') {
        setView(restored);
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Sync hash whenever view changes
    const hash = viewToHash(view);
    window.location.hash = hash;
  }, [view]);

  const handleWatchlistClick = (symbol) => {
    onWatchlist && onWatchlist(symbol);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(symbol);
    toastTimer.current = setTimeout(() => setToast(null), 2500);
  };

  // ── Fetch articles from /api/news ─────────────────────────────────────────
  const fetchArticles = (sym) => {
    const url = `${API}?limit=100&symbol=${sym}`;
    return fetch(url).then(r => r.json()).then(d => d.data || []);
  };

  const buildFeedUrl = () => {
    if (isExchange) return `${API}?limit=500`;
    if (view !== 'feed') return `${API}?limit=1200&category=${encodeURIComponent(view)}`;
    return `${API}?limit=1200`;
  };

  // ── FIX 2: Auto-refresh — silently check for new articles every 60s ───────
  const startAutoRefresh = (currentView) => {
    stopAutoRefresh();
    refreshTimer.current = setInterval(async () => {
      try {
        let fresh = [];
        if (currentView?.type === 'stock') {
          fresh = await fetchArticles(currentView.symbol);
        } else {
          const url = buildFeedUrl();
          const d = await fetch(url).then(r => r.json());
          fresh = d.data || [];
          // Apply same filters as initial load
          const bad = ['wrestlemania','wwe','cricket','ipl','bollywood','celebrity'];
          const allExchangeSources = Object.values(EXCHANGE_SOURCES).flat();
          fresh = fresh.filter(a => {
            const src = [(a.source||''), (a.tag_source_name||''), (a.agent_source||'')].join(' ').toLowerCase();
            return !allExchangeSources.some(s => src.includes(s)) && !isHindi(a.title) && !bad.some(k => (a.title||'').toLowerCase().includes(k));
          });
        }

        if (fresh.length === 0) return;

        // Find articles newer than the newest we already have
        const topId = latestIdRef.current;
        if (!topId) { latestIdRef.current = fresh[0]?.id; return; }
        const newer = fresh.filter(a => a.id > topId);
        if (newer.length > 0) {
          setNewArticles(newer);
        }
      } catch (_) {}
    }, AUTO_REFRESH_INTERVAL);
  };

  const stopAutoRefresh = () => {
    if (refreshTimer.current) { clearInterval(refreshTimer.current); refreshTimer.current = null; }
  };

  // Load new articles when user taps the pill
  const loadNewArticles = () => {
    if (newArticles.length === 0) return;
    setArticles(prev => {
      const existingIds = new Set(prev.map(a => a.id));
      const toAdd = newArticles.filter(a => !existingIds.has(a.id));
      const merged = [...toAdd, ...prev];
      latestIdRef.current = merged[0]?.id || latestIdRef.current;
      return merged;
    });
    setNewArticles([]);
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ── Poll every 5s until articles arrive (max 12 attempts = 60s) ──────────
  const startPolling = (sym) => {
    stopPolling();
    pollCount.current = 0;
    pollTimer.current = setInterval(async () => {
      pollCount.current += 1;
      if (pollCount.current > 12) { stopPolling(); setFetching(false); return; }
      const data = await fetchArticles(sym);
      if (data.length > 0) {
        setArticles(data);
        latestIdRef.current = data[0]?.id;
        setFetching(false);
        stopPolling();
        startAutoRefresh({ type: 'stock', symbol: sym });
      }
    }, 5000);
  };

  const stopPolling = () => {
    if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null; }
  };

  useEffect(() => {
    stopPolling();
    stopAutoRefresh();
    setLoading(true);
    setArticles([]);
    setNewArticles([]);
    setFetching(false);
    latestIdRef.current = null;

    const delay = isStock ? 300 : 0;
    const timer = setTimeout(async () => {
      if (isStock) {
        const sym = view.symbol;
        fetch(`${SEARCH_API}/news?symbol=${sym}`).catch(() => {});
        fetch(`${SEARCH_API}/news?symbol=${sym}`).catch(() => {});
        const data = await fetchArticles(sym).catch(() => []);
        setArticles(data);
        latestIdRef.current = data[0]?.id || null;
        setLoading(false);
        if (data.length === 0) {
          setFetching(true);
          startPolling(sym);
        } else {
          startAutoRefresh(view);
        }
      } else {
        const url = buildFeedUrl();
        fetch(url).then(r => r.json()).then(d => {
          let data = d.data || [];
          const bad = ['wrestlemania','wwe','cricket','ipl','bollywood','celebrity'];
          const allExchangeSources = Object.values(EXCHANGE_SOURCES).flat();
          data = data.filter(a => {
            const src = [(a.source||''), (a.tag_source_name||''), (a.agent_source||'')].join(' ').toLowerCase();
            return !allExchangeSources.some(s => src.includes(s)) && !isHindi(a.title) && !bad.some(k => (a.title||'').toLowerCase().includes(k));
          });
          setArticles(data);
          latestIdRef.current = data[0]?.id || null;
          setLoading(false);
          startAutoRefresh(view);
        }).catch(() => setLoading(false));
      }
    }, delay);

    return () => { clearTimeout(timer); stopPolling(); stopAutoRefresh(); };
  }, [view]);

  const filteredExchange = isExchange ? articles.filter(a => {
    const sources = EXCHANGE_SOURCES[exchangeTab]||[];
    return sources.some(s => (a.source||'').toLowerCase().includes(s) || (a.tag_source_name||'').toLowerCase().includes(s) || (a.agent_source||'').toLowerCase().includes(s));
  }) : [];

  const feedTitle       = isStock ? view.symbol : isExchange ? 'World Exchange' : view === 'feed' ? 'Global Feed' : view;
  // Safety filter: on stock pages, only show articles actually tagged with that symbol
  const stockFiltered   = isStock ? articles.filter(a => a.symbol === view.symbol) : articles;
  const displayArticles = isExchange ? filteredExchange : stockFiltered;
  const inWatchlist     = isStock && watchlist?.find(w => w.symbol === view.symbol);
  const showFetching    = isStock && (loading || (fetching && displayArticles.length === 0));

  // New articles pill — only for articles not in exchange tab
  const newPillCount = isExchange ? 0 : newArticles.length;

  if (isMobile) {
    return (
      <div style={{ background:'#f3f4f6', minHeight:'100vh', display:'flex', flexDirection:'column' }}>
        {toast && <WatchlistToast symbol={toast} />}
        <MobileHeader feedTitle={feedTitle} articleCount={displayArticles.length} isStock={isStock} view={view} setView={setView} watchlist={watchlist} onWatchlistClick={handleWatchlistClick} loading={loading} />
        {isExchange && (
          <div style={{ display:'flex', gap:8, padding:'10px 12px', overflowX:'auto', background:'#fff', borderBottom:'1px solid #f0f0f0' }}>
            {EXCHANGE_TABS.map(ex => (
              <button key={ex.key} onClick={() => setExchangeTab(ex.key)} style={{ padding:'6px 16px', borderRadius:20, fontSize:12, fontWeight:700, border:'none', background: exchangeTab===ex.key ? ex.color : '#f3f4f6', color: exchangeTab===ex.key ? '#fff' : '#374151', cursor:'pointer', whiteSpace:'nowrap', flexShrink:0 }}>{ex.label}</button>
            ))}
          </div>
        )}
        <div style={{ flex:1, overflowY:'auto', padding:'12px' }}>
          {newPillCount > 0 && <NewArticlesPill count={newPillCount} onClick={loadNewArticles} />}
          {showFetching && <FetchingScreen symbol={view.symbol} />}
          {loading && !isStock && (
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:80, gap:12 }}>
              <div style={{ width:36, height:36, border:'3px solid #e5e7eb', borderTop:'3px solid #2563eb', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              <div style={{ fontSize:13, color:'#9ca3af' }}>Loading news...</div>
            </div>
          )}
          {!showFetching && !loading && displayArticles.length === 0 && (
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:80, gap:12 }}>
              <div style={{ fontSize:44 }}>📭</div>
              <div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No news found</div>
            </div>
          )}
          {!showFetching && displayArticles.map(a => (
            <MobileNewsCard key={a.id} a={a} watchlist={watchlist} setView={setView} onWatchlistClick={handleWatchlistClick} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <main style={{ background:'#f3f4f6', borderRadius:12, padding:'0', overflowY:'hidden', display:'flex', flexDirection:'column' }}>
      {toast && <WatchlistToast symbol={toast} />}
      <div style={{ display:'flex', alignItems:'center', gap:10, padding:'16px 12px 14px', borderBottom:'1px solid #e5e7eb', flexShrink:0, background:'#fff', borderRadius:'12px 12px 0 0' }}>
        {view !== 'feed' && <button onClick={() => setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:18, color:'#6b7280', padding:0 }}>←</button>}
        <div style={{ fontSize:20, fontWeight:700, color:'#111' }}>{feedTitle}</div>
        {!loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:8 }}>{displayArticles.length} articles</span>}
        {isStock && (
          <button onClick={() => handleWatchlistClick(view.symbol)} style={{ marginLeft:'auto', padding:'6px 16px', borderRadius:8, fontSize:13, fontWeight:600, cursor:'pointer', background: inWatchlist ? '#2563eb' : '#eff6ff', color: inWatchlist ? '#fff' : '#2563eb', border:'1px solid #bfdbfe', transition:'all 0.2s' }}>
            {inWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
          </button>
        )}
      </div>
      {isExchange && (
        <div style={{ display:'flex', gap:8, padding:'12px 12px 0' }}>
          {EXCHANGE_TABS.map(ex => (
            <button key={ex.key} onClick={() => setExchangeTab(ex.key)} style={{ padding:'6px 18px', borderRadius:20, fontSize:12, fontWeight:700, border: exchangeTab===ex.key ? 'none' : '1.5px solid #e5e7eb', background: exchangeTab===ex.key ? ex.color : '#fff', color: exchangeTab===ex.key ? '#fff' : '#374151', cursor:'pointer' }}>{ex.label}</button>
          ))}
        </div>
      )}
      <div style={{ overflowY:'auto', padding:'12px', flex:1 }}>
        {newPillCount > 0 && <NewArticlesPill count={newPillCount} onClick={loadNewArticles} />}
        {showFetching && <FetchingScreen symbol={view.symbol} />}
        {loading && !isStock && (
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:60, gap:12 }}>
            <div style={{ width:36, height:36, border:'3px solid #e5e7eb', borderTop:'3px solid #2563eb', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <div style={{ fontSize:13, color:'#9ca3af' }}>Loading news...</div>
          </div>
        )}
        {!showFetching && !loading && displayArticles.length === 0 && (
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', paddingTop:60, gap:12 }}>
            <div style={{ fontSize:44 }}>📭</div>
            <div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No news found</div>
          </div>
        )}
        {!showFetching && displayArticles.map(a => (
          <NewsCard key={a.id} a={a} onWatchlist={onWatchlist} watchlist={watchlist} setView={setView} onWatchlistClick={handleWatchlistClick} />
        ))}
      </div>
    </main>
  );
}