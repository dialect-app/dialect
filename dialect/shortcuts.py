# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from dialect.define import RES_PATH
from dialect.settings import Settings


@Gtk.Template(resource_path=f'{RES_PATH}/shortcuts.ui')
class DialectShortcutsWindow(Gtk.ShortcutsWindow):
    __gtype_name__ = 'DialectShortcutsWindow'

    translate_shortcut = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback()
    def _on_show(self, _data):
        """ Called on self::show signal """
        self.translate_shortcut.props.visible = not Settings.get().live_translation
        self.translate_shortcut.props.accelerator = Settings.get().translate_accel
