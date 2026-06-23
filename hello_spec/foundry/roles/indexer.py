"""Indexer (Foundry spec.md §5.2 / FR-020-029).

Builds the code index every downstream role queries: symbols, their spans, the
call graph, and the function source. Crucially it exposes `resolves(file,
symbol, line)`, which the evidence gate uses to mechanically verify citations
(§7.3). The index is persisted atomically (Constitution XI).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..lifecycle.fingerprint import normalize_path
from ..substrate.persistence import atomic_write_json
from .base import Role


@dataclass
class FuncInfo:
    name: str
    file: str
    lineno: int
    end_lineno: int
    source: str
    calls: Set[str] = field(default_factory=set)
    decorators: List[str] = field(default_factory=list)
    reads_request: bool = False
    route_line: Optional[int] = None    # line of an @app.route-style decorator
    is_module_var: bool = False         # module-level assignment, not a function


class CodeIndex:
    def __init__(self) -> None:
        self.functions: Dict[str, FuncInfo] = {}      # "file::name" -> info
        self.files: Set[str] = set()

    def add(self, fn: FuncInfo) -> None:
        self.functions[f"{normalize_path(fn.file)}::{fn.name}"] = fn
        self.files.add(normalize_path(fn.file))

    def all(self) -> List[FuncInfo]:
        return list(self.functions.values())

    def get(self, file: str, name: str) -> Optional[FuncInfo]:
        return self.functions.get(f"{normalize_path(file)}::{name}")

    def resolves(self, file: str, symbol: str, line: int) -> bool:
        """A citation resolves iff the file is indexed, the symbol is a known
        function in it, and the cited line falls within that function's span."""
        fn = self.get(file, symbol)
        if fn is None:
            return False
        return fn.lineno <= line <= fn.end_lineno

    def to_dict(self) -> dict:
        return {
            "files": sorted(self.files),
            "functions": {
                k: {"file": v.file, "lineno": v.lineno, "end_lineno": v.end_lineno,
                    "calls": sorted(v.calls), "decorators": v.decorators,
                    "reads_request": v.reads_request, "route_line": v.route_line}
                for k, v in self.functions.items()
            },
        }


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel_file: str, src_lines: List[str]) -> None:
        self.rel_file = rel_file
        self.src_lines = src_lines
        self.funcs: List[FuncInfo] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        end = getattr(node, "end_lineno", node.lineno)
        source = "\n".join(self.src_lines[node.lineno - 1:end])
        calls: Set[str] = set()
        reads_request = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                calls.add(_call_name(sub.func))
            if isinstance(sub, ast.Attribute) and _root_name(sub) == "request":
                reads_request = True
            if isinstance(sub, ast.Name) and sub.id == "request":
                reads_request = True
        decorators, route_line = [], None
        for dec in node.decorator_list:
            dn = _call_name(dec.func if isinstance(dec, ast.Call) else dec)
            decorators.append(dn)
            if "route" in dn:
                route_line = dec.lineno
        self.funcs.append(FuncInfo(
            name=node.name, file=self.rel_file, lineno=node.lineno,
            end_lineno=end, source=source, calls=calls, decorators=decorators,
            reads_request=reads_request, route_line=route_line))
        self.generic_visit(node)


def _root_name(node: ast.AST) -> str:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ""


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_root_name(node)}.{node.attr}" if _root_name(node) else node.attr
    return ""


class Indexer(Role):
    name = "indexer"

    def build(self, target_dir: Path, tick: int) -> CodeIndex:
        self.heartbeat()
        index = CodeIndex()
        target_dir = Path(target_dir)
        for py in sorted(target_dir.rglob("*.py")):
            rel = str(py.relative_to(target_dir))
            text = py.read_text(encoding="utf-8")
            tree = ast.parse(text)
            visitor = _Visitor(rel, text.splitlines())
            visitor.visit(tree)
            for fn in visitor.funcs:
                index.add(fn)
            # Module-level assignments are symbols too (so the evidence gate can
            # resolve citations for module-scope secrets — FR-039 findings).
            for node in tree.body:
                targets = []
                if isinstance(node, ast.Assign):
                    targets = node.targets
                elif isinstance(node, ast.AnnAssign) and node.target:
                    targets = [node.target]
                for tgt in targets:
                    if isinstance(tgt, ast.Name):
                        index.add(FuncInfo(
                            name=tgt.id, file=rel, lineno=node.lineno,
                            end_lineno=getattr(node, "end_lineno", node.lineno),
                            source=text.splitlines()[node.lineno - 1],
                            is_module_var=True))
        self.emit(tick, "index",
                  f"indexed {len(index.files)} file(s), "
                  f"{len(index.functions)} function(s)")
        return index

    def persist(self, index: CodeIndex, path: Path) -> None:
        atomic_write_json(Path(path), index.to_dict())   # Constitution XI
