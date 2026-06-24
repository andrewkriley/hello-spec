#!/usr/bin/env python3
"""A tiny, dependency-free local showcase web service for hello-spec.

Serves a single hub page that pulls the showcase together: the visual explainer
(embedded), the architecture diagrams (rendered), the docs, and a button that
runs a scan and streams the output into the page.

    python3 scripts/showcase_server.py            # http://127.0.0.1:8000
    python3 scripts/showcase_server.py --port 9001

Secure-coding notes (Gate B): binds to 127.0.0.1 only (never exposed); static
files are served only from docs/ with path-containment checks (no traversal); the
/run endpoint executes a FIXED command (no user input reaches a shell); the scan
defaults to the offline `stub` backend.
"""
from __future__ import annotations

import argparse
import mimetypes
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

REPO = Path(__file__).resolve().parents[1]
DOCS = (REPO / "docs").resolve()


def safe_doc_path(rel: str):
    """Resolve a request path under docs/ and reject anything that escapes it."""
    rel = rel.lstrip("/")
    if rel.startswith("docs/"):
        rel = rel[len("docs/"):]
    candidate = (DOCS / rel).resolve()
    if candidate == DOCS or DOCS not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def run_scan(backend: str = "stub") -> str:
    """Run one evaluation and return its text output. Fixed argv, no shell."""
    backend = backend if backend in ("stub", "cli", "api") else "stub"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "hello_spec.foundry.engine",
             "--config", "config/evaluation.yaml"],
            cwd=str(REPO), capture_output=True, text=True,
            timeout=600, env={**_env(), "FOUNDRY_LLM_BACKEND": backend})
    except subprocess.TimeoutExpired:
        return "scan timed out"
    return (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")


def _env():
    import os
    return dict(os.environ)


def build_hub_html() -> str:
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>hello-spec — showcase</title>
<style>
  :root{--ink:#23303a;--soft:#5b6b78;--line:#e7ddcf;--bg:#fbf7f0;--card:#fff;
        --guard:#1f9c8b;--foundry:#e8893b;--demo:#3f7fd6}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55}
  .wrap{max-width:1000px;margin:0 auto;padding:0 22px}
  header{padding:40px 0 18px;text-align:center;
    background:radial-gradient(1100px 320px at 50% -120px,#fff6e6 0,var(--bg) 70%)}
  header .kick{color:var(--foundry);font-weight:800;letter-spacing:.14em;text-transform:uppercase;font-size:.8rem}
  h1{font-size:2.1rem;margin:.2em 0}
  nav{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:10px}
  nav a{font-size:.9rem;text-decoration:none;color:var(--demo);background:#fff;
    border:1px solid var(--line);border-radius:999px;padding:6px 13px}
  section{padding:30px 0;border-top:1px solid var(--line)}
  h2{font-size:1.4rem;margin:0 0 6px}
  .muted{color:var(--soft)}
  .card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;
    box-shadow:0 8px 24px rgba(60,40,10,.05)}
  iframe{width:100%;height:560px;border:0;display:block}
  .btn{font:inherit;font-weight:700;cursor:pointer;border:0;border-radius:12px;color:#fff;
    padding:11px 18px;background:var(--demo)}
  .btn.secondary{background:#fff;color:var(--foundry);border:1px solid var(--foundry)}
  pre.out{background:#0f1720;color:#d7e2ec;border-radius:14px;padding:16px;overflow:auto;
    max-height:520px;font-size:12.5px;line-height:1.5;white-space:pre-wrap}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
  .mermaid{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:12px 0}
  footer{padding:30px 0 60px;color:var(--soft);font-size:.9rem;text-align:center}
  a{color:var(--demo)}
</style></head><body>
<header><div class="wrap">
  <div class="kick">local showcase</div>
  <h1>hello-spec</h1>
  <p class="muted">Project CodeGuard + the Foundry Security Spec, brought to life.</p>
  <nav>
    <a href="#explainer">Explainer</a><a href="#run">Run a scan</a>
    <a href="#architecture">Architecture</a><a href="#docs">Docs</a>
    <a href="/docs/visual/poster.pdf" target="_blank">Poster (PDF)</a>
  </nav>
</div></header>

<section id="explainer"><div class="wrap">
  <h2>The explainer</h2>
  <p class="muted">Plain-language, for any audience. Scroll, and open the "go deeper" sections.</p>
  <div class="card"><iframe src="/docs/visual/index.html" title="visual explainer"></iframe></div>
</div></section>

<section id="run"><div class="wrap">
  <h2>Run a scan</h2>
  <p class="muted">Runs the Foundry mini-engine against the deliberately-vulnerable
    target and shows every role's output. <b>stub</b> is instant and offline;
    <b>live</b> uses <code>claude -p</code> (slower, costs tokens).</p>
  <div class="row">
    <button class="btn" onclick="runScan('stub')">Run (stub · offline)</button>
    <button class="btn secondary" onclick="runScan('cli')">Run live (claude -p)</button>
    <span id="status" class="muted"></span>
  </div>
  <pre class="out" id="out">Click a button to run a scan…</pre>
</div></section>

<section id="architecture"><div class="wrap">
  <h2>Architecture</h2>
  <p class="muted">Rendered from <code>docs/ARCHITECTURE.md</code> (needs internet for
    the diagram renderer; otherwise see it on GitHub).</p>
  <div id="diagrams"></div>
</div></section>

<section id="docs"><div class="wrap">
  <h2>Docs</h2>
  <ul>
    <li><a href="/docs/SHOWCASE.md" target="_blank">SHOWCASE.md</a> — the guided tour</li>
    <li><a href="/docs/METHODOLOGY.md" target="_blank">METHODOLOGY.md</a> — how the 3 pieces fit</li>
    <li><a href="/docs/ELEMENT-MAP.md" target="_blank">ELEMENT-MAP.md</a> — every element → its file</li>
    <li><a href="/docs/security-review.md" target="_blank">security-review.md</a> — the engine's own review</li>
  </ul>
</div></section>

<footer>Local showcase server · binds to 127.0.0.1 only · teaching demo, not a product.</footer>

<script type="module">
  async function loadDiagrams(){
    try{
      const md = await (await fetch('/docs/ARCHITECTURE.md')).text();
      const blocks = [...md.matchAll(/```mermaid\\n([\\s\\S]*?)```/g)].map(m=>m[1]);
      const host = document.getElementById('diagrams');
      if(!blocks.length){host.innerHTML='<p class="muted">No diagrams found.</p>';return;}
      host.innerHTML = blocks.map(b=>`<pre class="mermaid">${b.replace(/</g,'&lt;')}</pre>`).join('');
      const {default:mermaid} = await import('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs');
      mermaid.initialize({startOnLoad:false,theme:'neutral'});
      await mermaid.run({querySelector:'.mermaid'});
    }catch(e){
      document.getElementById('diagrams').innerHTML =
        '<p class="muted">Could not render diagrams here (offline?). See '+
        '<a href="https://github.com/andrewkriley/hello-spec/blob/main/docs/ARCHITECTURE.md" target="_blank">ARCHITECTURE.md on GitHub</a>.</p>';
    }
  }
  window.runScan = async (backend)=>{
    const out=document.getElementById('out'), st=document.getElementById('status');
    out.textContent=''; st.textContent = backend==='stub'
      ? 'running (instant)…' : 'running live claude -p — this can take a minute…';
    try{
      const r = await fetch('/run?backend='+backend);
      out.textContent = await r.text();
    }catch(e){ out.textContent = 'error: '+e; }
    st.textContent='done.';
  };
  loadDiagrams();
</script>
</body></html>
"""


class ShowcaseHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(200, build_hub_html())
        if url.path == "/health":
            return self._send(200, "ok", "text/plain")
        if url.path == "/run":
            backend = parse_qs(url.query).get("backend", ["stub"])[0]
            return self._send(200, run_scan(backend), "text/plain; charset=utf-8")
        if url.path.startswith("/docs/"):
            path = safe_doc_path(url.path)
            if not path:
                return self._send(404, "not found", "text/plain")
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if path.suffix == ".md":
                ctype = "text/plain; charset=utf-8"
            return self._send(200, path.read_bytes(), ctype)
        return self._send(404, "not found", "text/plain")

    def log_message(self, *args):       # quiet by default
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="hello-spec local showcase server")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ShowcaseHandler)
    print(f"hello-spec showcase → http://127.0.0.1:{args.port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
