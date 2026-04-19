import { useEffect, useState } from 'react';

const SENTIMENT = {
  bullish:  { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  bearish:  { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  positive: { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  negative: { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  neutral:  { bg:'#f3f4f6', color:'#6b7280', label:'Neutral', arrow:'●' },
};

const PLACEHOLDER = 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80';

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

function NewsCard({ a }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle = (a.title || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '');
  const cleanSummary = (a.summary_60w || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '');
  const summary = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;

  return (
    <div style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 20, marginBottom: 20 }}>

      {/* IMAGE — full width */}
      <div style={{ width: '100%', height: 200, borderRadius: 12, overflow: 'hidden', marginBottom: 12, position: 'relative' }}>
        <img
          src={PLACEHOLDER}
          alt=""
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
        {/* Sentiment badge overlaid on image */}
        {s && (
          <div style={{
            position: 'absolute', top: 12, left: 12,
            background: s.color, color: '#fff',
            fontSize: 11, fontWeight: 700,
            padding: '4px 10px', borderRadius: 6,
            display: 'flex', alignItems: 'center', gap: 4
          }}>
            {s.arrow} {s.label.toUpperCase()}
          </div>
        )}
      </div>

      {/* Time + Source */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, fontWeight: 700, background: '#f3f4f6', color: '#374151', padding: '2px 8px', borderRadius: 4 }}>
          {a.symbol || 'Global News'}
        </span>
        <span style={{ fontSize: 11, color: '#9ca3af' }}>{a.tag_source_name || a.source}</span>
        <span style={{ fontSize: 11, color: '#c4c4c4' }}>·</span>
        <span style={{ fontSize: 11, color: '#9ca3af' }}>{timeAgo(a.published_at)}</span>
      </div>

      {/* Read Article button — full width */}
      <a
        href={a.url}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          background: '#2563eb', color: '#fff',
          fontSize: 13, fontWeight: 600,
          padding: '10px 0', borderRadius: 8,
          textDecoration: 'none', marginBottom: 12,
          width: '100%'
        }}
        onMouseEnter={e => e.currentTarget.style.background = '#1d4ed8'}
        onMouseLeave={e => e.currentTarget.style.background = '#2563eb'}
      >
        Read Article <span style={{ fontSize: 15 }}>↗</span>
      </a>

      {/* Title */}
      <div style={{ fontSize: 15, fontWeight: 600, color: '#111', lineHeight: 1.5, marginBottom: 8 }}>
        {cleanTitle}
      </div>

      {/* Summary — plain text */}
      {summary && (
        <div style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.65, marginBottom: 8 }}>
          {summary}
        </div>
      )}

      {/* Sentiment reason — colored box */}
      {reason && s && (
        <div style={{
          fontSize: 12, fontStyle: 'italic',
          background: s.bg, color: s.color,
          padding: '8px 12px', borderRadius: 8, lineHeight: 1.6
        }}>
          {reason}
        </div>
      )}

    </div>
  );
}

export default function Feed({ user, view, setView }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

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
    <main style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: '20px 24px', overflowY: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18, paddingBottom: 14, borderBottom: '1px solid #e5e7eb' }}>
        {view !== 'feed' && (
          <button onClick={() => setView('feed')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#6b7280', padding: 0 }}>←</button>
        )}
        <div style={{ fontSize: 20, fontWeight: 700, color: '#111' }}>{view === 'feed' ? 'Global Feed' : view}</div>
        {loading && <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 8 }}>Loading...</span>}
        {!loading && <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 8 }}>{articles.length} articles</span>}
      </div>

      {!loading && articles.length === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '65%', gap: 12 }}>
          <div style={{ fontSize: 44 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#6b7280' }}>No real news found yet</div>
          <div style={{ fontSize: 13, color: '#9ca3af', textAlign: 'center', lineHeight: 1.7, maxWidth: 280 }}>The agents are fetching live market news. Check back in a few minutes.</div>
        </div>
      )}

      {articles.map(a => <NewsCard key={a.id} a={a} />)}
    </main>
  );
}