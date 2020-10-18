#!/usr/bin/env bash
set -eu -o pipefail
cd "$(dirname "$(realpath "${0}")")"

DATADIR=${DATADIR:-/usr/share}
LIBDIR=${LIBDIR:-/usr/lib}

# The actual executable
install -Dm 0755 search_provider.py /usr/local/share/dialect/dialect/search_provider.py

# Search provider definition
install -Dm 0644 com.github.gi_lom.dialect.SearchProvider.ini "${DATADIR}"/gnome-shell/search-providers/com.github.gi_lom.dialect.SearchProvider.ini

# DBus configuration (no-systemd)
install -Dm 0644 com.github.gi_lom.dialect.SearchProvider.service.dbus "${DATADIR}"/dbus-1/services/com.github.gi_lom.dialect.SearchProvider.service

# DBus configuration (systemd)
install -Dm 0644 com.github.gi_lom.dialect.SearchProvider.service.systemd "${LIBDIR}"/systemd/user/com.github.gi_lom.dialect.SearchProvider.service
