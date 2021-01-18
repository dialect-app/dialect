<img height="128" src="data/com.github.gi_lom.dialect.svg" align="left"/>

# Dialect

A translation app for GNOME based on Google Translate.

![Dialect](preview.png?raw=true)

## Features

- Translation based on the [googletrans](https://github.com/ssut/py-googletrans) Python API, an unofficial API for Google Translate
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
```
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

If official packages are not available for any of the python dependencies, you can install them from pip:

```bash
pip install googletrans gtts
```

### Building from Git

```bash
git clone https://github.com/gi-lom/dialect.git
cd dialect
meson builddir --prefix=/usr/local
sudo ninja -C builddir install
```

For testing and development purposes, you may run a local build:

```bash
git clone https://github.com/gi-lom/dialect.git
cd dialect
meson builddir
meson configure _build -Dprefix=$(pwd)/builddir/testdir
ninja -C builddir install
ninja -C builddir run
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[GNU General Public License 3 or later](https://www.gnu.org/licenses/gpl-3.0.en.html)
