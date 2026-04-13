# Changelog

All notable changes to `markview` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-04-13

### Added
- **Edit mode.** Toggle button in the header (between Open and Reload) flips the view to a plain text editor for the current file.
- `Ctrl+E` toggles edit mode; `Ctrl+S` saves the buffer to disk.
- Dirty indicator (`•`) appended to the window title when the editor buffer has unsaved changes.
- Edit button is disabled on the welcome screen (no file open); enabled once a file is loaded.

### Changed
- Live-reload file monitor is paused while in edit mode so in-flight edits are never clobbered by a self-triggered reload.
- Preview and editor share a `Gtk.Stack` with a short crossfade transition.

## [0.1.0] — 2026-04-13

### Added
- Initial release: GTK3 + WebKit2 markdown viewer for Linux.
- Light/dark theme auto-detected from system, toggle with `Ctrl+D`.
- Syntax highlighting via Pygments.
- Live reload on file save (GIO file monitor).
- Drag-and-drop of `.md` files onto the window.
- Keyboard shortcuts: `Ctrl+O` open, `Ctrl+R` reload, `Ctrl+D` theme, `Ctrl+Q` quit.
- Markdown extensions: fenced code, tables, TOC, footnotes, admonitions, def lists, abbr.
- `install.sh` / `uninstall.sh` — user-local install with `.desktop` entry and PATH shim.
- Welcome screen when launched with no file argument.
