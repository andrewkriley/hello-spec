# Visual explainers

Plain-language, non-technical visuals of what hello-spec is and how it aligns to
**Project CodeGuard** and the **Foundry Security Spec**. Built around a
building-inspection analogy: CodeGuard = the building code, Foundry = a
trustworthy inspector, hello-spec = the model house you walk through.

| File | What it is |
|---|---|
| `index.html` | The full explainer — scroll-through page with optional "go deeper" sections. Just open it in any browser. |
| `poster.html` | A one-page, at-a-glance poster (A4 portrait). |
| `poster.pdf` | The poster, pre-rendered for printing / sharing. |

Both HTML files are **self-contained** (inline styles + inline SVG, no internet
needed) — they work offline and survive being emailed around.

### Re-rendering the poster PDF

Open `poster.html` in a browser → **Print → Save as PDF**, or regenerate with
headless Chrome:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="docs/visual/poster.pdf" docs/visual/poster.html
```

> The program the demo inspects is a small teaching example with deliberate flaws
> (plus a safe twin) — not a real product. The visuals say so explicitly.
