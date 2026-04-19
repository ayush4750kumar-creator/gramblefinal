import { useEffect, useState } from 'react';

const SENTIMENT = {
  bullish:  { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  bearish:  { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  positive: { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  negative: { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  neutral:  { bg:'#f3f4f6', color:'#6b7280', label:'Neutral', arrow:'●' },
};

const PLACEHOLDER = 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80';

const EXCHANGE_TABS = ['NSE','BSE','NASDAQ','NYSE','MCX','CRYPTO'];

const EXCHANGE_SOURCES = {
  NSE:    ['nse_announcements','nse','NSE India','NSE'],
  BSE:    ['bse','BSE','bse_announcements'],
  NASDAQ: ['nasdaq','NASDAQ','nasdaq.com'],
  NYSE:   ['nyse','NYSE'],
  MCX:    ['mcx','MCX'],
  CRYPTO: ['crypto','bitcoin','coindesk'],
};

function isHindi(text) {
  if (!text) return false;
  const hindiChars = (text.match(/[\u0900-\u097F]/g) || []).length;
  return hindiChars / text.length > 0.2;
}

function isVader(text) {
  if (!text) return true;
  return text.toLowerCase().includes('vader') || text.toLowerCase().includes('compound score');
}

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

const btnStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
  fontSize: 13, fontWeight: 600,
  padding: '10px 0', borderRadius: 20,
  textDecoration: 'none', flex: 1,
  background: '#e0f2fe', color: '#0284c7',
  border: '1.5px solid #bae6fd',
  cursor: 'pointer',
  transition: 'background 0.15s',
};

function NewsCard({ a, onWatchlist, watchlist }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle = (a.title || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '');
  const cleanSummary = (a.summary_60w || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '');
  const summary = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;
  const isCompany = !!a.symbol;
  const isWatchlisted = watchlist?.find(w => w.symbol === a.symbol);

  return (
    <div style={{ background:'#fff', borderRadius:14, border:'1px solid #e5e7eb', boxShadow:'0 2px 8px rgba(0,0,0,0.06)', marginBottom:16, overflow:'hidden' }}>
      <div style={{ width:'100%', height:180, position:'relative', overflow:'hidden' }}>
        <img src={PLACEHOLDER} alt="" style={{ width:'100%', height:'100%', objectFit:'cover' }} />
        {s && (
          <div style={{ position:'absolute', top:12, left:12, background:s.color, color:'#fff', fontSize:11, fontWeight:700, padding:'4px 10px', borderRadius:6 }}>
            {s.arrow} {s.label.toUpperCase()}
          </div>
        )}
        {isCompany && (
          <button onClick={() => onWatchlist && onWatchlist(a.symbol)} style={{
            position:'absolute', top:12, right:12,
            background: isWatchlisted ? '#2563eb' : 'rgba(255,255,255,0.92)',
            border:'1px solid #e5e7eb', borderRadius:6, padding:'4px 10px',
            fontSize:11, fontWeight:600, color: isWatchlisted ? '#fff' : '#374151', cursor:'pointer',
          }}>
            {isWatchlisted ? '✓ Watchlisted' : '+ Watchlist'}
          </button>
        )}
      </div>

      <div style={{ padding:'14px 16px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:10, flexWrap:'wrap' }}>
          <span style={{ fontSize:11, fontWeight:700, background:'#f3f4f6', color:'#374151', padding:'2px 8px', borderRadius:4 }}>
            {a.symbol || 'Global News'}
          </span>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{a.tag_source_name || a.source}</span>
          <span style={{ fontSize:11, color:'#c4c4c4' }}>·</span>
          <span style={{ fontSize:11, color:'#9ca3af' }}>{timeAgo(a.published_at)}</span>
        </div>

        <div style={{ display:'flex', gap:10, marginBottom:12 }}>
          <a href={a.url} target="_blank" rel="noreferrer" style={btnStyle}
            onMouseEnter={e => e.currentTarget.style.background='#bae6fd'}
            onMouseLeave={e => e.currentTarget.style.background='#e0f2fe'}>
            Read Article <span style={{ fontSize:15 }}>↗</span>
          </a>
          {isCompany && (
            <a href={`/stock/${a.symbol}`} style={btnStyle}
              onMouseEnter={e => e.currentTarget.style.background='#bae6fd'}
              onMouseLeave={e => e.currentTarget.style.background='#e0f2fe'}>
              Stock Analysis <span style={{ fontSize:14 }}>→</span>
            </a>
          )}
        </div>

        <div style={{ fontSize:15, fontWeight:700, color:'#111', lineHeight:1.5, marginBottom:8 }}>{cleanTitle}</div>

        {summary && <div style={{ fontSize:13, color:'#4b5563', lineHeight:1.65, marginBottom:8 }}>{summary}</div>}

        {reason && s && (
          <div style={{ fontSize:12, fontStyle:'italic', background:s.bg, color:s.color, padding:'8px 12px', borderRadius:8, lineHeight:1.6 }}>
            {reason}
          </div>
        )}
      </div>
    </div>
  );
}

function MarketView({ exchange, setView, onWatchlist, watchlist }) {
  const [tab, setTab] = useState(exchange);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`https://gramblefinal-production.up.railway.app/api/news?limit=200`)
      .then(r => r.json())
      .then(d => {
        const sources = EXCHANGE_SOURCES[tab] || [];
        const filtered = (d.data || []).filter(a => {
          const src = (a.source || '').toLowerCase();
          const srcName = (a.tag_source_name || '').toLowerCase();
          const agentSrc = (a.agent_source || '').toLowerCase();
          return sources.some(s => src.includes(s.toLowerCase()) || srcName.includes(s.toLowerCase()) || agentSrc.includes(s.toLowerCase()));
        });
        setArticles(filtered);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [tab]);

  return (
    <main style={{ background:'#f3f4f6', borderRadius:12, padding:'16px 12px', overflowY:'auto' }}>
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:14, padding:'4px 4px 14px', borderBottom:'1px solid #e5e7eb' }}>
        <button onClick={() => setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:18, color:'#6b7280', padding:0 }}>←</button>
        <div style={{ fontSize:20, fontWeight:700, color:'#111' }}>Markets</div>
        {loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:8 }}>Loading...</span>}
        {!loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:8 }}>{articles.length} articles</span>}
      </div>

      {/* Exchange tabs */}
      <div style={{ display:'flex', gap:8, marginBottom:16, flexWrap:'wrap' }}>
        {EXCHANGE_TABS.map(ex => (
          <button
            key={ex}
            onClick={() => setTab(ex)}
            style={{
              padding:'6px 16px', borderRadius:20, fontSize:12, fontWeight:700,
              border: tab === ex ? 'none' : '1.5px solid #e5e7eb',
              background: tab === ex ? '#2563eb' : '#fff',
              color: tab === ex ? '#fff' : '#374151',
              cursor:'pointer',
            }}
          >{ex}</button>
        ))}
      </div>

      {!loading && articles.length === 0 && (
        <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', paddingTop:60, gap:12 }}>
          <div style={{ fontSize:44 }}>📭</div>
          <div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No {tab} news found</div>
          <div style={{ fontSize:13, color:'#9ca3af', textAlign:'center' }}>Check back soon for {tab} updates.</div>
        </div>
      )}

      {articles.map(a => <NewsCard key={a.id} a={a} onWatchlist={onWatchlist} watchlist={watchlist} />)}
    </main>
  );
}

