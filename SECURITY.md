# Security policy

## Reporting a vulnerability

If you believe you've found a security issue in markview, please **do not** open a public GitHub issue.

Instead, open a private GitHub Security Advisory:

1. Go to the repo's **Security → Advisories** tab.
2. Click **Report a vulnerability**.
3. Describe the issue, impact, and a minimal reproducer if possible.

You should get an acknowledgement within a week.

## Scope

markview is a desktop viewer/editor that:

- Reads local files chosen by the user
- Renders them in an embedded WebKit view (scripts enabled, plugins disabled, dev tools disabled)
- Fetches KaTeX and Mermaid from a CDN on each preview load
- Calls `pandoc` (if present) for exports
- Reads/writes files under the user's home directory

Issues relevant to the project include, for example:

- Path traversal in transclusion or image paste
- Unexpected code execution from a crafted markdown file
- XSS that escapes the WebKit view into the host process
- Filesystem writes outside the user-selected document folder
- Leaks of local file contents via the CDN fetches

## Not in scope

- Vulnerabilities in Python, GTK, WebKit, GtkSourceView, pandoc, KaTeX, or Mermaid themselves — please report those upstream.
- Theoretical issues without a concrete reproducer.
- The user intentionally opening a local file they don't trust (markview is a local viewer; treat inputs accordingly).

## Supported versions

Only the latest minor release line receives security fixes. Older versions may not be patched.
