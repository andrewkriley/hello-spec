"""Showcase server tests — focus on the secure-coding surface (path containment)
and that the hub renders. No socket is bound; helpers are called directly.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "showcase_server", ROOT / "scripts" / "showcase_server.py")
srv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srv)


def test_serves_real_doc():
    p = srv.safe_doc_path("/docs/SHOWCASE.md")
    assert p is not None and p.name == "SHOWCASE.md"


def test_serves_nested_visual():
    assert srv.safe_doc_path("/docs/visual/index.html") is not None


def test_rejects_path_traversal():
    # Classic escapes must all resolve to None (no serving outside docs/).
    for bad in ["/docs/../config/evaluation.yaml",
                "/docs/../../etc/passwd",
                "/docs/visual/../../config/secrets.env.example",
                "/docs/"]:
        assert srv.safe_doc_path(bad) is None, bad


def test_rejects_missing_file():
    assert srv.safe_doc_path("/docs/does-not-exist.md") is None


def test_hub_html_renders():
    html = srv.build_hub_html()
    assert "hello-spec" in html and "/docs/visual/index.html" in html
    assert "/run?backend=" in html or "runScan(" in html
