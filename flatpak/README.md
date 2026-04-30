# Flatpak packaging

## Build for validation (without installing the app)

```bash
sudo apt install flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk//49 org.gnome.Platform//49
cd /path/to/vertexwrite
flatpak-builder --force-clean --repo=repo-flatpak build-flatpak flatpak/com.canarybuilds.VertexWrite.yml
```

## Create a distributable bundle (optional)

```bash
flatpak build-bundle repo-flatpak com.canarybuilds.VertexWrite.flatpak com.canarybuilds.VertexWrite
```

## Submit to Flathub (website)

Flathub does not accept direct binary uploads. You submit a pull request to the
`flathub/flathub` GitHub repository.

```bash
git clone https://github.com/flathub/flathub.git
cd flathub
git checkout -b new-pr
cp /path/to/vertexwrite/flatpak/com.canarybuilds.VertexWrite.yml .
cp /path/to/vertexwrite/flatpak/vertexwrite-wrapper .
cp /path/to/vertexwrite/flatpak/com.canarybuilds.VertexWrite.desktop .
cp /path/to/vertexwrite/flatpak/com.canarybuilds.VertexWrite.metainfo.xml .
git add com.canarybuilds.VertexWrite.yml \
  vertexwrite-wrapper \
  com.canarybuilds.VertexWrite.desktop \
  com.canarybuilds.VertexWrite.metainfo.xml
git commit -m "Add com.canarybuilds.VertexWrite"
git push origin new-pr
```

Then open a PR from your fork `new-pr` branch to `flathub/flathub`.
After review/merge, Flathub builds and publishes automatically.

Before opening the PR, ensure screenshot URLs in
`com.canarybuilds.VertexWrite.metainfo.xml` point to a stable commit/tag URL and
not a moving branch.
