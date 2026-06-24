# Architecture

Diagrams of how hello-spec works. They render on GitHub. For the plain-language
version, see the [visual explainer](visual/index.html); for the spec/process
layering, see [`METHODOLOGY.md`](METHODOLOGY.md); for the file-by-file map, see
[`ELEMENT-MAP.md`](ELEMENT-MAP.md).

## The big picture

```mermaid
flowchart LR
  subgraph inputs[" "]
    CG["📕 CodeGuard rules<br/>(rules/)"]
    T["🏠 target/<br/>vulnerable + secure"]
    CFG["⚙️ config/evaluation.yaml"]
  end
  CG --> ENG
  T --> ENG
  CFG --> ENG
  ENG["🔍 Foundry mini-engine<br/>hello_spec/foundry/"]
  ENG --> OUT["📋 findings · issues · candidate fixes<br/>variants · attack paths · crashes · proposed rules"]
```

## The evaluation pipeline (the 8 core roles, §5)

```mermaid
flowchart TD
  O["Orchestrator §5.1<br/>spawns the fleet, takes operator input"]
  O --> I["Indexer §5.2<br/>symbols, call graph"]
  I --> C["Cartographer §5.3<br/>entry points, trust boundaries"]
  C --> D["Detector §5.4<br/>rule sweep (LLM-eval) + secret/dep/exploratory"]
  D -->|candidates| TR["Triager §5.5<br/>verdict + EVIDENCE GATE"]
  TR -->|true-positive| V["Validator §5.6<br/>clean-room reproduction → exploited"]
  TR --> Cov["Coverage-Guide §5.7<br/>checklist, coverage-complete"]
  V --> R["Reporter §5.8<br/>severity, issue, rollup (only writer)"]
  D -.->|rule-gap → Self-Improver §6.5| R
  subgraph gate["Evidence gate (Constitution I)"]
    TR
  end
```

The Triager is the heart: a finding is only `true-positive` if its reachability,
trust-boundary and impact citations **mechanically resolve** against the index —
the model reasons, the architecture decides.

## The extension roles (§6) — all implemented

```mermaid
flowchart TD
  store["Finding store<br/>(confirmed findings)"]
  store --> RM["Remediator §6.4<br/>propose + VERIFY a fix"]
  store --> VH["Variant-Hunter §6.2<br/>same pattern elsewhere"]
  store --> AM["Attack-Mapper §6.3<br/>foothold → impact chains"]
  gap["Rule-gap (CWE-208)"] --> SI["Self-Improver §6.5<br/>author + VERIFY a CodeGuard rule"]
  tgt["target/parser.py"] --> DT["Deep-Tester §6.1<br/>fuzz in a subprocess → crashes"]
  SI -.->|accepted by a human| CG2["📕 rules/ (prevention)"]
```

## The detection → prevention flywheel (Foundry's centrepiece)

```mermaid
flowchart LR
  sweep["Rule sweep<br/>catches known classes"] --> explore["Exploration<br/>finds what rules missed"]
  explore --> gap["Rule-gap recorded<br/>(FR-042)"]
  gap --> author["Self-Improver authors<br/>a CodeGuard rule"]
  author --> verify["Verified: next sweep<br/>catches the class"]
  verify --> accept["Human accepts →<br/>rules/ corpus grows"]
  accept --> prevent["Loads into IDE assistants<br/>= prevention at the keystroke"]
  accept --> sweep
```

## How it's built — the two-gate spec-driven process

```mermaid
flowchart LR
  seed["Foundry seed<br/>spec.md + constitution.md"] --> sk
  subgraph sk["spec-kit workflow"]
    direction LR
    sp["/speckit-specify"] --> pl["/speckit-plan"] --> tk["/speckit-tasks"] --> im["/speckit-implement"]
  end
  pl --> GA{"Gate A<br/>Constitution Check<br/>(architecture)"}
  im --> GB{"Gate B<br/>CodeGuard review<br/>(secure-coding)"}
  GA --> done["merge"]
  GB --> done
```

See [`METHODOLOGY.md`](METHODOLOGY.md) for what each gate checks and why CodeGuard
wears two hats (the Detector's rule corpus *and* the secure-coding gate).
