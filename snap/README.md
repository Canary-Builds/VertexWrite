# Snap packaging

## Build locally

```bash
sudo snap install snapcraft --classic
cd /path/to/vertexwrite
snapcraft pack
```

## Publish

```bash
snapcraft login
snapcraft register vertexwrite
snapcraft upload --release=stable vertexwrite_*.snap
```

If the name `vertexwrite` is unavailable, register a different unique snap name and update `name:` in `snap/snapcraft.yaml`.
