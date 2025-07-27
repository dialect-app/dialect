<img height="128" src="data/app.drey.Dialect.svg" align="left"/>

# Dialect

A translation app for GNOME.

![Dialect](preview.png?raw=true)

## Features

- Translation based on Google Translate
- Translation based on the LibreTranslate API, allowing you to use any public instance
- Translation based on Lingva Translate API</li>
- Translation based on Bing
- Translation based on Yandex
- Translation history
- Automatic language detection
- Text to speech
- Clipboard buttons

## Installation

### Flathub

<a href='https://flathub.org/apps/details/app.drey.Dialect'><img alt='Download on Flathub' src='https://flathub.org/api/badge?svg&locale=en'/></a>

### Arch Linux

The stable version is available from the official `Extra` repository: [`dialect`](https://archlinux.org/packages/extra/any/dialect/) and the latest git revision is available as an AUR package: [`dialect-git`](https://aur.archlinux.org/packages/dialect-git/)

### Fedora

Dialect is available for Fedora 33 and later:

```bash
sudo dnf install dialect
```

### Debian

Dialect is available in Debian 12:

```bash
sudo apt-get install dialect
```

## Building

### Requirements

- Python 3 (>=3.10) `python`
- PyGObject (>=3.51.0) `python-gobject`
- GTK4 (>= 4.17.5) `gtk4`
- libadwaita (>= 1.7.0) `libadwaita`
- libsoup (>= 3.0) `libsoup`
- libsecret
- libspelling
- GStreamer 1.0 `gstreamer`
- Meson `meson`
- Ninja `ninja`
- gTTS `python-gtts`
- Beautiful Soup `python-beautifulsoup4`

If official packages are not available for any of the python dependencies, you can install them from pip:

```bash
pip install gtts
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
