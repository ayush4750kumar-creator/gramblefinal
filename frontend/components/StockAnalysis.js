import { useState, useEffect, useRef } from 'react';

const BASE = 'https://gramblefinal-production.up.railway.app';
const REFRESH_INTERVAL = 15_000;
const RANGES = ['1D', '5D', '1M', '6M', '1Y', '5Y'];
const UP = '#1a9e6a';
const DN = '#e24b4a';

const SENT = {
  bullish:  { bg: '#d4f0e4', color: '#0f6e56', label: '▲ Bullish' },
  bearish:  { bg: '#fee2e2', color: '#dc2626', label: '▼ Bearish' },
  positive: { bg: '#d4f0e4', color: '#0f6e56', label: '▲ Bullish' },
  negative: { bg: '#fee2e2', color: '#dc2626', label: '▼ Bearish' },
  neutral:  { bg: '#f3f4f6', color: '#6b7280', label: '● Neutral' },
};

function buildSeries(livePrice, prevClose, range) {
  const counts = { '1D':78, '5D':25, '1M':22, '6M':26, '1Y':52, '5Y':60 };
  const labelers = {
    '1D': i => { const m = i * 5; const h = 9 + Math.floor((m+30)/60); const min = (m+30)%60; return `${h}:${min.toString().padStart(2,'0')}`; },
    '5D': i => ['Mon','Tue','Wed','Thu','Fri'][Math.floor(i/5)%5],
    '1M': i => `Apr ${i+3}`,
    '6M': i => ['Nov','Dec','Jan','Feb','Mar','Apr'][Math.floor(i*6/26)]??'',
    '1Y': i => ['May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr'][Math.floor(i/4.3)]??'',
    '5Y': i => `${2021+Math.floor(i/12)}`,
  };
  const startOffsets = { '1D':0, '5D':0.02, '1M':0.05, '6M':0.12, '1Y':0.22, '5Y':0.45 };
  const n = counts[range];
  const start = livePrice * (1 - startOffsets[range]);
  const arr = Array.from({ length:n }, (_,i) => {
    const trend = start + (livePrice - start) * (i/(n-1));
    const noise = (Math.random()-0.45) * livePrice * 0.005;
    return { t: labelers[range](i), v: Math.max(trend+noise, start*0.88) };
  });
  arr[arr.length-1].v = livePrice;
  return arr;
}

function Spinner() {
  return (
    <>
      <div style={{ width:22, height:22, border:'2px solid #e5e7eb', borderTop:'2px solid #2563eb', borderRadius:'50%', animation:'sa-spin 0.8s linear infinite' }} />
      <style>{`@keyframes sa-spin{to{transform:rotate(360deg)}}`}</style>
    </>
  );
}

