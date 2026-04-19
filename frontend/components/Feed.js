import { useEffect, useState } from 'react';

const SENTIMENT = {
  bullish:  { bg:'#dcfce7', color:'#16a34a', label:'Bullish' },
  bearish:  { bg:'#fee2e2', color:'#dc2626', label:'Bearish' },
  positive: { bg:'#dcfce7', color:'#16a34a', label:'Bullish' },
  negative: { bg:'#fee2e2', color:'#dc2626', label:'Bearish' },
  neutral:  { bg:'#f3f4f6', color:'#6b7280', label:'Neutral' },
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

export default function Feed({ user, view, setView }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = view === 'feed' ? '' : `&category=${encodeURIComponent(view)}`;
    fetch(`http://localhost:5000/api/news?limit=60${params}`)
      .then(r => r.json())
      .then(d => {
        const filtered = (d.data || []).filter(a => !isHindi(a.title));
        setArticles(filtered);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [view]);

  return (
    <main style={{ background:'#fff', borderRadius:12, border:'1px solid #e5e7eb', padding:'20px 24px', overflowY:'auto' }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:18, paddingBottom:14, borderBottom:'1px solid #e5e7eb' }}>
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

      {articles.map(a => {
        const s = SENTIMENT[a.sentiment_label] || null;
        const summary = !isVader(a.summary_60w) ? a.summary_60w : null;
        const reason = !isVader(a.sentiment_reason) ? a.sentiment_reason : null;

        return (
          <div key={a.id} style={{ borderBottom:'1px solid #f3f4f6', padding:'16px 0', display:'flex', gap:14 }}>
            {a.image_url && (
              <img src={a.image_url} alt="" style={{ width:90, height:68, objectFit:'cover', borderRadius:8, flexShrink:0 }}
                onError={e => e.target.style.display='none'} />
            )}
            <div style={{ flex:1 }}>
              <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:7, flexWrap:'wrap' }}>
                {a.symbol ? (
                  <span style={{ fontSize:11, fontWeight:600, background:'#f3f4f6', color:'#374151', padding:'2px 8px', borderRadius:4 }}>{a.symbol}</span>
                ) : (
                  <span style={{ fontSize:11, fontWeight:600, background:'#f3f4f6', color:'#374151', padding:'2px 8px', borderRadius:4 }}>Global News</span>
                )}
                {s && (
                  <span style={{ fontSize:11, fontWeight:700, background:s.bg, color:s.color, padding:'2px 8px', borderRadius:4 }}>{s.label}</span>
                )}
                <span style={{ fontSize:11, color:'#9ca3af' }}>{a.tag_source_name || a.source}</span>
                <span style={{ fontSize:11, color:'#9ca3af' }}>{(() => { const diff = Math.floor((Date.now() - new Date(a.published_at)) / 1000); if (diff < 60) return "just now"; if (diff < 3600) return `${Math.floor(diff/60)}m ago`; if (diff < 86400) return `${Math.floor(diff/3600)}h ago`; return `${Math.floor(diff/86400)}d ago`; })()}</span>
              </div>

              <a href={a.url} target="_blank" rel="noreferrer"
                style={{ fontSize:15, fontWeight:600, color:'#111', lineHeight:1.45, display:'block', marginBottom:6, textDecoration:'none' }}
                onMouseEnter={e => e.target.style.color='#2563eb'}
                onMouseLeave={e => e.target.style.color='#111'}>
                {(a.title || '').replace(/^\[(NSE|BSE|SEC)\]\s*/i, '')}
              </a>

              {summary && (
                <div style={{ fontSize:13, color:'#4b5563', lineHeight:1.65, marginBottom:4 }}>{summary}</div>
              )}

              {reason && (
                <div style={{ fontSize:11, color:'#9ca3af', fontStyle:'italic' }}>{reason}</div>
              )}
            </div>
          </div>
        );
      })}
    </main>
  );
}
