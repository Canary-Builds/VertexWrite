#!/usr/bin/env python3
"""markview — minimal modern markdown viewer for Linux."""
import os
import sys
import argparse
import html
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2, Gio, GLib, Gdk  # noqa: E402

import markdown  # noqa: E402
from pygments.formatters import HtmlFormatter  # noqa: E402

__version__ = "0.2.0"

APP_ID = "dev.markview.Viewer"
APP_NAME = "markview"
APP_DIR = Path(__file__).resolve().parent
STYLE_PATH = APP_DIR / "style.css"

MD_EXTENSIONS = [
    "fenced_code",
    "tables",
    "toc",
    "codehilite",
    "sane_lists",
    "footnotes",
    "attr_list",
    "md_in_html",
    "admonition",
    "def_list",
    "abbr",
]
MD_EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "css_class": "codehilite"},
    "toc": {"permalink": False},
}


def load_style() -> str:
    try:
        return STYLE_PATH.read_text()
    except OSError:
        return ""


def pygments_css(theme: str) -> str:
    style = "github-dark" if theme == "dark" else "friendly"
    try:
        return HtmlFormatter(style=style).get_style_defs(".codehilite")
    except Exception:
        return HtmlFormatter().get_style_defs(".codehilite")


def render(md_text: str, theme: str, title: str) -> str:
    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS)
    body = md.convert(md_text)
    return f"""<!DOCTYPE html>
<html data-theme="{theme}">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{load_style()}</style>
<style>{pygments_css(theme)}</style>
</head>
<body>
<main class="markdown-body">
{body}
</main>
</body>
</html>"""


def welcome_html(theme: str) -> str:
    md_text = (
        f"# markview\n\n"
        f"*v{__version__} — a minimal, modern markdown viewer.*\n\n"
        "- **Open a file** — `Ctrl+O`, drag & drop, or pass a path on the CLI\n"
        "- **Reload** — `Ctrl+R`\n"
        "- **Toggle theme** — `Ctrl+D`\n"
        "- **Quit** — `Ctrl+Q`\n\n"
        "```python\n"
        "def hello():\n"
        "    print('markview')\n"
        "```\n"
    )
    return render(md_text, theme, "markview")