function LineChart({ series, prevClose, isUp }) {
  const wrapRef = useRef(null);
  const [w, setW] = useState(560);
  const [hover, setHover] = useState(null);
  const color = isUp ? UP : DN;

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  if (!series?.length) return (
    <div style={{ height:220, display:'flex', alignItems:'center', justifyContent:'center' }}>
      <Spinner />
    </div>
  );

  const H=220, ml=8, mr=52, mt=16, mb=28;
  const cw = w-ml-mr, ch = H-mt-mb;
  const vals = series.map(d=>d.v);
  const range_ = Math.max(...vals)-Math.min(...vals);
  const minV = Math.min(...vals, prevClose??Infinity) - range_*0.1;
  const maxV = Math.max(...vals) + range_*0.1;
  const xOf = i => ml+(i/(series.length-1))*cw;
  const yOf = v => mt+ch-((v-minV)/(maxV-minV))*ch;
  const prevY = prevClose!=null ? yOf(prevClose) : null;

  // Smooth bezier path
  const pts = series.map((d,i)=>[xOf(i), yOf(d.v)]);
  let linePath = `M ${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  for (let i=1;i<pts.length;i++) {
    const cpx = ((pts[i-1][0]+pts[i][0])/2).toFixed(1);
    linePath += ` C ${cpx},${pts[i-1][1].toFixed(1)} ${cpx},${pts[i][1].toFixed(1)} ${pts[i][0].toFixed(1)},${pts[i][1].toFixed(1)}`;
  }
  const areaPath = linePath + ` L ${xOf(series.length-1).toFixed(1)},${(mt+ch).toFixed(1)} L ${xOf(0).toFixed(1)},${(mt+ch).toFixed(1)} Z`;

  const yTicks = Array.from({length:5},(_,i)=>minV+((maxV-minV)/4)*i);
  const xIdxs  = [0, Math.floor(series.length*0.25), Math.floor(series.length*0.5), Math.floor(series.length*0.75), series.length-1];
  const gradId = `g${color.replace('#','')}`;

  const onMove = e => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = e.clientX-rect.left-ml;
    const idx = Math.max(0,Math.min(series.length-1,Math.round((mx/cw)*(series.length-1))));
    setHover({ x:xOf(idx), y:yOf(series[idx].v), val:series[idx].v, label:series[idx].t });
  };

  return (
    <div ref={wrapRef} style={{ width:'100%', position:'relative', userSelect:'none' }}>
      <svg width={w} height={H} onMouseMove={onMove} onMouseLeave={()=>setHover(null)} style={{ cursor:'crosshair', display:'block' }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={color} stopOpacity="0.14"/>
            <stop offset="100%" stopColor={color} stopOpacity="0.01"/>
          </linearGradient>
        </defs>

        {yTicks.map((v,i) => <line key={i} x1={ml} x2={ml+cw} y1={yOf(v)} y2={yOf(v)} stroke="#f0f0f0" strokeWidth={1}/>)}

        {prevY!=null && prevY>mt && prevY<mt+ch && (
          <line x1={ml} x2={ml+cw} y1={prevY} y2={prevY} stroke="#d1d5db" strokeWidth={1} strokeDasharray="5,3"/>
        )}

        <path d={areaPath} fill={`url(#${gradId})`}/>
        <path d={linePath} fill="none" stroke={color} strokeWidth={2.2} strokeLinejoin="round" strokeLinecap="round"/>

        {yTicks.map((v,i) => <text key={i} x={ml+cw+6} y={yOf(v)} dominantBaseline="middle" fontSize={10} fill="#ccc">${v.toFixed(0)}</text>)}

        {prevY!=null && prevY>mt && prevY<mt+ch && (
          <text x={ml+cw+6} y={prevY-7} fontSize={9} fill="#ccc">Prev</text>
        )}

        {xIdxs.map(i => <text key={i} x={xOf(i)} y={H-5} textAnchor="middle" fontSize={10} fill="#ccc">{series[i]?.t}</text>)}

        {hover && <>
          <line x1={hover.x} x2={hover.x} y1={mt} y2={mt+ch} stroke="rgba(0,0,0,0.08)" strokeWidth={1}/>
          <circle cx={hover.x} cy={hover.y} r={5} fill={color} stroke="#fff" strokeWidth={2}/>
        </>}
      </svg>

      {hover && (
        <div style={{
          position:'absolute', top:Math.max(4,hover.y-40), left:hover.x,
          transform:'translateX(-50%)', background:'rgba(17,17,17,0.88)',
          color:'#fff', fontSize:12, fontWeight:600,
          padding:'5px 10px', borderRadius:6, pointerEvents:'none',
          whiteSpace:'nowrap', boxShadow:'0 2px 8px rgba(0,0,0,0.2)',
        }}>
          ${hover.val.toFixed(2)} · {hover.label}
        </div>
      )}
    </div>
  );
}

