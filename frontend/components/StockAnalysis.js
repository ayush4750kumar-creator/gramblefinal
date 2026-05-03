import { useState, useEffect, useRef } from 'react';

const BASE             = 'https://gramblefinal-production.up.railway.app';
const REFRESH_INTERVAL = 15_000;
const RANGES           = ['1D', '5D', '1M', '6M', '1Y', '5Y'];

const UP    = '#16a34a';
const DN    = '#dc2626';
const UP_BG = 'rgba(22,163,74,0.09)';
const DN_BG = 'rgba(220,38,38,0.09)';

const SENT = {
  bullish:  { color: UP, label: '▲ Bullish today' },
  bearish:  { color: DN, label: '▼ Bearish today' },
  positive: { color: UP, label: '▲ Bullish today' },
  negative: { color: DN, label: '▼ Bearish today' },
  neutral:  { color: '#6b7280', label: '● Neutral today' },
};

// ── Simulated series ──────────────────────────────────────────────────────────
function buildSeries(livePrice, prevClose, range) {
  const counts = { '1D':78,'5D':25,'1M':22,'6M':26,'1Y':52,'5Y':60 };
  const labelers = {
    '1D': i => { const m=i*5; const h=9+Math.floor((m+30)/60); const mn=(m+30)%60; return `${h}:${mn.toString().padStart(2,'0')}`; },
    '5D': i => ['Mon','Tue','Wed','Thu','Fri'][Math.floor(i/5)%5],
    '1M': i => `Apr ${i+3}`,
    '6M': i => ['Nov','Dec','Jan','Feb','Mar','Apr'][Math.floor(i*6/26)]??'',
    '1Y': i => ['May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr'][Math.floor(i/4.3)]??'',
    '5Y': i => `${2021+Math.floor(i/12)}`,
  };
  const offsets = {'1D':0,'5D':0.02,'1M':0.05,'6M':0.12,'1Y':0.22,'5Y':0.45};
  const n     = counts[range];
  const start = livePrice*(1-offsets[range]);
  const arr   = Array.from({length:n},(_,i)=>{
    const trend = start+(livePrice-start)*(i/(n-1));
    const noise = (Math.random()-0.45)*livePrice*0.006;
    return { t:labelers[range](i), v:Math.max(trend+noise,start*0.85) };
  });
  arr[arr.length-1].v = livePrice;
  return arr;
}

// ── Spinner ───────────────────────────────────────────────────────────────────
function Spinner({ size=20 }) {
  return (
    <>
      <div style={{width:size,height:size,border:'2px solid #e5e7eb',borderTop:'2px solid #2563eb',borderRadius:'50%',animation:'_sa_spin .8s linear infinite',flexShrink:0}}/>
      <style>{`@keyframes _sa_spin{to{transform:rotate(360deg)}}`}</style>
    </>
  );
}

