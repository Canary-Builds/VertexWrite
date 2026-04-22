# Roadmap

Living document. Versions and scope shift; open an issue to push or pull items.

Legend: ðŸŸ¢ done Â· ðŸŸ¡ planned Â· ðŸŸ£ researching Â· âšª idea

## 0.5.0 â€” Core is done ðŸŸ¢

See [CHANGELOG.md](CHANGELOG.md). Covers 24 of the ~26 features surveyed from the category â€” navigation, editing, preview extras, palette actions, craft, and persistence. All keyboard-activated, no new visible chrome.

---

## 0.6.0 â€” Intentionally-deferred-from-0.5 ðŸŸ¡

Targeting the six features that were deliberately held back in 0.5 to keep the release focused.

- ðŸŸ¡ **Spell check** â€” GtkSpell3 integration when `gir1.2-gspell-1` is available; graceful fallback when not. Dictionary selection via palette.
- ðŸŸ¡ **Structured front-matter UI** â€” detect YAML / TOML front matter, expose as a form dialog (keys + values + add/remove) from the palette. Raw text editing stays first-class.
- ðŸŸ¡ **Outline drag-to-reorder** â€” `Gtk.TreeView` with DnD reorder; re-emits the section moves back into the buffer.
- ðŸŸ¡ **Smart list continuation for nested lists** â€” handle `Tab` / `Shift+Tab` for indent/outdent, renumber ordered lists on reorder.
- ðŸŸ¡ **Bundled KaTeX + Mermaid** â€” ship minified copies under `vendor/` so math/diagrams work offline. Fall back to CDN when the bundle is missing.
- ðŸŸ¡ **Link integrity: URL reachability** â€” optional opt-in HEAD check for http(s) links alongside the existing relative-path check.

## 0.7.0 â€” Writer ergonomics ðŸŸ¡

- ðŸŸ¡ **Table editor** â€” dialog with a spreadsheet-like `Gtk.Grid`: add/remove rows and columns, per-column alignment, live markdown sync. Invoked from the palette or from a right-click over a markdown table.
- ðŸŸ¡ **Grammar via LanguageTool** â€” local server mode (`languagetool-server.jar`) or hosted API; inline squiggles using `GtkTextTag`s and a margin mark.
- ðŸŸ¡ **Distraction-free focus mode** â€” in addition to typewriter, dim non-current paragraphs via `GtkTextTag`s. Single toggle.
- ðŸŸ¡ **Word-count breakdown** â€” `Ctrl+P` â†’ "Document stats": characters, words, reading time, sentence count, longest paragraph, prose/code ratio.
- ðŸŸ¡ **Snippets / templates** â€” user-defined templates under `~/.config/vertexmarkdown/templates/` surfaced in the palette (e.g. "Daily note", "Meeting").

## 0.8.0 â€” Modality ðŸŸ¡

- ðŸŸ¡ **Vim keybindings** â€” opt-in, normal/insert/visual/command modes. Implemented as a dedicated input handler that can be disabled entirely.
- ðŸŸ¡ **Command-mode `:` buffer** â€” reachable even without the vim layer (`Ctrl+Shift+;`) for power-user commands.
- ðŸŸ£ **Multi-cursor** â€” `Ctrl+D` next-occurrence (reassigning current "toggle theme" shortcut), `Alt+Click` add cursor.

## 0.9.0 â€” Notes graph ðŸŸ¡

- ðŸŸ¡ **Persistent backlinks index** â€” background scan of the folder, cached in `~/.local/state/vertexmarkdown/index/<folder-hash>.sqlite`. Makes backlink + orphan queries O(1).
- ðŸŸ¡ **Orphan / broken note report** â€” palette: "Show orphans", "Show broken references".
- ðŸŸ¡ **Graph view** â€” a D3 / Cytoscape mini-graph in the preview pane for a selected root note.
- ðŸŸ£ **Tag index** â€” treat `#tag` outside code as tags; palette view of all tags + membership.

## 1.0.0 â€” Foundations ðŸŸ¡

- ðŸŸ¡ **GTK4 + libadwaita port** â€” matches modern Linux desktops; `Adw.TabView` for multi-document; `Adw.HeaderBar` with adaptive layout.
- ðŸŸ¡ **Plugin API** â€” discover Python modules under `~/.config/vertexmarkdown/plugins/`; stable hook points for render post-processing, palette items, and toolbar additions.
- ðŸŸ¡ **Accessibility audit** â€” focus order, screen-reader labels, high-contrast theme, keyboard-only coverage.
- ðŸŸ¡ **Packaging** â€” Flatpak on Flathub, Ubuntu PPA maintenance, AUR `vertexmarkdown` (for Arch/Manjaro), Fedora COPR package, and a pip-installable wheel for `pip install vertexmarkdown` on systems with PyGObject.
- ðŸŸ¡ **i18n** â€” gettext catalog, first pass of translations (contrib-driven).

## Post-1.0 â€” Stretch âšª

- âšª **Local LLM assist** â€” summarise selection, rewrite tone, generate outline; local-first via ollama or llama.cpp, opt-in and clearly bounded.
- âšª **Markdown Language Server** integration (`marksman`) â€” hover previews on links, goto-definition for internal refs, completion for heading anchors and file paths.
- âšª **Collaborative editing** â€” CRDT (Yjs/Automerge) over an optional sync backend.
- âšª **PDF export without pandoc** â€” `WebKit2.PrintOperation` straight from the preview; styleable via `custom.css`.
- âšª **Mobile companion** â€” read-only Android/iOS viewer pointed at a synced folder.
- âšª **Clipper** â€” a browser extension + Python endpoint to save a webpage as clean markdown in a chosen folder.
- âšª **Encryption at rest** â€” age-based (or similar) per-file encryption with keyring integration.
- âšª **Versioned local history viewer** â€” diff-side-by-side between snapshots with a `difflib` renderer.

---

## Explicitly out of scope

- Cloud sync, accounts, or any network-mandatory feature.
- A plugin marketplace with its own server.
- Bundling all dependencies in a universal binary (GTK is a platform; Flatpak is the right answer).
- Becoming a block editor or outliner.

---

## How items move on this roadmap

1. **Idea â†’ Researching**: an issue exists, design is sketched.
2. **Researching â†’ Planned**: approach is agreed, assigned to a version bucket.
3. **Planned â†’ Done**: ships in a tagged release; moves to [CHANGELOG.md](CHANGELOG.md).

Version buckets are approximate â€” features may hop if they grow or shrink in scope.