function HistoryCards({ livePrice, range }) {
  if (!livePrice || range==='1D') return null;
  const offsets = { '5D':0.02,'1M':0.05,'6M':0.12,'1Y':0.22,'5Y':0.45 };
  const offset = offsets[range]; if (!offset) return null;
  const start = livePrice*(1-offset);
  const change = livePrice-start;
  const pct = (change/start)*100;
  const isUp = change>=0;
  const label = {'5D':'5 days ago','1M':'1 month ago','6M':'6 months ago','1Y':'1 year ago','5Y':'5 years ago'}[range];
  return (
    <div style={{ display:'flex', gap:8, marginBottom:'1rem' }}>
      <div style={{ flex:1, padding:'10px 12px', background:'#f9fafb', borderRadius:8, border:'1px solid #e5e7eb' }}>
        <p style={{ fontSize:11, color:'#9ca3af', margin:'0 0 3px' }}>{label}</p>
        <p style={{ fontSize:14, fontWeight:600, color:'#111', margin:0 }}>${start.toFixed(2)}</p>
      </div>
      <div style={{ flex:1, padding:'10px 12px', background:'#f9fafb', borderRadius:8, border:'1px solid #e5e7eb' }}>
        <p style={{ fontSize:11, color:'#9ca3af', margin:'0 0 3px' }}>Change since</p>
        <p style={{ fontSize:14, fontWeight:600, color: isUp?UP:DN, margin:0 }}>
          {isUp?'+':''}{pct.toFixed(2)}% ({isUp?'+':''}${change.toFixed(2)})
        </p>
      </div>
    </div>
  );
}

