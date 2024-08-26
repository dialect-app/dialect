# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from dialect.define import RES_PATH


@Gtk.Template(resource_path=f"{RES_PATH}/widgets/voice_button.ui")
class VoiceButton(Gtk.Button):
    __gtype_name__ = "VoiceButton"

    stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    progress_bar: Gtk.ProgressBar = Gtk.Template.Child()  # type: ignore

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def ready(self):
        self.stack.props.visible_child_name = "ready"
        self.props.tooltip_text = _("Listen")
        self.progress_bar.props.visible = False

    def progress(self, fraction: float):
        if self.stack.props.visible_child_name != "progress":
            self.stack.props.visible_child_name = "progress"
            self.props.tooltip_text = _("Cancel Audio")
            self.progress_bar.props.visible = True

        self.progress_bar.props.fraction = fraction

    def error(self, message: str = _("A network issue has occurred. Retry?")):
        self.stack.props.visible_child_name = "error"
        self.props.tooltip_text = message
        self.progress_bar.props.visible = False

    def loading(self):
        self.stack.props.visible_child_name = "loading"
        self.props.tooltip_text = _("Loading…")
        self.progress_bar.props.visible = False
