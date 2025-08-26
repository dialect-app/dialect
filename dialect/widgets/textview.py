# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# Copyright 2023 Libretto
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk, GObject, Gtk, GtkSource

from dialect.settings import Settings


class TextView(GtkSource.View):
    __gtype_name__ = "TextView"

    activate_mod: bool = GObject.Property(type=bool, default=True)  # type: ignore
    """If activation requieres the mod key"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Set word/char text wrapping
        self.props.wrap_mode = Gtk.WrapMode.WORD_CHAR

        # Key press controller
        key_ctrlr = Gtk.EventControllerKey()
        key_ctrlr.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrlr)

        # Scroll controller
        scroll_ctrlr = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_ctrlr.connect("scroll", self._on_scroll)
        self.add_controller(scroll_ctrlr)

        # Custom font
        self._font_size = Settings.get().system_font_size
        self._font_css_provider = Gtk.CssProvider()

        # Add font CSS provider
        widget_style_context = self.get_style_context()
        widget_style_context.add_provider(self._font_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        widget_style_context.add_class("dialect-sourceview")

    @GObject.Signal()
    def activate(self): ...

    @GObject.Property(type=int)
    def font_size(self) -> int:  # type: ignore
        return self._font_size

    @font_size.setter
    def font_size(self, value: int):
        # Save value
        self._font_size = value
        # Update CSS
        self._font_css_provider.load_from_data(f"textview {{ font-size: {str(value)}pt; }}")

    def font_size_inc(self):
        self.font_size += 5

    def font_size_dec(self):
        new_size = self.font_size - 5
        if new_size >= 6:
            self.font_size = new_size

    def _on_key_pressed(self, _ctrl, keyval: int, _keycode: int, state: Gdk.ModifierType):
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        control_mask = Gdk.ModifierType.CONTROL_MASK
        enter_keys = (Gdk.KEY_Return, Gdk.KEY_KP_Enter)

        # Activate with mod key pressed
        if control_mask == modifiers:
            if keyval in enter_keys:
                if self.activate_mod:
                    self.emit("activate")
                    return Gdk.EVENT_STOP

        # Activate without mod key pressed
        elif keyval in enter_keys:
            if not self.activate_mod:
                self.emit("activate")
                return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def _on_scroll(self, ctrl: Gtk.EventControllerScroll, _dx: float, dy: float):
        state = ctrl.get_current_event_state()

        # If Control modifier is pressed
        if state == Gdk.ModifierType.CONTROL_MASK:
            if dy > 0:
                self.font_size_dec()
            else:
                self.font_size_inc()

            # Stop propagation
            return Gdk.EVENT_STOP

        # Propagate event (scrolled window, etc)
        return Gdk.EVENT_PROPAGATE