// ── Main chart — exactly like the screenshot ─────────────────────────────────
function MainChart({ series, prevClose, isUp, range, setRange }) {
  const wrapRef = useRef(null);
  const [w, setW]         = useState(600);
  const [hover, setHover] = useState(null);
  const color   = isUp ? UP : DN;
  const fillClr = isUp ? UP_BG : DN_BG;

  useEffect(()=>{
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(([e])=>setW(e.contentRect.width));
    ro.observe(wrapRef.current);
    return ()=>ro.disconnect();
  },[]);

  // chart dims — left labels like screenshot
  const H=200, ml=52, mr=12, mt=10, mb=36;
  const cw=w-ml-mr, ch=H-mt-mb;

  const tabSt = active => ({
    padding:'6px 12px', fontSize:12, cursor:'pointer', border:'none',
    background:'transparent', fontFamily:'inherit',
    color: active?'#111':'#9ca3af',
    borderBottom:`2px solid ${active?color:'transparent'}`,
    fontWeight: active?700:400, marginBottom:-1,
  });

  if (!series?.length) return (
    <div style={{padding:'0 0 8px'}}>
      <div style={{display:'flex',borderBottom:'1px solid #f0f0f0',marginBottom:8}}>
        {RANGES.map(r=><button key={r} onClick={()=>setRange(r)} style={tabSt(range===r)}>{r}</button>)}
      </div>
      <div style={{height:H,display:'flex',alignItems:'center',justifyContent:'center'}}>
        <Spinner size={28}/>
      </div>
    </div>
  );

  const vals = series.map(d=>d.v);
  const rng  = Math.max(...vals)-Math.min(...vals)||1;
  const minV = Math.min(...vals, prevClose??Infinity)-rng*0.08;
  const maxV = Math.max(...vals)+rng*0.08;
  const xOf  = i => ml+(i/(series.length-1))*cw;
  const yOf  = v => mt+ch-((v-minV)/(maxV-minV))*ch;
  const prevY = prevClose!=null ? yOf(prevClose) : null;

  // smooth bezier
  const pts = series.map((d,i)=>[xOf(i),yOf(d.v)]);
  let line = `M ${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  for(let i=1;i<pts.length;i++){
    const cpx=((pts[i-1][0]+pts[i][0])/2).toFixed(1);
    line+=` C ${cpx},${pts[i-1][1].toFixed(1)} ${cpx},${pts[i][1].toFixed(1)} ${pts[i][0].toFixed(1)},${pts[i][1].toFixed(1)}`;
  }
  const area = line+` L ${xOf(series.length-1).toFixed(1)},${(mt+ch).toFixed(1)} L ${xOf(0).toFixed(1)},${(mt+ch).toFixed(1)} Z`;

  // y-axis ticks (left side, like screenshot)
  const yTicks = Array.from({length:6},(_,i)=>maxV-((maxV-minV)/5)*i);
  // x-axis ticks — 5 evenly spaced
  const xIdxs  = [0,Math.floor(series.length*.2),Math.floor(series.length*.4),Math.floor(series.length*.6),Math.floor(series.length*.8),series.length-1];

  const onMove = e => {
    const rect = e.currentTarget.getBoundingClientRect();
    const mx   = e.clientX-rect.left-ml;
    const idx  = Math.max(0,Math.min(series.length-1,Math.round((mx/cw)*(series.length-1))));
    setHover({x:xOf(idx),y:yOf(series[idx].v),val:series[idx].v,label:series[idx].t});
  };

  return (
    <div style={{paddingBottom:4}}>
      {/* Range tabs */}
      <div style={{display:'flex',borderBottom:'1px solid #f0f0f0',marginBottom:4}}>
        {RANGES.map(r=><button key={r} onClick={()=>setRange(r)} style={tabSt(range===r)}>{r}</button>)}
      </div>

      <div ref={wrapRef} style={{width:'100%',position:'relative',userSelect:'none'}}>
        <svg width={w} height={H+mb} onMouseMove={onMove} onMouseLeave={()=>setHover(null)} style={{cursor:'crosshair',display:'block'}}>
          <defs>
            <linearGradient id="_sa_grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={color} stopOpacity="0.18"/>
              <stop offset="100%" stopColor={color} stopOpacity="0.01"/>
            </linearGradient>
          </defs>

          {/* horizontal grid lines + left y-labels */}
          {yTicks.map((v,i)=>(
            <g key={i}>
              <line x1={ml} x2={ml+cw} y1={yOf(v)} y2={yOf(v)} stroke="#f0f0f0" strokeWidth={1}/>
              <text x={ml-6} y={yOf(v)} textAnchor="end" dominantBaseline="middle" fontSize={10} fill="#9ca3af">
                {v>=1000 ? v.toFixed(0) : v.toFixed(2)}
              </text>
            </g>
          ))}

          {/* Previous close dashed */}
          {prevY!=null&&prevY>mt&&prevY<mt+ch&&(
            <>
              <line x1={ml} x2={ml+cw} y1={prevY} y2={prevY} stroke="#d1d5db" strokeWidth={1} strokeDasharray="5,3"/>
              <text x={ml-6} y={prevY} textAnchor="end" dominantBaseline="middle" fontSize={9} fill="#c0c0c0">Prev</text>
            </>
          )}

          {/* Area fill */}
          <path d={area} fill="url(#_sa_grad)"/>
          {/* Line */}
          <path d={line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"/>

          {/* x-axis labels */}
          {xIdxs.map(i=>(
            <text key={i} x={xOf(i)} y={H+mb-8} textAnchor="middle" fontSize={10} fill="#9ca3af">
              {series[i]?.t}
            </text>
          ))}

          {/* Hover crosshair */}
          {hover&&<>
            <line x1={hover.x} x2={hover.x} y1={mt} y2={mt+ch} stroke="rgba(0,0,0,0.08)" strokeWidth={1}/>
            <circle cx={hover.x} cy={hover.y} r={4} fill={color} stroke="#fff" strokeWidth={2}/>
            {/* value label on left y-axis */}
            <text x={ml-6} y={hover.y} textAnchor="end" dominantBaseline="middle" fontSize={10} fontWeight="700" fill={color}>
              {hover.val>=1000?hover.val.toFixed(2):hover.val.toFixed(4)}
            </text>
          </>}
        </svg>

        {/* Floating tooltip */}
        {hover&&(
          <div style={{
            position:'absolute',top:Math.max(4,hover.y-36),left:Math.min(hover.x+8,w-120),
            background:'rgba(17,17,17,0.85)',color:'#fff',
            fontSize:11,fontWeight:600,padding:'4px 9px',borderRadius:5,
            pointerEvents:'none',whiteSpace:'nowrap',
          }}>
            {hover.val>=1000?hover.val.toLocaleString('en-IN',{maximumFractionDigits:2}):hover.val.toFixed(4)} · {hover.label}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Volume bars ───────────────────────────────────────────────────────────────
function VolumeBars({ series, isUp }) {
  const wrapRef = useRef(null);
  const [w, setW] = useState(600);
  useEffect(()=>{
    if(!wrapRef.current)return;
    const ro=new ResizeObserver(([e])=>setW(e.contentRect.width));
    ro.observe(wrapRef.current);
    return()=>ro.disconnect();
  },[]);
  if(!series?.length)return null;
  const ml=52,mr=12,H=40;
  const cw=w-ml-mr;
  const vols=series.map((_,i)=>Math.abs(Math.sin(i*0.7+1)*100+Math.random()*60+40));
  const maxV=Math.max(...vols);
  const bw=Math.max(1,(cw/series.length)-0.5);
  return(
    <div ref={wrapRef} style={{width:'100%',marginTop:2}}>
      <svg width={w} height={H} style={{display:'block'}}>
        {vols.map((v,i)=>{
          const x=ml+(i/(series.length-1))*cw-bw/2;
          const bh=(v/maxV)*(H-4);
          const c=i%3===0?DN:UP;
          return<rect key={i} x={x} y={H-4-bh} width={bw} height={bh} fill={c} opacity={0.45}/>;
        })}
      </svg>
    </div>
  );
}

// ── Performance tab ───────────────────────────────────────────────────────────
function PerformanceTab({ price, livePrice, prevClose, isUp, diff, pct }) {
  const fmtNum = v => {
    if (v==null||v===''||isNaN(Number(v))) return '—';
    return Number(v).toLocaleString('en-IN',{maximumFractionDigits:2});
  };

  const metrics = [
    { label:'Open',       value: fmtNum(price?.open) },
    { label:'High',       value: fmtNum(price?.high) },
    { label:'Low',        value: fmtNum(price?.low) },
    { label:'Prev close', value: fmtNum(prevClose) },
    { label:'Mkt cap',    value: price?.marketCap ?? '—' },
    { label:'P/E ratio',  value: price?.pe!=null ? String(price.pe) : '—' },
    { label:'52-wk high', value: fmtNum(price?.high52w) },
    { label:'52-wk low',  value: fmtNum(price?.low52w) },
    { label:'Dividend',   value: price?.dividend!=null ? String(price.dividend) : '—' },
    { label:'Volume',     value: price?.volume!=null ? String(price.volume) : '—' },
  ];

  // Range performance
  const rangePerfCards = livePrice ? [
    {r:'5D',  off:0.02},
    {r:'1M',  off:0.05},
    {r:'3M',  off:0.09},
    {r:'6M',  off:0.12},
    {r:'1Y',  off:0.22},
    {r:'5Y',  off:0.45},
  ].map(({r,off})=>{
    const s=livePrice*(1-off), ch=livePrice-s, p=(ch/s)*100;
    return {r, pct:p, up:ch>=0};
  }) : [];

  return (
    <div>
      {/* Performance cards */}
      {rangePerfCards.length>0&&(
        <>
          <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:10}}>Price Performance</div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:8,marginBottom:20}}>
            {rangePerfCards.map(c=>(
              <div key={c.r} style={{padding:'10px 12px',background:'#f9fafb',borderRadius:8,border:'1px solid #e5e7eb'}}>
                <div style={{fontSize:11,color:'#9ca3af',marginBottom:3}}>{c.r} ago</div>
                <div style={{fontSize:14,fontWeight:700,color:c.up?UP:DN}}>{c.up?'+':''}{c.pct.toFixed(2)}%</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Key stats */}
      <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:10}}>Key Statistics</div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0 20px',marginBottom:20}}>
        {metrics.map(m=>(
          <div key={m.label} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'0.5px solid #f0f0f0',fontSize:13}}>
            <span style={{color:'#6b7280'}}>{m.label}</span>
            <span style={{fontWeight:600,color:'#111'}}>{m.value}</span>
          </div>
        ))}
      </div>

      {/* Analyst consensus */}
      <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:10}}>Analyst Consensus</div>
      {[
        {label:'Strong Buy',pct:58,color:UP},
        {label:'Buy',       pct:24,color:'#5DCAA5'},
        {label:'Hold',      pct:12,color:'#888780'},
        {label:'Sell',      pct:6, color:DN},
      ].map(c=>(
        <div key={c.label} style={{display:'flex',alignItems:'center',gap:10,marginBottom:8}}>
          <span style={{fontSize:12,color:'#6b7280',width:80,flexShrink:0}}>{c.label}</span>
          <div style={{flex:1,height:6,background:'#f0f0f0',borderRadius:3,overflow:'hidden'}}>
            <div style={{width:`${c.pct}%`,height:'100%',background:c.color,borderRadius:3}}/>
          </div>
          <span style={{fontSize:12,fontWeight:600,color:'#111',width:34,textAlign:'right'}}>{c.pct}%</span>
        </div>
      ))}
    </div>
  );
}

// ── Stats Graphs tab ──────────────────────────────────────────────────────────
function StatsGraphsTab({ livePrice }) {
  // Simulated quarterly revenue data
  const quarters = ['Q1 24','Q2 24','Q3 24','Q4 24','Q1 25','Q2 25','Q3 25','Q4 25'];
  const revenue  = [42,45,48,51,49,54,58,62].map(v=>v+(Math.random()*4-2));
  const profit   = [8,9,10,11,10,12,13,15].map(v=>v+(Math.random()*1.5-0.75));
  const eps      = [12.4,13.1,14.2,15.0,14.6,16.2,17.8,19.4].map(v=>v+(Math.random()*0.5-0.25));

  const BarChart = ({ data, label, color, unit='' }) => {
    const wrapRef=useRef(null);
    const [w,setW]=useState(300);
    useEffect(()=>{
      if(!wrapRef.current)return;
      const ro=new ResizeObserver(([e])=>setW(e.contentRect.width));
      ro.observe(wrapRef.current);
      return()=>ro.disconnect();
    },[]);
    const H=100,ml=30,mr=8,mt=8,mb=24;
    const cw=w-ml-mr,ch=H-mt-mb;
    const maxV=Math.max(...data)*1.1;
    const bw=Math.max(4,(cw/data.length)*0.6);
    const gap=(cw/data.length);
    return(
      <div style={{padding:'14px 16px',background:'#f9fafb',borderRadius:10,border:'1px solid #e5e7eb'}}>
        <div style={{fontSize:11,color:'#6b7280',fontWeight:600,marginBottom:8}}>{label}</div>
        <div ref={wrapRef} style={{width:'100%'}}>
          <svg width={w} height={H} style={{display:'block'}}>
            {data.map((v,i)=>{
              const bh=(v/maxV)*ch;
              const x=ml+i*gap+gap/2-bw/2;
              return<g key={i}>
                <rect x={x} y={mt+ch-bh} width={bw} height={bh} fill={color} rx={2}/>
                <text x={x+bw/2} y={H-6} textAnchor="middle" fontSize={8} fill="#9ca3af">{quarters[i]}</text>
              </g>;
            })}
            {/* y-axis */}
            <text x={ml-4} y={mt} textAnchor="end" fontSize={8} fill="#9ca3af">{(maxV).toFixed(0)}{unit}</text>
            <text x={ml-4} y={mt+ch} textAnchor="end" fontSize={8} fill="#9ca3af">0</text>
          </svg>
        </div>
        <div style={{fontSize:13,fontWeight:700,color:color,marginTop:2}}>
          {data[data.length-1].toFixed(1)}{unit} <span style={{fontSize:11,color:'#9ca3af',fontWeight:400}}>latest quarter</span>
        </div>
      </div>
    );
  };

  const statCards=[
    {label:'Beta',       value:'0.92', desc:'Low volatility vs market'},
    {label:'RSI (14)',   value:'54.2', desc:'Neutral momentum'},
    {label:'50-Day MA',  value: livePrice?(livePrice*0.97).toFixed(2):'—', desc:'Price above moving avg'},
    {label:'200-Day MA', value: livePrice?(livePrice*0.88).toFixed(2):'—', desc:'Long-term uptrend'},
    {label:'Avg Volume', value:'12.4M', desc:'30-day average'},
    {label:'Short Float',value:'1.8%',  desc:'Low short interest'},
  ];

  return(
    <div>
      <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:12}}>Financial Performance</div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10,marginBottom:20}}>
        <BarChart data={revenue} label="Revenue (₹Bn)" color="#2563eb" unit="B"/>
        <BarChart data={profit}  label="Net Profit (₹Bn)" color={UP} unit="B"/>
        <BarChart data={eps}     label="EPS (₹)" color="#9333ea"/>
        <BarChart data={revenue.map((_,i)=>revenue[i]-profit[i])} label="Operating Expense (₹Bn)" color="#f59e0b" unit="B"/>
      </div>

      <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:12}}>Technical Indicators</div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8}}>
        {statCards.map(c=>(
          <div key={c.label} style={{padding:'12px 14px',background:'#f9fafb',borderRadius:10,border:'1px solid #e5e7eb'}}>
            <div style={{fontSize:11,color:'#9ca3af',marginBottom:3}}>{c.label}</div>
            <div style={{fontSize:17,fontWeight:700,color:'#111',marginBottom:2}}>{c.value}</div>
            <div style={{fontSize:11,color:'#6b7280'}}>{c.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── All News tab ──────────────────────────────────────────────────────────────
function AllNewsTab({ symbol }) {
  const [news,    setNews]    = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(()=>{
    if(!symbol)return;
    setLoading(true);
    fetch(`${BASE}/api/news?limit=40&symbol=${symbol}`)
      .then(r=>r.json())
      .then(d=>{ setNews(d.data||[]); setLoading(false); })
      .catch(()=>setLoading(false));
  },[symbol]);

  const timeAgo = d => {
    if(!d)return'';
    const s=Math.floor((Date.now()-new Date(d).getTime())/1000);
    if(s<3600)return`${Math.floor(s/60)}m ago`;
    if(s<86400)return`${Math.floor(s/3600)}h ago`;
    return`${Math.floor(s/86400)}d ago`;
  };

  const SC = {bullish:UP,positive:UP,bearish:DN,negative:DN,neutral:'#6b7280'};

  if(loading)return<div style={{display:'flex',justifyContent:'center',paddingTop:32}}><Spinner size={24}/></div>;
  if(!news.length)return<div style={{textAlign:'center',paddingTop:32,color:'#9ca3af',fontSize:14}}>No news found for {symbol}</div>;

  return(
    <div>
      <div style={{fontSize:11,fontWeight:700,color:'#9ca3af',textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:10}}>
        {news.length} articles for {symbol}
      </div>
      {news.map((a,i)=>{
        const title = (a.title||'').replace(/^\[(NSE|BSE|SEC)\]\s*/i,'');
        const sc    = SC[a.sentiment_label]||'#6b7280';
        const arrow = (a.sentiment_label==='bullish'||a.sentiment_label==='positive')?'▲':'▼';
        const isNeutral = !a.sentiment_label||a.sentiment_label==='neutral';
        return(
          <a key={a.id||i} href={a.url} target="_blank" rel="noreferrer"
            style={{display:'flex',alignItems:'center',gap:10,padding:'10px 0',borderBottom:'1px solid #f3f4f6',textDecoration:'none',cursor:'pointer'}}
          >
            {/* Sentiment dot */}
            <div style={{width:6,height:6,borderRadius:'50%',background:isNeutral?'#d1d5db':sc,flexShrink:0,marginTop:1}}/>
            {/* Headline — one line */}
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontSize:13,fontWeight:500,color:'#111',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis',lineHeight:1.4}}>
                {title}
              </div>
              <div style={{display:'flex',alignItems:'center',gap:6,marginTop:2}}>
                <span style={{fontSize:11,color:'#9ca3af'}}>{timeAgo(a.published_at)}</span>
                <span style={{fontSize:11,color:'#d1d5db'}}>·</span>
                <span style={{fontSize:11,color:'#9ca3af'}}>{a.tag_source_name||a.source}</span>
                {!isNeutral&&<>
                  <span style={{fontSize:11,color:'#d1d5db'}}>·</span>
                  <span style={{fontSize:11,fontWeight:600,color:sc}}>{arrow} {a.sentiment_label}</span>
                </>}
              </div>
            </div>
          </a>
        );
      })}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function StockAnalysis({ symbol, companyName, sentiment, watchlist, onWatchlistClick, onBack }) {
  const [tab,    setTab]    = useState('performance');
  const [range,  setRange]  = useState('1D');
  const [price,  setPrice]  = useState(null);
  const [series, setSeries] = useState([]);
  const [loadP,  setLoadP]  = useState(true);
  const timerRef = useRef(null);

  useEffect(()=>{
    if(!symbol)return;
    const go=async()=>{
      setLoadP(true);
      try{
        const res  = await fetch(`${BASE}/api/price?symbols=${symbol}`);
        const json = await res.json();
        if(json.success&&json.data?.[symbol]) setPrice(json.data[symbol]);
      }catch(_){}
      setLoadP(false);
    };
    go();
    clearInterval(timerRef.current);
    timerRef.current=setInterval(go,REFRESH_INTERVAL);
    return()=>clearInterval(timerRef.current);
  },[symbol]);

  useEffect(()=>{
    if(!price)return;
    const lp   = price.price     ?? 0;
    const prev = price.prevClose ?? lp*0.97;
    setSeries(buildSeries(lp,prev,range));
  },[symbol,range,price]);

  const livePrice = price?.price     ?? null;
  const prevClose = price?.prevClose ?? null;
  const diff      = livePrice!=null&&prevClose!=null ? livePrice-prevClose : null;
  const pct       = diff!=null ? (diff/prevClose)*100 : null;
  const isUp      = diff!=null ? diff>=0 : true;
  const ss        = SENT[sentiment?.toLowerCase()] ?? SENT.neutral;
  const inWL      = watchlist?.some(w=>w.symbol===symbol);

  const mainTabSt = active => ({
    padding:'10px 18px', fontSize:13, cursor:'pointer', border:'none',
    fontFamily:'inherit', background:'transparent',
    color: active?'#111':'#6b7280',
    borderBottom:`2.5px solid ${active?'#111':'transparent'}`,
    fontWeight: active?700:500, marginBottom:-1,
  });

  return (
    <div style={{fontFamily:'inherit',paddingBottom:'2rem'}}>

      {/* Back */}
      <button onClick={onBack} style={{display:'inline-flex',alignItems:'center',gap:4,background:'none',border:'none',cursor:'pointer',fontSize:13,color:'#6b7280',padding:'0 0 12px',fontFamily:'inherit'}}>
        ← Back to news
      </button>

      {/* Stock name + watchlist */}
      <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:6}}>
        <div>
          <div style={{fontSize:12,color:'#9ca3af',fontWeight:500,marginBottom:2}}>{symbol} · NSE/BSE</div>
          <div style={{fontSize:19,fontWeight:700,color:'#111'}}>{companyName||symbol}</div>
        </div>
        <button
          onClick={()=>onWatchlistClick?.(symbol)}
          style={{padding:'7px 16px',borderRadius:8,fontSize:13,cursor:'pointer',fontFamily:'inherit',fontWeight:600,background:inWL?'#2563eb':'#f3f4f6',color:inWL?'#fff':'#374151',border:'none',marginTop:4,flexShrink:0}}
        >
          {inWL?'✓ Watchlisted':'+ Watchlist'}
        </button>
      </div>

      {/* Live price + change */}
      <div style={{marginBottom:12}}>
        {loadP ? (
          <div style={{display:'flex',alignItems:'center',gap:8,height:44}}>
            <Spinner/><span style={{fontSize:13,color:'#9ca3af'}}>Fetching live price…</span>
          </div>
        ) : (
          <>
            <div style={{display:'flex',alignItems:'baseline',gap:12}}>
              <span style={{fontSize:30,fontWeight:300,color:'#111',letterSpacing:'-0.5px'}}>
                {livePrice!=null ? livePrice.toLocaleString('en-IN',{maximumFractionDigits:2}) : '—'}
              </span>
              {diff!=null&&(
                <span style={{fontSize:14,color:isUp?UP:DN,fontWeight:600}}>
                  {isUp?'▲':'▼'} {isUp?'+':''}{diff.toFixed(2)} ({isUp?'+':''}{pct.toFixed(2)}%)
                </span>
              )}
            </div>
            <div style={{fontSize:12,color:ss.color,fontWeight:600,marginTop:2}}>{ss.label}</div>
          </>
        )}
      </div>

      {/* ── CHART — always on top, fixed ── */}
      <div style={{background:'#fff',border:'1px solid #e5e7eb',borderRadius:10,padding:'10px 10px 0',marginBottom:0}}>
        <MainChart series={series} prevClose={prevClose} isUp={isUp} range={range} setRange={setRange}/>
        <VolumeBars series={series} isUp={isUp}/>
      </div>

      {/* ── 3 TABS ── */}
      <div style={{display:'flex',borderBottom:'1px solid #e5e7eb',marginTop:16,marginBottom:16}}>
        <button onClick={()=>setTab('performance')} style={mainTabSt(tab==='performance')}>Performance</button>
        <button onClick={()=>setTab('graphs')}      style={mainTabSt(tab==='graphs')}>Stats Graphs</button>
        <button onClick={()=>setTab('news')}        style={mainTabSt(tab==='news')}>All News</button>
      </div>

      {/* Tab content */}
      {tab==='performance'&&(
        <PerformanceTab price={price} livePrice={livePrice} prevClose={prevClose} isUp={isUp} diff={diff} pct={pct}/>
      )}
      {tab==='graphs'&&(
        <StatsGraphsTab livePrice={livePrice}/>
      )}
      {tab==='news'&&(
        <AllNewsTab symbol={symbol}/>
      )}
    </div>
  );
}