export default function Feed({ user, view, setView, onWatchlist, watchlist }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  // If market view
  if (view && view.startsWith('market_')) {
    const exchange = view.replace('market_', '');
    return <MarketView exchange={exchange} setView={setView} onWatchlist={onWatchlist} watchlist={watchlist} />;
  }

  useEffect(() => {
    const fetchNews = () => {
      const params = view === 'feed' ? '' : `&category=${encodeURIComponent(view)}`;
      fetch(`https://gramblefinal-production.up.railway.app/api/news?limit=200${params}`)
        .then(r => r.json())
        .then(d => {
          const filtered = (d.data || []).filter(a => !isHindi(a.title));
          setArticles(filtered);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    };
    setLoading(true);
    fetchNews();
    const interval = setInterval(fetchNews, 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, [view]);

  return (
    <main style={{ background:'#f3f4f6', borderRadius:12, padding:'16px 12px', overflowY:'auto' }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16, padding:'4px 4px 14px', borderBottom:'1px solid #e5e7eb' }}>
        {view !== 'feed' && (
          <button onClick={() => setView('feed')} style={{ background:'none', border:'none', cursor:'pointer', fontSize:18, color:'#6b7280', padding:0 }}>←</button>
        )}
        <div style={{ fontSize:20, fontWeight:700, color:'#111' }}>{view === 'feed' ? 'Global Feed' : view}</div>
        {loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:8 }}>Loading...</span>}
        {!loading && <span style={{ fontSize:12, color:'#9ca3af', marginLeft:8 }}>{articles.length} articles</span>}
      </div>

      {!loading && articles.length === 0 && (
        <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'65%', gap:12 }}>
          <div style={{ fontSize:44 }}>📭</div>
          <div style={{ fontSize:16, fontWeight:600, color:'#6b7280' }}>No real news found yet</div>
          <div style={{ fontSize:13, color:'#9ca3af', textAlign:'center', lineHeight:1.7, maxWidth:280 }}>The agents are fetching live market news. Check back in a few minutes.</div>
        </div>
      )}

      {articles.map(a => <NewsCard key={a.id} a={a} onWatchlist={onWatchlist} watchlist={watchlist} />)}
    </main>
  );
}