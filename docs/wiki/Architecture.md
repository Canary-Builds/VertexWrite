# Architecture

VertexWrite now has a shared rendering core plus two native frontends:

- `vertexwrite.py` for Linux (`GTK3 + WebKit2 + GtkSourceView`)
- `vertexwrite_win.py` for Windows (`PyQt6 + QtWebEngine + QWebChannel`)
- `vertexwrite_core.py` for shared markdown/rendering helpers
- `vertexwrite_files.py` for storage URI and backend primitives

```
┌──────────────────────────────────────────────────────────┐
│ Gtk.ApplicationWindow                                    │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Gtk.HeaderBar                                        │ │
│ │   [Open] [Edit toggle] [Reload] ...........  [Theme] │ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Gtk.Revealer  (edit toolbar, slides down)            │ │
│ │   [File] [History] [Clipboard] [Format] [View] [Find]│ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Gtk.SearchBar (find in buffer)                       │ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌─────────────────┬──────────────────────────────────┐   │
│ │ Gtk.Revealer    │ Gtk.Box (content area)           │   │
│ │  Document pane  │   preview | editor | Gtk.Paned    │   │
│ │  recents + tree │                                  │   │
│ └─────────────────┴──────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Rendering pipeline

```
source (string)
    │
    ├─ preprocess_transclusions  ── resolves ![[other]] / ![[other#Section]]
    │
    ├─ preprocess_tasks          ── swaps `- [ ] foo` for inline HTML inputs
    │
    ├─ markdown.Markdown         ── with curated extensions
    │
    ├─ inject <style> (base + pygments + user custom.css)
    │
    ├─ inject <script> KaTeX + Mermaid (CDN)
    │
    ├─ inject JS bridge           ── scrollToAnchor, task click postMessage,
    │                                 mermaid.run, renderMathInElement
    │
    └─▶ native webview loads HTML
         Linux: WebKit2.WebView.load_html(html, base_uri)
         Windows: QWebEngineView.setHtml(html, base_url)
```

## Editor

```
GtkSource.Buffer (language: 'markdown', undo levels 500)
    │
    ├─ connect "changed"                ── refresh heading cache, schedule live preview,
    │                                       schedule word count
    ├─ connect "notify::cursor-position" ── typewriter recenter, scroll-sync debounce
    │
GtkSource.View
    │
    ├─ CSS provider (font)
    ├─ connect "key-press-event"         ── smart paste (Ctrl+V),
    │                                       smart list continuation (Enter),
    │                                       block move (Alt+↑/↓)
```

## Bridge layer

Linux uses a WebKit `UserContentManager`:

```python
ucm.register_script_message_handler("vertexwrite")
ucm.connect("script-message-received::vertexwrite", self._on_script_message)
webview = WebKit2.WebView.new_with_user_content_manager(ucm)
```

In-page JS posts messages:

```js
window.webkit.messageHandlers.vertexwrite.postMessage(JSON.stringify({...}));
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
| Editor | `content_box` ← `editor_scroller` |
| Preview | `content_box` ← `preview_scroller` |
| Split | `content_box` ← `Gtk.Paned(H)` with editor on the left, preview on the right |

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

## Storage boundary

`vertexwrite_files.py` owns stable document identifiers and backend dispatch:

| Type | Responsibility |
|---|---|
| `FileUri` | Parse and serialize `file://...` and future `sftp://user@host:port/...` document IDs |
| `FileInfo` | Backend-neutral file metadata |
| `LocalBackend` | Local stat/list/read/write operations, including temp-file + `os.replace` atomic writes |
| `SftpBackend` | Paramiko-backed SFTP stat/list/read/write operations with strict host-key policy |
| `BackendRegistry` | Scheme-to-backend lookup |

The Linux frontend stores the active document as a `FileUri`. Local documents still keep a `Path` mirror for features that require native filesystem access, while SFTP documents route open/save and sidebar folder browsing through the backend registry. Recent documents persist URI-shaped records: `{"uri": "file:///..."}`. Legacy string-path recents are migrated on read.

The document sidebar has a bottom SSH/SFTP control. It accepts `sftp://user@host:port/path` folder URIs and SSH-style shorthand such as `ssh example-host`, bare `example-host`, `ssh -p 2200 -l user host ~/docs`, and `host:/path`. The same dialog also exposes manual Host/IP, User, Port, and Path fields; filling Host/IP makes the manual fields the selected connection method. Host aliases are resolved through SSH config during connection. If no path is supplied, the SFTP backend normalizes `.` to the remote login directory before listing.

The folder tree is a browser, not a markdown-only scan. It lists the current directory's folders and files, includes parent-folder navigation, opens files through the backend registry, and has a dotfile visibility toggle. When the active folder tree root is remote, the sidebar file/folder buttons must remain inside the SFTP boundary. They open a remote SFTP browser on the active connection instead of opening a local `Gtk.FileChooserDialog`; local choosers are only used when the active folder tree root is local. The remote browser lists folders and files, supports Home, Up, Refresh, direct path entry, a hidden-dotfile toggle, and double-click folder navigation, then returns a `FileUri` to the folder tree browser.

For SSH config aliases, VertexWrite opens the TCP connection to `HostName` but checks host keys against the alias, `HostKeyAlias`, and resolved host candidates. This keeps strict known-hosts enforcement while matching common `ssh alias` workflows.

Long-term rule: new remote support should enter through a backend implementation, not through scattered `Path` special cases in UI code.

SFTP rules:

- `sftp://user:password@host/...` is rejected; passwords are never stored in URIs.
- Missing hosts and invalid ports are rejected during URI parsing.
- Connections use SSH agent/key auth and load system `known_hosts`.
- Missing host keys are rejected, not silently trusted.
- Remote writes use a temporary file followed by OpenSSH `posix-rename@openssh.com`; if the server cannot do atomic rename, the write fails instead of falling back to an unsafe overwrite.

## Snapshots

`_write_to` always writes a dated copy to `~/.local/state/vertexwrite/snapshots/<sha1(path)>-<stem>/<YYYYMMDD-HHMMSS>.md`. Latest 30 retained per document. Snapshots are not threaded or indexed.

## Keyboard shortcut system

`Gtk.AccelGroup` on the window binds shortcuts at the application-window level. Lambda handlers always return `True` so accelerators are consumed. See `_setup_shortcuts`.

## Dependencies map

```
vertexwrite_core.py
│
├─ markdown + pygments                           ── shared render pipeline
├─ markdown.extensions.toc.slugify               ── heading anchors
├─ html2text (optional)                          ── smart-paste HTML
├─ html.parser (stdlib)                          ── fallback for above
├─ urllib.request (stdlib)                       ── open-from-URL
├─ subprocess (stdlib)                           ── pandoc export
└─ hashlib (stdlib)                              ── snapshot folder naming

vertexwrite.py
│
└─ gi + Gtk/WebKit2/GtkSource/Gdk/GLib/Gio/Pango ── Linux frontend

vertexwrite_files.py
│
├─ pathlib + urllib.parse + tempfile + os/stat    ── backend-neutral file access
└─ paramiko (optional runtime dependency)         ── SFTP backend

vertexwrite_win.py
│
└─ PyQt6 + QtWebEngine + QWebChannel             ── Windows frontend
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
