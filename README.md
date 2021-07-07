<img height="128" src="data/com.github.gi_lom.dialect.svg" align="left"/>

# Dialect

A translation app for GNOME.

![Dialect](preview.png?raw=true)

## Features

- Translation based on the [googletrans](https://github.com/ssut/py-googletrans) Python API, an unofficial API for Google Translate
- Translation based on the LibreTranslate API, allowing you to use any public instance
- Translation history
- Automatic language detection
- Text to speech
- Clipboard buttons

## Installation

### Flathub

<a href='https://flathub.org/apps/details/com.github.gi_lom.dialect'><img width='240' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

### AUR

Arch-based distro users can install from the AUR: [`dialect`](https://aur.archlinux.org/packages/dialect) for the stable version or [`dialect-git`](https://aur.archlinux.org/packages/dialect-git/) for the latest git revision.

### Fedora

Dialect is available for Fedora 33 and later:

```bash
sudo dnf install dialect
```

## Building

### Requirements

- Python 3 `python`
- PyGObject `python-gobject`
- GTK3 `gtk3`
- libhandy (>= 0.90.0) `libhandy`
- GStreamer 1.0 `gstreamer`
- Meson `meson`
- Ninja `ninja`
- Googletrans `python-googletrans`
- gTTS `python-gtts`
- D-Bus `python-dbus`
- HTTPX `python-httpx`

If official packages are not available for any of the python dependencies, you can install them from pip:

```bash
pip install googletrans gtts
```

### Building from Git

```bash
git clone --recurse-submodules https://github.com/dialect-app/dialect.git
cd dialect
meson builddir --prefix=/usr/local
sudo ninja -C builddir install
```

For testing and development purposes, you may run a local build:

```bash
git clone --recurse-submodules https://github.com/dialect-app/dialect.git
cd dialect
meson builddir
meson configure builddir -Dprefix=$(pwd)/builddir/testdir
ninja -C builddir install
ninja -C builddir run
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

### Translations

Dialect has already been translated into many languages (see the [translations repository](https://github.com/dialect-app/po/blob/main/README.md) file). Please help translate Dialect into more languages through [Weblate](https://hosted.weblate.org/engage/dialect/).

<a href="https://hosted.weblate.org/engage/dialect/">
<img src="https://hosted.weblate.org/widgets/dialect/-/dialect/multi-auto.svg" alt="Translation status" />
</a>

## License

[GNU General Public License 3 or later](https://www.gnu.org/licenses/gpl-3.0.en.html)
