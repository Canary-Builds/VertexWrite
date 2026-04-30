# Keyboard Shortcuts

All shortcuts are bound at the window level, so they work regardless of whether the editor, the preview, or the find bar has focus — except where noted.

## File

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open file |
| `Ctrl+N` | New untitled document (enters edit mode) |
| `Ctrl+S` | Save (prompts for location if untitled) |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+R` | Reload current file from disk |
| `Ctrl+Q` | Quit |

## View

| Shortcut | Action |
|---|---|
| `Ctrl+E` | Toggle edit mode (shows the edit toolbar) |
| `Ctrl+Shift+O` | Toggle document sidebar |
| `Ctrl+Shift+T` | Toggle typewriter mode |
| `Ctrl+D` | Toggle light / dark theme |

In edit mode the view-mode segmented buttons on the toolbar switch between **Editor**, **Split**, and **Preview** sub-views.

## Navigation

| Shortcut | Action |
|---|---|
| `Ctrl+P` | Command palette (fuzzy jump to actions, headings, files) |
| `Ctrl+F` | Find in current buffer (edit mode only) |
| `Ctrl+Shift+F` | Search in folder |
| `Alt+←` | Go back (file + line) |
| `Alt+→` | Go forward |

## Editing

| Shortcut | Action |
|---|---|
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` / `Ctrl+Y` | Redo |
| `Ctrl+X` | Cut |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Smart paste (image → assets, HTML → md, CSV → table, else text) |
| `Alt+↑` / `Alt+↓` | Move current line or selection up/down |
| `Enter` | Smart list continuation (`-`, `1.`, `- [ ]`); empty bullet exits list |

## Formatting

| Shortcut | Action |
|---|---|
| `Ctrl+B` | Bold |
| `Ctrl+I` | Italic |
| `Ctrl+K` | Link |
| `Ctrl+H` | Heading (toggles `# ` on the current line) |

## Preview interactions

| Action | Behaviour |
|---|---|
| Click `☐` / `☑` | Toggles the underlying `- [ ]` / `- [x]` in the buffer or file |
| Drag a `.md` onto the window | Opens it |

## Palette-only actions

Triggered from `Ctrl+P`, no dedicated shortcut:

- Insert table…
- Open from URL…
- Show all tasks in folder…
- Show backlinks to this file
- Check links in current buffer
- View snapshot history…
- Export as PDF / DOCX / HTML / EPUB (pandoc)
