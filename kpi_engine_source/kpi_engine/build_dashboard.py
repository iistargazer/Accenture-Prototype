import json
from pathlib import Path

ROOT = Path(__file__).parent
scenarios = json.load(open(ROOT / "output" / "scenarios.json"))
DATA_JSON = json.dumps(scenarios)

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>KPI intelligence-to-action engine — prototype</title>
<style>
  :root{
    --bg:#F6F6F3; --panel:#FFFFFF; --ink:#1B1D1A; --ink-soft:#5B5D57; --line:#E1E0D8;
    --teal:#0F6E56; --teal-bg:#E1F5EE; --purple:#4B3F72; --purple-bg:#ECEAF4;
    --amber:#8A5A0B; --amber-bg:#FBEFDD; --red:#9A2F2F; --red-bg:#FBEAEA;
    --gray-bg:#EFEEE9;
    --mono: "SFMono-Regular", ui-monospace, Menlo, Consolas, monospace;
    --sans: -apple-system, "Inter", "Segoe UI", Helvetica, Arial, sans-serif;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.5}
  header{padding:28px 32px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
  header h1{margin:0 0 4px;font-size:20px;font-weight:600;letter-spacing:-.01em}
  header p{margin:0;color:var(--ink-soft);font-size:13.5px;max-width:780px}
  nav{display:flex;gap:2px;padding:0 32px;background:var(--panel);border-bottom:1px solid var(--line);overflow-x:auto}
  nav button{border:none;background:none;padding:12px 16px;font-size:13px;font-weight:500;color:var(--ink-soft);cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;font-family:var(--sans)}
  nav button.active{color:var(--ink);border-bottom-color:var(--teal)}
  nav button:hover{color:var(--ink)}
  main{max-width:980px;margin:0 auto;padding:26px 32px 80px}
  section{display:none}
  section.active{display:block}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px 22px;margin-bottom:16px}
  .card h2{margin:0 0 4px;font-size:15px;font-weight:600}
  .card .sub{color:var(--ink-soft);font-size:12.5px;margin-bottom:14px}
  .badge{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);font-size:10.5px;font-weight:600;padding:3px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:.03em}
  .b-sql{background:var(--teal-bg);color:var(--teal)}
  .b-rule{background:var(--amber-bg);color:var(--amber)}
  .b-corr{background:var(--gray-bg);color:var(--ink-soft)}
  .b-llm{background:var(--purple-bg);color:var(--purple)}
  .b-deny{background:var(--red-bg);color:var(--red)}
  .kv{display:flex;justify-content:space-between;font-size:13.5px;padding:6px 0;border-bottom:1px dashed var(--line)}
  .kv:last-child{border-bottom:none}
  .kv .k{color:var(--ink-soft)}
  .kv .v{font-family:var(--mono);font-weight:600}
  table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
  th{text-align:left;color:var(--ink-soft);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.03em;padding:6px 8px;border-bottom:1px solid var(--line)}
  td{padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}
  td.num{font-family:var(--mono);font-weight:600;white-space:nowrap}
  .pos{color:var(--teal)} .neg{color:var(--red)}
  .narrative{background:var(--purple-bg);border-left:3px solid var(--purple);border-radius:6px;padding:14px 16px;font-size:13.5px;white-space:pre-wrap;margin-top:10px}
  .narrative .tag{display:block;margin-bottom:8px}
  .confbar-track{background:var(--gray-bg);border-radius:6px;height:8px;overflow:hidden;margin-top:6px}
  .confbar-fill{height:100%;border-radius:6px}
  .pills{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
  .pill{background:var(--gray-bg);border-radius:20px;padding:5px 12px;font-size:12px;font-weight:500;cursor:pointer;border:1px solid transparent}
  .pill.active{background:var(--ink);color:#fff}
  .reasons{font-size:12.5px;color:var(--ink-soft);margin-top:8px}
  .reasons li{margin-bottom:3px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media (max-width:760px){.grid2{grid-template-columns:1fr}}
  .abstain-banner{background:var(--red-bg);color:var(--red);border-radius:8px;padding:10px 14px;font-size:13px;font-weight:600;margin-bottom:10px}
  .foot-note{color:var(--ink-soft);font-size:12px;margin-top:4px}
  code{font-family:var(--mono);background:var(--gray-bg);padding:1px 5px;border-radius:4px;font-size:12px}
  .stat-row{display:flex;gap:14px;flex-wrap:wrap}
  .stat{flex:1;min-width:130px;background:var(--gray-bg);border-radius:8px;padding:12px 14px}
  .stat .num-lg{font-family:var(--mono);font-size:20px;font-weight:700}
  .stat .lbl{font-size:11px;color:var(--ink-soft);text-transform:uppercase;letter-spacing:.03em}
</style>
</head>
<body>
<header>
  <h1>KPI intelligence-to-action engine</h1>
  <p>Every number on this page is tagged with the method that produced it. The narrative text (purple) is the only thing an LLM touches — it reads a structured evidence object and never computes a figure itself.</p>
</header>
<nav id="tabs"></nav>
<main id="app"></main>

<script>
const DATA = __DATA_JSON__;

const TABS = [
  {id:'alerts', label:'Alerts feed'},
  {id:'personas', label:'Persona comparison'},
  {id:'driver', label:'Driver breakdown'},
  {id:'abstain', label:'Abstention'},
  {id:'security', label:'Security & entitlements'},
  {id:'feedback', label:'Feedback loop'},
  {id:'telemetry', label:'Telemetry & cost'},
];

function methodBadge(method){
  if(!method) return '<span class="badge b-corr">n/a</span>';
  if(method.startsWith('price_volume_mix') || method.startsWith('z_score') || method.startsWith('pct_change')) return `<span class="badge b-sql">stat / SQL</span>`;
  if(method.startsWith('rule_lookup')) return `<span class="badge b-rule">rule-based</span>`;
  if(method.startsWith('pearson_correlation')) return `<span class="badge b-corr">correlation</span>`;
  return `<span class="badge b-corr">${method}</span>`;
}

function fmtPct(x){ if(x===null||x===undefined) return 'n/a'; const s = x>=0?'+':''; return `${s}${x.toFixed(1)}%`; }
function signClass(x){ return x>0?'pos':(x<0?'neg':''); }

function driverTable(drivers){
  let rows = drivers.map(d => `
    <tr>
      <td>${d.name}</td>
      <td class="num ${signClass(d.contribution_pct||0)}">${fmtPct(d.contribution_pct)}</td>
      <td>${d.direction}</td>
      <td>${methodBadge(d.method)}</td>
      <td style="color:var(--ink-soft);font-size:12px">${d.source}</td>
    </tr>`).join('');
  return `<table><tr><th>Driver</th><th>Contribution</th><th>Direction</th><th>Method</th><th>Source</th></tr>${rows}</table>`;
}

function evidenceCard(ev, opts={}){
  const confColor = ev.confidence >= 0.7 ? 'var(--teal)' : (ev.confidence >= 0.45 ? 'var(--amber)' : 'var(--red)');
  return `
  <div class="kv"><span class="k">KPI</span><span class="v">${ev.display_name}${ev.region?` (${ev.region})`:''}</span></div>
  <div class="kv"><span class="k">Period</span><span class="v">${ev.period}</span></div>
  <div class="kv"><span class="k">Movement</span><span class="v ${signClass(ev.pct_change)}">${fmtPct(ev.pct_change)} (\$${ev.prior_value.toLocaleString()} → \$${ev.latest_value.toLocaleString()})</span></div>
  <div class="kv"><span class="k">Materiality</span><span class="v">${ev.is_material ? 'material' : 'not material'} ${methodBadge('z_score')}</span></div>
  <div class="kv"><span class="k">Lineage</span><span class="v" style="font-weight:400;font-size:12px;text-align:right">${ev.lineage}</span></div>
  <div class="kv"><span class="k">Source freshness</span><span class="v" style="font-weight:400;font-size:12px">${Object.entries(ev.freshness).map(([k,v])=>`${k}: ${v}`).join(', ')}</span></div>
  <div style="margin-top:14px">
    <div class="kv"><span class="k">Confidence</span><span class="v" style="color:${confColor}">${(ev.confidence*100).toFixed(0)}%</span></div>
    <div class="confbar-track"><div class="confbar-fill" style="width:${ev.confidence*100}%;background:${confColor}"></div></div>
    <ul class="reasons">${ev.confidence_reasons.map(r=>`<li>${r}</li>`).join('')}</ul>
  </div>
  ${ev.drivers.length ? `<div style="margin-top:14px"><strong style="font-size:12.5px;text-transform:uppercase;letter-spacing:.03em;color:var(--ink-soft)">Driver ranking</strong>${driverTable(ev.drivers)}</div>` : ''}
  `;
}

function narrativeBlock(result){
  return `<div class="narrative"><span class="tag badge b-llm">LLM narrative — ${result.narrative_model}</span>${result.narrative}</div>`;
}

function actionsBlock(actions){
  if(!actions || !actions.length) return '<p class="foot-note">No actions recommended (engine abstained or no lever mapped).</p>';
  return `<table><tr><th>Driver</th><th>Lever</th><th>Action</th><th>Owner</th><th>Monitoring</th></tr>` +
    actions.map(a=>`<tr><td>${a.driver}</td><td>${a.lever}</td><td style="max-width:220px">${a.action}</td><td>${a.owner}</td><td style="font-size:12px;color:var(--ink-soft)">${a.monitoring_plan}</td></tr>`).join('') +
    `</table>`;
}

function telemetryStats(t){
  return `<div class="stat-row">
    <div class="stat"><div class="num-lg">${t.total_latency_ms.toFixed(0)}ms</div><div class="lbl">total latency</div></div>
    <div class="stat"><div class="num-lg">${t.model_calls}</div><div class="lbl">model calls</div></div>
    <div class="stat"><div class="num-lg">${t.total_input_tokens + t.total_output_tokens}</div><div class="lbl">tokens (in+out)</div></div>
    <div class="stat"><div class="num-lg">\$${t.total_cost_usd.toFixed(5)}</div><div class="lbl">est. cost / insight</div></div>
  </div>`;
}

function render(){
  const nav = document.getElementById('tabs');
  nav.innerHTML = TABS.map(t=>`<button data-tab="${t.id}">${t.label}</button>`).join('');
  nav.querySelectorAll('button').forEach(b=>b.addEventListener('click', ()=>showTab(b.dataset.tab)));
  const app = document.getElementById('app');
  app.innerHTML = TABS.map(t=>`<section id="sec-${t.id}"></section>`).join('');

  renderAlerts();
  renderPersonas();
  renderDriverExplorer();
  renderAbstain();
  renderSecurity();
  renderFeedback();
  renderTelemetry();

  showTab('alerts');
}

function showTab(id){
  document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active', b.dataset.tab===id));
  document.querySelectorAll('main section').forEach(s=>s.classList.toggle('active', s.id==='sec-'+id));
}

function renderAlerts(){
  const el = document.getElementById('sec-alerts');
  const entries = Object.entries(DATA).filter(([k,v])=>!v.error);
  el.innerHTML = `<div class="card"><h2>Detected movements this run</h2><div class="sub">Ranked by materiality — z-score / pct-change vs trailing history, computed with pandas, zero LLM involvement.</div>` +
    entries.map(([k,v])=>{
      const ev = v.evidence;
      return `<div class="kv" style="align-items:flex-start">
        <span class="k">${ev.display_name}${ev.region?` · ${ev.region}`:''} <span style="color:var(--ink-soft);font-size:11px">(${k})</span></span>
        <span class="v ${signClass(ev.pct_change)}">${fmtPct(ev.pct_change)} ${ev.should_abstain?'<span class="badge b-deny">abstained</span>':(ev.is_material?'<span class="badge b-rule">material</span>':'')}</span>
      </div>`;
    }).join('') + `</div>`;
}

function renderPersonas(){
  const el = document.getElementById('sec-personas');
  const exec_ = DATA['multi_driver_revenue__exec'];
  const analyst = DATA['multi_driver_revenue__sales_analyst'];
  el.innerHTML = `<div class="card"><h2>Same evidence, two personas</h2>
    <div class="sub">Both personas are looking at the identical revenue movement (East / existing_A). The evidence object below is shared — only the narrative differs.</div>
    <div class="grid2">
      <div><h2 style="font-size:13px">VP Sales (exec)</h2>${narrativeBlock(exec_)}<p class="foot-note">${exec_.actions.length} action(s) surfaced</p></div>
      <div><h2 style="font-size:13px">Sales Analyst</h2>${narrativeBlock(analyst)}<p class="foot-note">${analyst.actions.length} action(s) surfaced</p></div>
    </div>
    <h2 style="margin-top:18px;font-size:13px">Shared evidence object</h2>
    ${evidenceCard(analyst.evidence)}
  </div>`;
}

function renderDriverExplorer(){
  const el = document.getElementById('sec-driver');
  const keys = Object.keys(DATA).filter(k=>!DATA[k].error);
  el.innerHTML = `<div class="card"><h2>Driver breakdown explorer</h2><div class="sub">Pick a scenario to see its full evidence object and recommended actions.</div>
    <div class="pills" id="driver-pills"></div>
    <div id="driver-detail"></div>
  </div>`;
  const pills = document.getElementById('driver-pills');
  pills.innerHTML = keys.map(k=>`<span class="pill" data-k="${k}">${k}</span>`).join('');
  pills.querySelectorAll('.pill').forEach(p=>p.addEventListener('click', ()=>{
    pills.querySelectorAll('.pill').forEach(x=>x.classList.remove('active'));
    p.classList.add('active');
    showDriverDetail(p.dataset.k);
  }));
  pills.querySelector('.pill').classList.add('active');
  showDriverDetail(keys[0]);
}
function showDriverDetail(k){
  const r = DATA[k];
  document.getElementById('driver-detail').innerHTML = `
    ${evidenceCard(r.evidence)}
    ${narrativeBlock(r)}
    <h2 style="margin-top:16px;font-size:13px">Recommended actions</h2>
    ${actionsBlock(r.actions)}
  `;
}

function renderAbstain(){
  const el = document.getElementById('sec-abstain');
  const r = DATA['sparse_history_new_launch'];
  el.innerHTML = `<div class="card">
    <h2>Sparse-history + abstention</h2>
    <div class="sub">New product launch, 2 weeks of history. The engine explicitly declines to name a root cause instead of guessing.</div>
    <div class="abstain-banner">Engine abstained — confidence ${(r.evidence.confidence*100).toFixed(0)}%</div>
    ${evidenceCard(r.evidence)}
    ${narrativeBlock(r)}
  </div>`;
}

function renderSecurity(){
  const el = document.getElementById('sec-security');
  const denied = DATA['security_denied_cross_region'];
  const allowed = DATA['multi_driver_revenue__regional_manager_west'];
  el.innerHTML = `<div class="card">
    <h2>Row-level entitlement enforcement</h2>
    <div class="sub">Filtering happens on structured data before the LLM ever sees it — not by asking the model to "please not mention" a region.</div>
    <div class="grid2">
      <div>
        <span class="badge b-deny">access denied</span>
        <p style="font-size:13px;margin-top:8px">${denied.error}</p>
      </div>
      <div>
        <span class="badge b-sql">access allowed (West only)</span>
        <p style="font-size:13px;margin-top:8px">${allowed.access_audit}</p>
      </div>
    </div>
    <h2 style="margin-top:16px;font-size:13px">Column-level redaction</h2>
    <p class="foot-note">Regional Manager - West has <code>margin</code> and <code>channel_cost</code> in its hidden_dimensions list (engine/security.py). Driver detail fields tied to those dimensions are replaced with <code>[redacted]</code> before the evidence object reaches the LLM.</p>
  </div>`;
}

function renderFeedback(){
  const el = document.getElementById('sec-feedback');
  const r = DATA['feedback_loop_after_2_false_alarms'];
  el.innerHTML = `<div class="card">
    <h2>Feedback → threshold adjustment loop</h2>
    <div class="sub">Two analysts flagged prior avg_selling_price alerts as false alarms. The engine surfaces a suggested (not auto-applied) threshold change on the next run.</div>
    <div class="kv"><span class="k">Feedback note</span><span class="v" style="font-weight:400">${r.feedback_loop.threshold_note}</span></div>
    <div class="kv"><span class="k">Suggested threshold</span><span class="v">${r.feedback_loop.suggested_threshold_pct}%</span></div>
    <p class="foot-note">Suggestion only — a human approves the change before it's written back to kpi_contracts.yaml. Kept manual deliberately for prototype safety.</p>
  </div>`;
}

function renderTelemetry(){
  const el = document.getElementById('sec-telemetry');
  const keys = Object.keys(DATA).filter(k=>!DATA[k].error);
  let totalCost=0, totalTokens=0, totalCalls=0;
  const rows = keys.map(k=>{
    const t = DATA[k].telemetry;
    totalCost += t.total_cost_usd; totalTokens += t.total_input_tokens+t.total_output_tokens; totalCalls += t.model_calls;
    return `<tr><td>${k}</td><td class="num">${t.total_latency_ms.toFixed(0)}ms</td><td class="num">${t.model_calls}</td><td class="num">${t.total_input_tokens+t.total_output_tokens}</td><td class="num">\$${t.total_cost_usd.toFixed(5)}</td></tr>`;
  }).join('');
  el.innerHTML = `<div class="card">
    <h2>Runtime telemetry</h2>
    <div class="sub">Per-run cost/latency accounting — this is what "LLM economics" looks like made concrete. Figures use a mock provider's token estimate; swap in real usage once a live API key is wired in.</div>
    ${telemetryStats({total_latency_ms: keys.reduce((s,k)=>s+DATA[k].telemetry.total_latency_ms,0), model_calls: totalCalls, total_input_tokens: totalTokens, total_output_tokens:0, total_cost_usd: totalCost})}
    <table style="margin-top:16px"><tr><th>Scenario</th><th>Latency</th><th>Model calls</th><th>Tokens</th><th>Cost</th></tr>${rows}</table>
  </div>`;
}

render();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA_JSON__", DATA_JSON)
out_path = ROOT / "output" / "dashboard.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({len(html)} bytes)")
