# Configuration

VertexMarkdown has no configuration file by design. A few optional drop-ins let you extend it without editing the code.

## Paths

| Env var override | Default | Purpose |
|---|---|---|
| `$XDG_CONFIG_HOME/vertexmarkdown/` | `~/.config/vertexmarkdown/` | User config (custom CSS, future plugins) |
| `$XDG_STATE_HOME/vertexmarkdown/snapshots/` | `~/.local/state/vertexmarkdown/snapshots/` | Auto-save history |
| `<doc>/assets/` | next to the document | Pasted images (relative) |
| `~/Pictures/vertexmarkdown/` | â€” | Pasted images for *untitled* buffers (absolute) |

## Custom CSS

Drop a file at `~/.config/vertexmarkdown/custom.css`. It is appended to the base preview stylesheet on every render, so rules defined there win.

Example â€” tweak the code font:

```css
pre, code, .codehilite { font-family: 'Cascadia Code', ui-monospace, monospace; }
```

Example â€” widen the reading column:

```css
.markdown-body { max-width: 1000px; }
```

Example â€” dark accent recolour:

```css
html[data-theme="dark"] {
  --accent: #a5e075;
  --selection: #3f7a1f;
}
```

CSS variables defined in `style.css`:

| Variable | Purpose |
|---|---|
| `--bg`, `--fg`, `--muted` | Background, foreground, secondary text |
| `--border`, `--accent`, `--selection` | UI chrome |
| `--code-bg`, `--code-fg`, `--kbd-bg` | Code surfaces |
| `--blockquote-border`, `--table-stripe` | Misc accents |

## Theme

- Auto-detected from `gtk-application-prefer-dark-theme` / `gtk-theme-name`.
- Manual toggle: `Ctrl+D`.
- Pygments code theme follows: `github-dark` in dark, `friendly` in light.

## Snapshot retention

- 30 per document.
- Filenames: `YYYYMMDD-HHMMSS.md`.
- Pruned on each save; no background job.

To wipe:

```bash
rm -rf ~/.local/state/vertexmarkdown/snapshots
```

## Desktop entry / MIME

`install.sh` registers `VertexMarkdown` as a handler for `text/markdown` and `text/plain`. To make it the default:

```bash
xdg-mime default vertexmarkdown.desktop text/markdown
xdg-mime default vertexmarkdown.desktop text/plain
```

## Command-line

```
vertexmarkdown [FILE]
VertexMarkdown -V / --version
```

Only one positional arg is accepted. All runtime behaviour is controlled from the UI.


