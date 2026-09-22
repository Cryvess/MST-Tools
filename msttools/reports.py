"""Self-contained, escaped HTML reports suitable for sharing offline."""
from html import escape

from .workspace import write_json, write_text


def html_report(data):
    e = lambda value: escape(str(value), quote=True)
    summary = data['summary']
    cards = ''.join(f'<article><strong>{e(value)}</strong><span>{e(label)}</span></article>'
                    for value, label in [(f"{data['score']}/100", 'Check score'),
                                         (f"{summary['files']:,}", 'Files indexed'),
                                         (f"{summary['lines']:,}", 'Text lines'),
                                         (len(data['findings']), 'Findings')])
    total = sum(data['languages'].values()) or 1
    languages = ''.join(f'<div class="language"><span>{e(name)}</span>'
                        f'<meter min="0" max="100" value="{count / total * 100:.2f}"></meter>'
                        f'<span>{count:,} lines</span></div>' for name, count in data['languages'].items())
    findings = ''.join(f'<tr data-level="{e(f["severity"])}"><td><b class="{e(f["severity"])}">'
                       f'{e(f["severity"].upper())}</b></td><td>{e(f["file"])}:{f["line"]}</td>'
                       f'<td>{e(f["rule"])}</td><td>{e(f["message"])}</td></tr>' for f in data['findings'])
    checks = ''.join(f'<span class="check">{"✓" if c["passed"] else "−"} {e(c["name"])}</span>'
                     for c in data['checks'])
    functions = ''.join(f'<tr><td>{e(f["function"])}</td><td>{e(f["file"])}:{f["line"]}</td>'
                        f'<td>{f["complexity"]}</td><td>{f["lines"]}</td></tr>' for f in data['functions'][:20])
    deps = ''.join(f'<tr><td>{e(d["ecosystem"])}</td><td>{e(d["name"])}</td>'
                  f'<td>{e(d["constraint"])}</td><td>{e(d["group"])}</td></tr>' for d in data['dependencies'])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>MSTTools · ''' + e(data['project']) + '''</title><style>
:root{color-scheme:dark;--bg:#0b1120;--panel:#131e30;--line:#273449;--muted:#a3b3c8;--accent:#5eead4}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#e5edf8;font:15px/1.65 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:48px 28px}header{border-bottom:1px solid var(--line);padding-bottom:30px}
.brand{letter-spacing:3px;color:var(--accent);font-weight:800}.version{color:var(--muted);letter-spacing:0;font-weight:400}
h1{font-size:clamp(30px,5vw,54px);letter-spacing:-2px;margin:22px 0 4px}p{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:28px 0}article{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:24px}
article strong{display:block;font-size:34px;color:var(--accent)}article span{text-transform:uppercase;font-size:11px;letter-spacing:2px;color:var(--muted)}
section{margin-top:36px}h2{font-size:18px}table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}
th{color:var(--muted);font-weight:500}td,th{padding:13px 12px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
.scroll{overflow:auto;border:1px solid var(--line);border-radius:10px}.high{color:#fb7185}.warning{color:#fbbf24}.info{color:var(--accent)}
.language{display:grid;grid-template-columns:160px 1fr 120px;gap:20px;align-items:center;margin:10px 0}meter{width:100%;height:12px;accent-color:var(--accent)}
.check{display:inline-block;padding:6px 14px;border:1px solid var(--line);border-radius:30px;margin:4px;color:var(--accent)}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
@media(max-width:650px){.cards{grid-template-columns:repeat(2,1fr)}.language{grid-template-columns:100px 1fr 80px;gap:8px}main{padding:24px 16px}}
@media print{body{background:white;color:#111}p,footer,th{color:#444}article{background:#f3f4f6}article strong,.check{color:#065f46}.cards{break-inside:avoid}}
</style></head><body><main><header><div class="brand">MSTTOOLS <span class="version">/ v''' + e(data['version']) + '''</span></div>
<h1>''' + e(data['project']) + '''</h1><p>Your workspace. Understood. · Local project review</p>
<small>Generated ''' + e(data['generated_at']) + '''</small></header><div class="cards">''' + cards + '''</div>
<section><h2>Project foundations</h2>''' + checks + '''</section><section><h2>Workspace composition</h2>''' + languages + '''</section>
<section><h2>Prioritized findings</h2><div class="scroll"><table><thead><tr><th>Level</th><th>Location</th><th>Rule</th><th>Action</th></tr></thead><tbody>''' + (findings or '<tr><td colspan="4">No findings from enabled checks.</td></tr>') + '''</tbody></table></div></section>
<section><h2>Python complexity · top 20 functions</h2><div class="scroll"><table><thead><tr><th>Function</th><th>Location</th><th>Complexity</th><th>Lines</th></tr></thead><tbody>''' + functions + '''</tbody></table></div></section>
<section><h2>Declared dependencies</h2><div class="scroll"><table><thead><tr><th>Ecosystem</th><th>Package</th><th>Constraint</th><th>Group</th></tr></thead><tbody>''' + deps + '''</tbody></table></div></section>
<footer>''' + e(data['scope']) + '''<br>Dependency inventory is not a vulnerability scan. Source snippets and credential values are excluded.</footer></main></body></html>'''


def export(data, output, force=False):
    if str(output).lower().endswith('.html'):
        write_text(output, html_report(data), force)
    elif str(output).lower().endswith('.json'):
        write_json(output, data, force)
    else:
        raise ValueError('Report output must end with .html or .json')