class Viewer(Gtk.ApplicationWindow):
    def __init__(self, app, path: Path | None):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(960, 780)
        self.current_path: Path | None = None
        self.monitor: Gio.FileMonitor | None = None
        self.theme = self._detect_theme()
        self.mode = "preview"  # "preview" | "edit"
        self._suppress_reload_until = 0.0

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = APP_NAME
        self.header = header
        self.set_titlebar(header)

        open_btn = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        open_btn.set_tooltip_text("Open markdown file (Ctrl+O)")
        open_btn.connect("clicked", self._on_open_clicked)
        header.pack_start(open_btn)

        self.edit_btn = Gtk.ToggleButton()
        self.edit_btn.set_image(
            Gtk.Image.new_from_icon_name("document-edit-symbolic", Gtk.IconSize.BUTTON)
        )
        self.edit_btn.set_tooltip_text("Edit mode (Ctrl+E)")
        self.edit_btn.set_sensitive(False)
        self.edit_btn.connect("toggled", self._on_edit_toggled)
        header.pack_start(self.edit_btn)

        reload_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        reload_btn.set_tooltip_text("Reload (Ctrl+R)")
        reload_btn.connect("clicked", lambda *_: self._reload())
        header.pack_start(reload_btn)

        self.theme_btn = Gtk.Button.new_from_icon_name(self._theme_icon(), Gtk.IconSize.BUTTON)
        self.theme_btn.set_tooltip_text("Toggle theme (Ctrl+D)")
        self.theme_btn.connect("clicked", lambda *_: self._toggle_theme())
        header.pack_end(self.theme_btn)

        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_property("enable-developer-extras", False)
        settings.set_property("enable-javascript", True)
        settings.set_property("enable-smooth-scrolling", True)

        self.preview_scroller = Gtk.ScrolledWindow()
        self.preview_scroller.add(self.webview)

        self.editor = Gtk.TextView()
        self.editor.set_monospace(True)
        self.editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.editor.set_left_margin(24)
        self.editor.set_right_margin(24)
        self.editor.set_top_margin(20)
        self.editor.set_bottom_margin(120)
        self.editor.set_pixels_above_lines(1)
        self.editor_buffer = self.editor.get_buffer()
        self.editor_buffer.connect("changed", self._on_buffer_changed)

        self.editor_scroller = Gtk.ScrolledWindow()
        self.editor_scroller.add(self.editor)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        self.stack.add_named(self.preview_scroller, "preview")
        self.stack.add_named(self.editor_scroller, "edit")
        self.add(self.stack)

        self._setup_shortcuts()
        self._setup_dnd()

        if path is not None:
            self.load_file(path)
        else:
            self._render_welcome()

    def _detect_theme(self) -> str:
        settings = Gtk.Settings.get_default()
        if settings is not None:
            prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
            if prefer_dark:
                return "dark"
            theme_name = (settings.get_property("gtk-theme-name") or "").lower()
            if "dark" in theme_name:
                return "dark"
        return "light"

    def _theme_icon(self) -> str:
        return "weather-clear-night-symbolic" if self.theme == "light" else "weather-clear-symbolic"

    def _setup_shortcuts(self):
        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)

        def bind(key: str, mod, handler):
            keyval = Gdk.keyval_from_name(key)
            accel.connect(keyval, mod, Gtk.AccelFlags.VISIBLE, lambda *_: handler() or True)

        bind("o", Gdk.ModifierType.CONTROL_MASK, self._on_open_clicked)
        bind("r", Gdk.ModifierType.CONTROL_MASK, self._reload)
        bind("q", Gdk.ModifierType.CONTROL_MASK, self.close)
        bind("d", Gdk.ModifierType.CONTROL_MASK, self._toggle_theme)
        bind("e", Gdk.ModifierType.CONTROL_MASK, self._toggle_edit)
        bind("s", Gdk.ModifierType.CONTROL_MASK, self._save_current)

    def _setup_dnd(self):
        targets = Gtk.TargetList.new([])
        targets.add_uri_targets(0)
        self.webview.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [],
            Gdk.DragAction.COPY,
        )
        self.webview.drag_dest_set_target_list(targets)
        self.webview.connect("drag-data-received", self._on_drag_received)

    def _on_drag_received(self, _widget, _context, _x, _y, data, _info, _time):
        uris = data.get_uris()
        if not uris:
            return
        path = Gio.File.new_for_uri(uris[0]).get_path()
        if path:
            self.load_file(Path(path))

    def _on_open_clicked(self, *_):
        dialog = Gtk.FileChooserDialog(
            title="Open markdown file",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Open", Gtk.ResponseType.OK,
        )
        f = Gtk.FileFilter()
        f.set_name("Markdown")
        for pattern in ("*.md", "*.markdown", "*.mdown", "*.mkd", "*.txt"):
            f.add_pattern(pattern)
        dialog.add_filter(f)
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)

        if dialog.run() == Gtk.ResponseType.OK:
            path = Path(dialog.get_filename())
            dialog.destroy()
            self.load_file(path)
        else:
            dialog.destroy()

    def load_file(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._render_error(f"Could not read {path}: {exc}")
            return
        self.current_path = path
        self.edit_btn.set_sensitive(True)
        self.header.props.title = path.name
        self.header.props.subtitle = str(path.parent)
        base_uri = path.parent.as_uri() + "/"
        self.webview.load_html(render(text, self.theme, path.name), base_uri)
        if self.mode == "edit":
            self._load_editor_text(text)
        self._watch_file(path)

    def _watch_file(self, path: Path):
        if self.monitor is not None:
            self.monitor.cancel()
        try:
            f = Gio.File.new_for_path(str(path))
            self.monitor = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self.monitor.connect("changed", self._on_file_changed)
        except GLib.Error:
            self.monitor = None

    def _on_file_changed(self, _mon, _file, _other, event):
        if self.mode == "edit":
            return  # don't clobber in-flight edits
        if GLib.get_monotonic_time() / 1e6 < self._suppress_reload_until:
            return  # our own save — ignore the resulting event
        if event in (
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CREATED,
        ):
            GLib.timeout_add(120, self._reload)

    def _reload(self, *_):
        if self.current_path and self.current_path.exists():
            self.load_file(self.current_path)
        else:
            self._render_welcome()
        return False

    def _toggle_theme(self, *_):
        self.theme = "dark" if self.theme == "light" else "light"
        self.theme_btn.set_image(
            Gtk.Image.new_from_icon_name(self._theme_icon(), Gtk.IconSize.BUTTON)
        )
        if self.current_path and self.current_path.exists():
            self.load_file(self.current_path)
        else:
            self._render_welcome()

    def _render_welcome(self):
        self.webview.load_html(welcome_html(self.theme), APP_DIR.as_uri() + "/")
        self.edit_btn.set_sensitive(False)

    def _render_error(self, msg: str):
        md_text = f"# Error\n\n```\n{msg}\n```\n"
        self.webview.load_html(render(md_text, self.theme, "Error"), APP_DIR.as_uri() + "/")

    # ---- edit mode ---------------------------------------------------------

    def _on_edit_toggled(self, btn):
        self._set_mode("edit" if btn.get_active() else "preview")

    def _toggle_edit(self, *_):
        if not self.edit_btn.get_sensitive():
            return
        self.edit_btn.set_active(not self.edit_btn.get_active())

    def _set_mode(self, mode: str):
        if mode == self.mode:
            return
        if mode == "edit":
            if not self.current_path:
                self.edit_btn.set_active(False)
                return
            try:
                text = self.current_path.read_text(encoding="utf-8")
            except OSError as exc:
                self._render_error(f"Could not read {self.current_path}: {exc}")
                self.edit_btn.set_active(False)
                return
            self._load_editor_text(text)
            self.stack.set_visible_child_name("edit")
            self.mode = "edit"
            self.edit_btn.set_tooltip_text("Exit edit mode (Ctrl+E) · save with Ctrl+S")
            self.editor.grab_focus()
        else:
            if self.editor_buffer.get_modified():
                self._write_buffer_to_file()
            self.stack.set_visible_child_name("preview")
            self.mode = "preview"
            self.edit_btn.set_tooltip_text("Edit mode (Ctrl+E)")
            if self.current_path and self.current_path.exists():
                self.load_file(self.current_path)

    def _load_editor_text(self, text: str):
        self.editor_buffer.handler_block_by_func(self._on_buffer_changed)
        self.editor_buffer.set_text(text)
        self.editor_buffer.set_modified(False)
        self.editor_buffer.handler_unblock_by_func(self._on_buffer_changed)
        self._update_title_dirty()

    def _on_buffer_changed(self, *_):
        self._update_title_dirty()

    def _update_title_dirty(self):
        if not self.current_path:
            return
        dirty = self.editor_buffer.get_modified()
        self.header.props.title = f"{self.current_path.name}{' •' if dirty else ''}"

    def _save_current(self, *_):
        if self.mode != "edit" or not self.current_path:
            return
        self._write_buffer_to_file()

    def _write_buffer_to_file(self) -> bool:
        if not self.current_path:
            return False
        start, end = self.editor_buffer.get_bounds()
        text = self.editor_buffer.get_text(start, end, True)
        try:
            self._suppress_reload_until = GLib.get_monotonic_time() / 1e6 + 1.0
            self.current_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            self._render_error(f"Could not write {self.current_path}: {exc}")
            return False
        self.editor_buffer.set_modified(False)
        self._update_title_dirty()
        return True


class App(Gtk.Application):
    def __init__(self, path: Path | None):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._initial_path = path

    def do_activate(self):
        win = Viewer(self, self._initial_path)
        win.show_all()


def parse_args(argv: list[str]) -> Path | None:
    parser = argparse.ArgumentParser(prog=APP_NAME, description="Minimal modern markdown viewer.")
    parser.add_argument("file", nargs="?", help="Path to a markdown file.")
    parser.add_argument("-V", "--version", action="version", version=f"{APP_NAME} {__version__}")
    args = parser.parse_args(argv)
    if args.file:
        p = Path(args.file).expanduser().resolve()
        if not p.exists():
            print(f"{APP_NAME}: file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p
    return None


def main():
    path = parse_args(sys.argv[1:])
    app = App(path)
    app.run([])


if __name__ == "__main__":
    main()
