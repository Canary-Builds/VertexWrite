# Architecture

VertexMarkdown now has a shared rendering core plus two native frontends:

- `vertexmarkdown.py` for Linux (`GTK3 + WebKit2 + GtkSourceView`)
- `vertexmarkdown_win.py` for Windows (`PyQt6 + QtWebEngine + QWebChannel`)
- `vertexmarkdown_core.py` for shared markdown/rendering helpers

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Gtk.ApplicationWindow                                    â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚ â”‚ Gtk.HeaderBar                                        â”‚ â”‚
â”‚ â”‚   [Open] [Edit toggle] [Reload] ...........  [Theme] â”‚ â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚ â”‚ Gtk.Revealer  (edit toolbar, slides down)            â”‚ â”‚
â”‚ â”‚   [File] [History] [Clipboard] [Format] [View] [Find]â”‚ â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚ â”‚ Gtk.SearchBar (find in buffer)                       â”‚ â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚ â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚ â”‚ Gtk.Revealer    â”‚ Gtk.Box (content area)           â”‚   â”‚
â”‚ â”‚  OutlineSidebar â”‚   preview | editor | Gtk.Paned    â”‚   â”‚
â”‚ â”‚  (slides right) â”‚                                  â”‚   â”‚
â”‚ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Rendering pipeline

```
source (string)
    â”‚
    â”œâ”€ preprocess_transclusions  â”€â”€ resolves ![[other]] / ![[other#Section]]
    â”‚
    â”œâ”€ preprocess_tasks          â”€â”€ swaps `- [ ] foo` for inline HTML inputs
    â”‚
    â”œâ”€ markdown.Markdown         â”€â”€ with curated extensions
    â”‚
    â”œâ”€ inject <style> (base + pygments + user custom.css)
    â”‚
    â”œâ”€ inject <script> KaTeX + Mermaid (CDN)
    â”‚
    â”œâ”€ inject JS bridge           â”€â”€ scrollToAnchor, task click postMessage,
    â”‚                                 mermaid.run, renderMathInElement
    â”‚
    â””â”€â–¶ native webview loads HTML
         Linux: WebKit2.WebView.load_html(html, base_uri)
         Windows: QWebEngineView.setHtml(html, base_url)
```

## Editor

```
GtkSource.Buffer (language: 'markdown', undo levels 500)
    â”‚
    â”œâ”€ connect "changed"                â”€â”€ refresh heading cache, schedule live preview,
    â”‚                                       schedule word count
    â”œâ”€ connect "notify::cursor-position" â”€â”€ typewriter recenter, scroll-sync debounce
    â”‚
GtkSource.View
    â”‚
    â”œâ”€ CSS provider (font)
    â”œâ”€ connect "key-press-event"         â”€â”€ smart paste (Ctrl+V),
    â”‚                                       smart list continuation (Enter),
    â”‚                                       block move (Alt+â†‘/â†“)
```

## Bridge layer

Linux uses a WebKit `UserContentManager`:

```python
ucm.register_script_message_handler("vertexmarkdown")
ucm.connect("script-message-received::vertexmarkdown", self._on_script_message)
webview = WebKit2.WebView.new_with_user_content_manager(ucm)
```

In-page JS posts messages:

```js
window.webkit.messageHandlers.vertexmarkdown.postMessage(JSON.stringify({...}));
```

Payload types today:

| `type` | Effect |
|---|---|
| `task_toggle` | Flip `[ ]` / `[x]` at `line` (buffer or file) |

Windows uses `QWebChannel`, exposing a `bridge` object to the page and receiving JSON payloads through `postMessage(...)`.

Both frontends support the same checkbox-toggle payload model.

## View modes

Three sub-views when edit mode is on, each by reparenting the existing `preview_scroller` and `editor_scroller`:

| Sub-view | Container |
|---|---|
| Editor | `content_box` â† `editor_scroller` |
| Preview | `content_box` â† `preview_scroller` |
| Split | `content_box` â† `Gtk.Paned(H)` with editor on the left, preview on the right |

A single feature flag (`_view_switching`) prevents radio-button toggle recursion.

## Debounce timers

Timer-based debouncing for expensive operations to avoid flicker or compute spikes on every keystroke:

| Timer | Default | Triggered by |
|---|---|---|
| `LIVE_PREVIEW_DEBOUNCE_MS` | 220 ms | buffer `changed` |
| `SCROLL_SYNC_DEBOUNCE_MS` | 80 ms | `notify::cursor-position` |
| `WORD_COUNT_DEBOUNCE_MS` | 250 ms | buffer `changed` |

## File monitor + save suppression

`Gio.File.monitor_file(...)` watches the current document for external changes. During self-save we suppress reload for ~1 s (`_suppress_reload_until`) so our own writes don't race.

## Snapshots

`_write_to` always writes a dated copy to `~/.local/state/vertexmarkdown/snapshots/<sha1(path)>-<stem>/<YYYYMMDD-HHMMSS>.md`. Latest 30 retained per document. Snapshots are not threaded or indexed.

## Keyboard shortcut system

`Gtk.AccelGroup` on the window binds shortcuts at the application-window level. Lambda handlers always return `True` so accelerators are consumed. See `_setup_shortcuts`.

## Dependencies map

```
vertexmarkdown_core.py
â”‚
â”œâ”€ markdown + pygments                           â”€â”€ shared render pipeline
â”œâ”€ markdown.extensions.toc.slugify               â”€â”€ heading anchors
â”œâ”€ html2text (optional)                          â”€â”€ smart-paste HTML
â”œâ”€ html.parser (stdlib)                          â”€â”€ fallback for above
â”œâ”€ urllib.request (stdlib)                       â”€â”€ open-from-URL
â”œâ”€ subprocess (stdlib)                           â”€â”€ pandoc export
â””â”€ hashlib (stdlib)                              â”€â”€ snapshot folder naming

vertexmarkdown.py
â”‚
â””â”€ gi + Gtk/WebKit2/GtkSource/Gdk/GLib/Gio/Pango â”€â”€ Linux frontend

vertexmarkdown_win.py
â”‚
â””â”€ PyQt6 + QtWebEngine + QWebChannel             â”€â”€ Windows frontend
```

## Adding a new palette action

1. Add a tuple to `_palette_items` actions list: `(label, shortcut-hint, key)`.
2. Handle the key in `_palette_select` dispatch table.
3. Implement the behaviour method.
4. (Optional) Bind a keyboard shortcut in `_setup_shortcuts`.
5. Document in `docs/wiki/Keyboard-Shortcuts.md` and `CHANGELOG.md`.

## Adding a new markdown preprocessor

1. Add a pure function `preprocess_foo(text: str) -> str` near the existing preprocessors.
2. Wire into `render()` before `markdown.Markdown(...)` is called.
3. Respect fenced code blocks (`FENCE_RE`).
4. Add tests to any smoke test script and a worked example in `docs/wiki/Markdown-Features.md`.