export default function StockAnalysis({ symbol, companyName, sentiment, watchlist, onWatchlistClick, onBack }) {
  const [range,  setRange]  = useState('1D');
  const [price,  setPrice]  = useState(null);
  const [series, setSeries] = useState([]);
  const [loadP,  setLoadP]  = useState(true);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!symbol) return;
    const go = async () => {
      setLoadP(true);
      try {
        const res  = await fetch(`${BASE}/api/price?symbols=${symbol}`);
        const json = await res.json();
        if (json.success && json.data?.[symbol]) setPrice(json.data[symbol]);
      } catch (_) {}
      setLoadP(false);
    };
    go();
    clearInterval(timerRef.current);
    timerRef.current = setInterval(go, REFRESH_INTERVAL);
    return () => clearInterval(timerRef.current);
  }, [symbol]);

  useEffect(() => {
    if (!price) return;
    const lp   = price.price     ?? 0;
    const prev = price.prevClose ?? lp*0.97;
    setSeries(buildSeries(lp, prev, range));
  }, [symbol, range, price]);

  const livePrice = price?.price     ?? null;
  const prevClose = price?.prevClose ?? null;
  const diff      = livePrice!=null && prevClose!=null ? livePrice-prevClose : null;
  const pct       = diff!=null ? (diff/prevClose)*100 : null;
  const isUp      = diff!=null ? diff>=0 : true;
  const ss        = SENT[sentiment?.toLowerCase()] ?? SENT.neutral;
  const inWL      = watchlist?.some(w=>w.symbol===symbol);

  const fmtNum = v => v!=null && v!=='' && !isNaN(Number(v)) ? `$${Number(v).toFixed(2)}` : '—';

  const metrics = [
    { label:'Open',       value: fmtNum(price?.open) },
    { label:'High',       value: fmtNum(price?.high) },
    { label:'Low',        value: fmtNum(price?.low) },
    { label:'Prev close', value: fmtNum(prevClose) },
    { label:'Mkt cap',    value: price?.marketCap ?? '—' },
    { label:'P/E ratio',  value: price?.pe != null ? String(price.pe) : '—' },
    { label:'52-wk high', value: fmtNum(price?.high52w) },
    { label:'52-wk low',  value: fmtNum(price?.low52w) },
  ];

  const consensus = [
    { label:'Strong Buy', pct:58, color:UP },
    { label:'Buy',        pct:24, color:'#5DCAA5' },
    { label:'Hold',       pct:12, color:'#888780' },
    { label:'Sell',       pct:6,  color:DN },
  ];

  const tabSt = active => ({
    padding:'8px 14px', fontSize:13, cursor:'pointer', border:'none',
    fontFamily:'inherit', background:'transparent',
    color: active?'#1a73e8':'#6b7280',
    borderBottom:`2px solid ${active?'#1a73e8':'transparent'}`,
    fontWeight: active?600:400, marginBottom:-1, transition:'color 0.15s',
  });

  return (
    <div style={{ fontFamily:'inherit', paddingBottom:'2rem' }}>

      <button onClick={onBack} style={{ display:'inline-flex', alignItems:'center', gap:5, background:'none', border:'none', cursor:'pointer', fontSize:13, color:'#6b7280', padding:'0 0 14px', fontFamily:'inherit' }}>
        ← Back to feed
      </button>

      {/* Header */}
      <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', padding:'1.25rem', background:'#f9fafb', borderRadius:12, border:'1px solid #e5e7eb', marginBottom:'1.25rem' }}>
        <div>
          <p style={{ fontSize:13, fontWeight:500, color:'#6b7280', margin:'0 0 2px' }}>{symbol} · NSE/BSE</p>
          <p style={{ fontSize:18, fontWeight:600, color:'#111', margin:'0 0 10px' }}>{companyName||symbol}</p>
          {loadP ? (
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <Spinner/>
              <span style={{ fontSize:13, color:'#9ca3af' }}>Fetching live price…</span>
            </div>
          ) : (
            <>
              <p style={{ fontSize:32, fontWeight:400, color:'#111', margin:0, lineHeight:1.1 }}>
                {livePrice!=null ? `$${livePrice.toFixed(2)}` : '—'}
                <span style={{ fontSize:14, color:'#9ca3af', marginLeft:6 }}>USD</span>
              </p>
              {diff!=null && (
                <p style={{ fontSize:13, color: isUp?UP:DN, margin:'5px 0 0' }}>
                  {isUp?'▲':'▼'} {isUp?'+':''}${Math.abs(diff).toFixed(2)} ({isUp?'+':''}{pct.toFixed(2)}%) today
                </p>
              )}
            </>
          )}
        </div>
        <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap:8 }}>
          <span style={{ display:'inline-flex', alignItems:'center', gap:5, padding:'5px 12px', borderRadius:20, fontSize:12, fontWeight:500, background:ss.bg, color:ss.color }}>
            {ss.label} signal
          </span>
          <button
            onClick={()=>onWatchlistClick?.(symbol)}
            style={{ padding:'5px 13px', borderRadius:20, fontSize:12, cursor:'pointer', fontFamily:'inherit', fontWeight:500, transition:'all 0.15s', background:inWL?'#2563eb':'transparent', color:inWL?'#fff':'#6b7280', border:'1px solid '+(inWL?'#2563eb':'#d1d5db') }}
          >
            {inWL?'✓ Watchlisted':'+ Watchlist'}
          </button>
        </div>
      </div>

      {/* Range tabs */}
      <div style={{ display:'flex', borderBottom:'1px solid #e5e7eb', marginBottom:'0.75rem' }}>
        {RANGES.map(r=><button key={r} onClick={()=>setRange(r)} style={tabSt(range===r)}>{r}</button>)}
      </div>

      <HistoryCards livePrice={livePrice} range={range}/>

      {/* Chart — Google-style box */}
      <div style={{ border:'1px solid #e5e7eb', borderRadius:10, padding:'12px 0 4px', marginBottom:'1.5rem', background:'#fff', overflow:'hidden' }}>
        <LineChart series={series} prevClose={prevClose} isUp={isUp}/>
      </div>

      {/* Metrics */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0 24px', marginBottom:'1.5rem' }}>
        {metrics.map(m=>(
          <div key={m.label} style={{ display:'flex', justifyContent:'space-between', padding:'9px 0', borderBottom:'0.5px solid #e5e7eb', fontSize:13 }}>
            <span style={{ color:'#6b7280' }}>{m.label}</span>
            <span style={{ fontWeight:500, color:'#111' }}>{m.value}</span>
          </div>
        ))}
      </div>

      {/* Analyst consensus */}
      <div style={{ height:1, background:'#e5e7eb', margin:'0.5rem 0 1rem' }}/>
      <p style={{ fontSize:12, fontWeight:600, color:'#6b7280', textTransform:'uppercase', letterSpacing:'0.07em', margin:'0 0 10px' }}>Analyst consensus</p>
      {consensus.map(c=>(
        <div key={c.label} style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
          <span style={{ fontSize:12, color:'#6b7280', width:76 }}>{c.label}</span>
          <div style={{ flex:1, height:5, background:'#e5e7eb', borderRadius:3, overflow:'hidden' }}>
            <div style={{ width:`${c.pct}%`, height:'100%', background:c.color, borderRadius:3 }}/>
          </div>
          <span style={{ fontSize:12, fontWeight:500, color:'#111', width:32, textAlign:'right' }}>{c.pct}%</span>
        </div>
      ))}
    </div>
  );
}