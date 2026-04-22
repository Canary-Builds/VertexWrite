# Troubleshooting

Quick fixes for common issues. If your problem isn't here, check [FAQ](FAQ.md) or open an issue.

## Launch

### `ModuleNotFoundError: No module named 'gi'`

PyGObject isn't installed. On Debian/Ubuntu:

```bash
sudo apt install python3-gi
```

### `ValueError: Namespace WebKit2 not available for version 4.1`

WebKit2 4.1 typelib is missing. On Ubuntu 24.04+ it's `gir1.2-webkit2-4.1`. Older distros ship `4.0` â€” VertexMarkdown does not support that version.

```bash
sudo apt install gir1.2-webkit2-4.1
```

### `ValueError: Namespace GtkSource not available for version 4`

```bash
sudo apt install gir1.2-gtksource-4
```

### `ModuleNotFoundError: No module named 'markdown'`

```bash
sudo apt install python3-markdown python3-pygments
```

### Window opens blank, no preview

1. Is GPU acceleration broken? Try: `WEBKIT_DISABLE_COMPOSITING_MODE=1 vertexmarkdown`.
2. Check stderr for WebKit crash messages.
3. Disable custom CSS: `mv ~/.config/vertexmarkdown/custom.css{,.disabled}` and relaunch.

## Editor

### Undo doesn't go back far enough

Default history is 500 steps. Once you close and reopen a document, history is reset â€” snapshots (Ctrl+P â†’ View snapshot history) are the longer-term fallback.

### Typing is laggy in split view

The preview re-renders after a 220 ms debounce. For very large docs, switch to Editor-only (View segmented button) and only flip to Split when you want to visually check.

### Smart paste didn't convert HTML

- If `python3-html2text` is not installed, VertexMarkdown uses a built-in fallback that handles common tags only (`h1-h6`, `p`, `br`, `strong/b`, `em/i`, `code`, `pre`, `a`, `img`, `ul/ol/li`, `blockquote`, `hr`). Anything else comes through as plain text. Install `python3-html2text` for best results.

### Smart list not continuing

Recognized patterns: `^\s*[-*+] `, `^\s*\d+\. `, `^\s*[-*+] \[[ xX]\] `. Custom bullet characters aren't supported.

## Preview

### KaTeX / Mermaid not rendering

- You're offline â€” the CDN bundle couldn't load. Content appears as raw source.
- A corporate firewall is blocking `cdn.jsdelivr.net`. Whitelist it or wait for the bundled offline copies in 0.6.
- WebView has JavaScript disabled. Not possible via UI; check if you modified `enable-javascript` in the source.

### Math delimiters not recognised

Use one of: `$â€¦$`, `$$â€¦$$`, `\(â€¦\)`, `\[â€¦\]`. `\begin{equation}` blocks aren't auto-rendered.

### Mermaid error in diagram

The error renders inline in the preview. Mermaid is strict about syntax â€” see [mermaid.js.org/syntax](https://mermaid.js.org/syntax).

### Custom CSS isn't applying

1. Path must be exactly `~/.config/vertexmarkdown/custom.css` (or `$XDG_CONFIG_HOME/vertexmarkdown/custom.css`).
2. Reload the document (`Ctrl+R`) â€” CSS is read at render time, not cached.
3. Check for a syntax error in your CSS â€” WebKit silently drops invalid rules.

### Transclusion target not found

- Relative to the *current file's* folder, not the working directory.
- `.md` extension is optional in `![[name]]` but the file must exist on disk.
- Max 4-level depth; cycles are cut off.

## Folder search / palette

### Search returns nothing but I know the term exists

- Search is scoped to the current document's folder (and subfolders). If your document is untitled, the working directory is used.
- Filtering is case-insensitive substring, not regex or fuzzy.
- `.git`, `node_modules`, `.venv`, `__pycache__` folders are skipped.

### Outline sidebar is empty

The outline lists headings found outside fenced code blocks. Check that the document has `#`-prefixed headings (not `=====` / `-----` underlined ones â€” Setext-style headings aren't indexed yet).

## File handling

### File monitor didn't detect my external edit

- Reload explicitly: `Ctrl+R`.
- Some network filesystems (older NFS, some SMB setups) don't emit inotify events. This is a kernel-level limitation.

### Save failed with "Could not write â€¦"

- Disk full or read-only filesystem.
- The file was moved or deleted while open. Use `Save As`.

### Snapshots aren't being created

- `_write_to` writes a snapshot on every successful save. Check `~/.local/state/vertexmarkdown/snapshots/` exists and is writable.
- Untitled buffers don't snapshot (there's no stable path yet). Save once, then edits are covered.

## Export

### Export to PDF fails

- `pandoc` must be installed: `sudo apt install pandoc`.
- PDF engine: VertexMarkdown passes `--pdf-engine=xelatex`. Install a LaTeX stack: `sudo apt install texlive-xetex`.
- For simpler HTML-to-PDF, export as HTML and print it from a browser.

### Export to DOCX / EPUB fails

- `pandoc` must be installed. No extra engines needed for these formats.

## Performance

### App uses more memory than expected

WebKit is the biggest consumer. Typical resident set is 150â€“300 MB. If it balloons, the preview likely has a stuck script â€” reload (`Ctrl+R`) or switch to Editor-only.

### Cold start is slow

- Usually GTK theme loading. Check `GTK_DEBUG=interactive vertexmarkdown` â€” if GTK itself is slow you'll see it spinning on theme parsing.
- Antivirus or file-indexer scanning your home on first read â€” wait for it to finish, or exclude the folder.


