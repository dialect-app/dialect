# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gtk

from dialect.define import RES_PATH
from dialect.widgets import ProviderRow


@Gtk.Template(resource_path=f'{RES_PATH}/providers-list.ui')
class ProvidersList(Adw.Bin):
    __gtype_name__ = 'ProvidersList'

    # Child widgets
    list = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def bind_model(self, model):
        self.model = model
        self.list.bind_model(self.model, self._create_rows)

    @Gtk.Template.Callback()
    def _on_provider_activated(self, _pspec, expanded_row):
        """ Called on self.list::row-activated signal
            Cretes an accordion effect
        """
        if not expanded_row.props.expanded:
            return

        for i in range(self.model.get_n_items()):
            row = self.list.get_row_at_index(i)

            if row == expanded_row:
                continue

            row.props.expanded = False

    def _create_rows(self, item):
        row = ProviderRow(item)
        row.props.selectable = False
        row.props.activatable = True
        return row
