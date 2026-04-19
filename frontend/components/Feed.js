import { useEffect, useState } from 'react';

const SENTIMENT = {
  bullish:  { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  bearish:  { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  positive: { bg:'#dcfce7', color:'#16a34a', label:'Bullish', arrow:'▲' },
  negative: { bg:'#fee2e2', color:'#dc2626', label:'Bearish', arrow:'▼' },
  neutral:  { bg:'#f3f4f6', color:'#6b7280', label:'Neutral', arrow:'●' },
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

function NewsCard({ a }) {
  const s = SENTIMENT[a.sentiment_label] || null;
  const cleanTitle = (a.title || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '');
  const cleanSummary = (a.summary_60w || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '');
  const summary = !isVader(cleanSummary) && cleanSummary !== cleanTitle && cleanSummary.length > 20 ? cleanSummary : null;
  const reason = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;
  const displayText = summary || reason;

  return (
    <div style={{
      borderBottom: '1px solid #f0f0f0',
      padding: '18px 0',
    }}>
      {/* Top meta row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
        <span style={{
          fontSize: 11, fontWeight: 700,
          background: '#f3f4f6', color: '#374151',
          padding: '2px 8px', borderRadius: 4, letterSpacing: 0.3
        }}>
          {a.symbol || 'Global News'}
        </span>

        {s && (
          <span style={{
            fontSize: 11, fontWeight: 700,
            background: s.bg, color: s.color,
            padding: '2px 8px', borderRadius: 4,
            display: 'flex', alignItems: 'center', gap: 3
          }}>
            <span style={{ fontSize: 9 }}>{s.arrow}</span> {s.label}
          </span>
        )}

        <span style={{ fontSize: 11, color: '#9ca3af' }}>{a.tag_source_name || a.source}</span>
        <span style={{ fontSize: 11, color: '#c4c4c4' }}>·</span>
        <span style={{ fontSize: 11, color: '#9ca3af' }}>{timeAgo(a.published_at)}</span>
      </div>

      {/* Title */}
      <a
        href={a.url}
        target="_blank"
        rel="noreferrer"
        style={{
          fontSize: 15, fontWeight: 600, color: '#111',
          lineHeight: 1.5, display: 'block', marginBottom: 10,
          textDecoration: 'none'
        }}
        onMouseEnter={e => e.currentTarget.style.color = '#2563eb'}
        onMouseLeave={e => e.currentTarget.style.color = '#111'}
      >
        {cleanTitle}
      </a>

      {/* Read Article button */}
      <a
        href={a.url}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: '#2563eb', color: '#fff',
          fontSize: 12, fontWeight: 600,
          padding: '7px 16px', borderRadius: 8,
          textDecoration: 'none', marginBottom: displayText ? 10 : 0,
          transition: 'background 0.15s'
        }}
        onMouseEnter={e => e.currentTarget.style.background = '#1d4ed8'}
        onMouseLeave={e => e.currentTarget.style.background = '#2563eb'}
      >
        Read Article <span style={{ fontSize: 14 }}>↗</span>
      </a>

      {/* Summary / Reason box */}
      {displayText && s && (
        <div style={{
          fontSize: 12, fontWeight: 500, fontStyle: 'italic',
          background: s.bg, color: s.color,
          padding: '8px 12px', borderRadius: 8,
          lineHeight: 1.6, marginTop: 2
        }}>
          {displayText}
        </div>
      )}

      {/* NSE fallback */}
      {!displayText && a.agent_source === 'nse' && (
        <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>
          Official NSE filing — no summary available
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
    <main style={{
      background: '#fff', borderRadius: 12,
      border: '1px solid #e5e7eb',
      padding: '20px 24px', overflowY: 'auto'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 18, paddingBottom: 14,
        borderBottom: '1px solid #e5e7eb'
      }}>
        {view !== 'feed' && (
          <button
            onClick={() => setView('feed')}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#6b7280', padding: 0 }}
          >←</button>
        )}
        <div style={{ fontSize: 20, fontWeight: 700, color: '#111' }}>
          {view === 'feed' ? 'Global Feed' : view}
        </div>
        {loading && <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 8 }}>Loading...</span>}
        {!loading && <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 8 }}>{articles.length} articles</span>}
      </div>

      {/* Empty state */}
      {!loading && articles.length === 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '65%', gap: 12
        }}>
          <div style={{ fontSize: 44 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#6b7280' }}>No real news found yet</div>
          <div style={{ fontSize: 13, color: '#9ca3af', textAlign: 'center', lineHeight: 1.7, maxWidth: 280 }}>
            The agents are fetching live market news. Check back in a few minutes.
          </div>
        </div>
      )}

      {/* Cards */}
      {articles.map(a => <NewsCard key={a.id} a={a} />)}
    </main>
  );
}