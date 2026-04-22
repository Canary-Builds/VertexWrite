# Development

## Setup

Linux:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 \
                 gir1.2-gtksource-4 python3-markdown python3-pygments

git clone https://github.com/<you>/VertexMarkdown.git
cd VertexMarkdown

# optional extras for dev
sudo apt install python3-html2text pandoc
python3 -m pip install --user ruff pyflakes
```

Windows:

```powershell
py -3.13 -m pip install -r requirements-win.txt pyinstaller
```

No virtualenv is required on Linux. PyGObject is a system package there.

## Run from source

Linux:

```bash
python3 vertexmarkdown.py README.md
```

Windows:

```powershell
py .\vertexmarkdown_win.py README.md
```

Or make the Linux CLI launcher point at your checkout by re-running `./install.sh` from that folder.

## Layout

```
VertexMarkdown/
â”œâ”€â”€ vertexmarkdown.py         # Linux GTK frontend
â”œâ”€â”€ vertexmarkdown_win.py     # Windows Qt frontend
â”œâ”€â”€ vertexmarkdown_core.py    # shared renderer/helpers
â”œâ”€â”€ style.css           # preview theme
â”œâ”€â”€ icon.png            # app icon (square 512Ã—512)
â”œâ”€â”€ icon-final.png      # master source icon
â”œâ”€â”€ icon-{16..256}.png  # hicolor sizes generated from master
â”œâ”€â”€ vertexmarkdown.desktop    # desktop entry template
â”œâ”€â”€ install.sh          # user-local installer
â”œâ”€â”€ build_win.ps1       # Windows build helper
â”œâ”€â”€ installer_win.iss   # Windows installer script
â”œâ”€â”€ vertexmarkdown.spec       # PyInstaller spec
â”œâ”€â”€ requirements-win.txt
â”œâ”€â”€ uninstall.sh
â”œâ”€â”€ CHANGELOG.md
â”œâ”€â”€ ROADMAP.md
â”œâ”€â”€ CONTRIBUTING.md
â”œâ”€â”€ LICENSE
â”œâ”€â”€ .github/
â”‚   â”œâ”€â”€ ISSUE_TEMPLATE/
â”‚   â””â”€â”€ workflows/ci.yml
â””â”€â”€ docs/wiki/          # this directory
```

## Code conventions

- Python â‰¥ 3.10. Use `str | None`, `list[dict]`, etc.
- Private methods on `Viewer` are prefixed `_`.
- Module-level helpers are pure functions (no GTK imports inside them).
- Comments for the *why*; let identifiers carry the *what*.
- Keep cold start cheap: initialize heavy things lazily.
- Every new user-visible feature needs both a keyboard shortcut and a palette action, unless it's a core editor primitive that earns a toolbar button.

## Debugging

### Show errors on launch

```bash
vertexmarkdown README.md    # errors go to stderr
```

### Filter GTK noise

```bash
vertexmarkdown 2>&1 | grep -vE 'GdkPixbuf|libEGL|portal|WebKitSettings'
```

### Windows bundle smoke test

```powershell
python .\scripts\smoke_test_win_bundle.py
```

### WebKit developer tools

Enable by flipping `enable-developer-extras` in `_build_editor_widgets`:

```python
wsettings.set_property("enable-developer-extras", True)
```

Right-click in the preview â†’ **Inspect Element**.

### Confirm renders

```python
python3 -c "
import sys; sys.path.insert(0, '.')
import vertexmarkdown
print(vertexmarkdown.render('# hi\n\n- [ ] task\n', 'dark', 't', None)[:200])
"
```

## Smoke test

There is no GUI test suite. Minimal smoke you should run before opening a PR:

```bash
python3 -m py_compile vertexmarkdown.py vertexmarkdown_win.py vertexmarkdown_core.py
ruff check --select E,F,W,B,UP --ignore E501 vertexmarkdown.py vertexmarkdown_win.py vertexmarkdown_core.py
python3 vertexmarkdown.py README.md
```

```powershell
py -m py_compile vertexmarkdown.py vertexmarkdown_win.py vertexmarkdown_core.py
py .\vertexmarkdown_win.py README.md
```

If you added a feature, run through:

1. Open a file â†’ reload â†’ save â†’ edit mode â†’ split view
2. Command palette (Ctrl+P), folder search (Ctrl+Shift+F)
3. Outline (Ctrl+Shift+O), typewriter (Ctrl+Shift+T)
4. Smart paste with an image, HTML, and CSV each

## Release process (maintainer)

1. Bump release versioning in `vertexmarkdown.py`, `vertexmarkdown_win.py`, and Windows metadata when needed.
2. Move `CHANGELOG.md` `[Unreleased]` items under a new version heading with today's date.
3. Commit: `git commit -m 'Release vX.Y.Z'`.
4. Tag: `git tag -a vX.Y.Z -m 'vX.Y.Z â€” summary'`.
5. Push: `git push origin main --tags`.
6. Tag pushes trigger the Windows release workflow, which builds and attaches the installer to the GitHub Release.


