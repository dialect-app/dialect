# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from typing import TypedDict

from gi.repository import Gio, GLib, Secret

from dialect.define import APP_ID

SECRETS_SCHEMA = Secret.Schema.new(
    APP_ID,
    Secret.SchemaFlags.NONE,
    {
        "provider": Secret.SchemaAttributeType.STRING,
    },
)


class ProviderDefaults(TypedDict):
    instance_url: str
    api_key: str
    src_langs: list[str]
    dest_langs: list[str]


class ProviderSettings(Gio.Settings):
    """
    Helper class for providers settings
    """

    def __init__(self, name: str, defaults: ProviderDefaults):
        super().__init__(schema_id=f"{APP_ID}.translator", path=f"/app/drey/Dialect/translators/{name}/")

        self.name = name
        self.defaults = defaults  # set of per-provider defaults
        self._secret_attr = {"provider": name}
        self._api_key: str | None = None

    @property
    def instance_url(self) -> str:
        """Instance url."""
        return self.get_string("instance-url") or self.defaults["instance_url"]

    @instance_url.setter
    def instance_url(self, url: str):
        self.set_string("instance-url", url)

    @property
    def api_key(self) -> str:
        """API key."""

        if self._api_key:
            return self._api_key

        # Check if we have an old API KEY in GSettings for migration
        if gsettings := self.get_string("api-key"):
            self.api_key = gsettings  # Save to secret
            self.set_string("api-key", "")  # Clear GSetting
            return gsettings

        try:
            self._api_key = (
                Secret.password_lookup_sync(SECRETS_SCHEMA, self._secret_attr, None) or self.defaults["api_key"]
            )
            return self._api_key
        except GLib.Error as exc:
            logging.warning(exc)

        return self.defaults["api_key"]

    @api_key.setter
    def api_key(self, api_key: str):
        try:
            if api_key:
                Secret.password_store_sync(
                    SECRETS_SCHEMA,
                    self._secret_attr,
                    Secret.COLLECTION_DEFAULT,
                    f"Dialect provider API KEY for {self.name}",
                    api_key,
                    None,
                )
                self._api_key = api_key
            else:  # Remove secret
                self._api_key = None
                Secret.password_clear_sync(SECRETS_SCHEMA, self._secret_attr, None)

            # Fake change in api-key setting
            self.emit("changed::api-key", "api-key")

        except GLib.Error as exc:
            logging.warning(exc)

    @property
    def src_langs(self) -> list[str]:
        """Recent source languages."""
        return self.get_strv("src-langs") or self.defaults["src_langs"]

    @src_langs.setter
    def src_langs(self, src_langs: list[str]):
        self.set_strv("src-langs", src_langs)

    @property
    def dest_langs(self) -> list[str]:
        """Recent destination languages."""
        return self.get_strv("dest-langs") or self.defaults["dest_langs"]

    @dest_langs.setter
    def dest_langs(self, dest_langs: list[str]):
        self.set_strv("dest-langs", dest_langs)
