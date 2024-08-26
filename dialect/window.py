# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# Copyright 2023 Libretto
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from typing import IO, Literal

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gst, Gtk

from dialect.define import APP_ID, PROFILE, RES_PATH, TRANS_NUMBER
from dialect.languages import LanguagesListModel
from dialect.providers import (
    TRANSLATORS,
    TTS,
    ProviderError,
    ProviderErrorCode,
    ProviderFeature,
)
from dialect.providers.base import BaseProvider, Translation
from dialect.settings import Settings
from dialect.shortcuts import DialectShortcutsWindow
from dialect.utils import find_item_match, first_exclude
from dialect.widgets import LangSelector, TextView, ThemeSwitcher, VoiceButton


@Gtk.Template(resource_path=f"{RES_PATH}/window.ui")
class DialectWindow(Adw.ApplicationWindow):
    __gtype_name__ = "DialectWindow"

    # Properties
    translator_loading: bool = GObject.Property(type=bool, default=True)  # type: ignore

    # Child widgets
    menu_btn: Gtk.MenuButton = Gtk.Template.Child()  # type: ignore
    main_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    error_page: Adw.StatusPage = Gtk.Template.Child()  # type: ignore
    translator_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    key_page: Adw.StatusPage = Gtk.Template.Child()  # type: ignore
    rmv_key_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    error_api_key_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore

    title_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    langs_button_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    switch_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    src_lang_selector: LangSelector = Gtk.Template.Child()  # type: ignore
    dest_lang_selector: LangSelector = Gtk.Template.Child()  # type: ignore

    return_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    forward_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore

    src_pron_revealer: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    src_pron_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    mistakes: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    mistakes_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    char_counter: Gtk.Label = Gtk.Template.Child()  # type: ignore
    src_text: TextView = Gtk.Template.Child()  # type: ignore
    clear_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    paste_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    src_voice_btn: VoiceButton = Gtk.Template.Child()  # type: ignore
    translate_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore

    dest_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    dest_pron_revealer: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    dest_pron_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    dest_text: TextView = Gtk.Template.Child()  # type: ignore
    dest_toolbar_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    trans_spinner: Adw.Spinner = Gtk.Template.Child()  # type: ignore
    trans_warning: Gtk.Image = Gtk.Template.Child()  # type: ignore
    edit_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    copy_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    dest_voice_btn: VoiceButton = Gtk.Template.Child()  # type: ignore

    actionbar: Gtk.ActionBar = Gtk.Template.Child()  # type: ignore
    src_lang_selector_m: LangSelector = Gtk.Template.Child()  # type: ignore
    dest_lang_selector_m: LangSelector = Gtk.Template.Child()  # type: ignore

    toast: Adw.Toast | None = None  # for notification management
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()  # type: ignore

    win_key_ctrlr: Gtk.EventControllerKey = Gtk.Template.Child()  # type: ignore

    # Providers objects
    provider: dict[str, BaseProvider | None] = {"trans": None, "tts": None}

    # Text to speech
    current_speech: dict[str, str] = {}
    voice_loading = False  # tts loading status

    # Preset language values
    src_langs: list[str] = []
    dest_langs: list[str] = []

    current_history = 0  # for history management

    # Translation-related variables
    next_trans = {}  # for ongoing translation
    ongoing_trans = False  # for ongoing translation
    trans_failed = False  # for monitoring connectivity issues
    trans_mistakes: tuple[str | None, str | None] = (None, None)  # "mistakes" suggestions
    # Pronunciations
    trans_src_pron = None
    trans_dest_pron = None
    # Suggestions
    before_suggest = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Application object
        self.app: Adw.Application = kwargs["application"]

        # GStreamer playbin object and related setup
        self.player = Gst.ElementFactory.make("playbin", "player")
        if self.player:
            if bus := self.player.get_bus():
                bus.add_signal_watch()
                bus.connect("message", self._on_gst_message)

        # Setup window
        self.setup_actions()
        self.setup()

    def setup_actions(self):
        back = Gio.SimpleAction(name="back")
        back.props.enabled = False
        back.connect("activate", self.ui_return)
        self.add_action(back)

        forward_action = Gio.SimpleAction(name="forward")
        forward_action.props.enabled = False
        forward_action.connect("activate", self.ui_forward)
        self.add_action(forward_action)

        switch_action = Gio.SimpleAction(name="switch")
        switch_action.connect("activate", self.ui_switch)
        self.add_action(switch_action)

        from_action = Gio.SimpleAction(name="from")
        from_action.connect("activate", self.ui_from)
        self.add_action(from_action)

        to_action = Gio.SimpleAction(name="to")
        to_action.connect("activate", self.ui_to)
        self.add_action(to_action)

        clear_action = Gio.SimpleAction(name="clear")
        clear_action.props.enabled = False
        clear_action.connect("activate", self.ui_clear)
        self.add_action(clear_action)

        font_size_inc_action = Gio.SimpleAction(name="font-size-inc")
        font_size_inc_action.connect("activate", self.ui_font_size_inc)
        self.add_action(font_size_inc_action)

        font_size_dec_action = Gio.SimpleAction(name="font-size-dec")
        font_size_dec_action.connect("activate", self.ui_font_size_dec)
        self.add_action(font_size_dec_action)

        paste_action = Gio.SimpleAction(name="paste")
        paste_action.connect("activate", self.ui_paste)
        self.add_action(paste_action)

        copy_action = Gio.SimpleAction(name="copy")
        copy_action.props.enabled = False
        copy_action.connect("activate", self.ui_copy)
        self.add_action(copy_action)

        listen_dest_action = Gio.SimpleAction(name="listen-dest")
        listen_dest_action.connect("activate", self.ui_dest_voice)
        listen_dest_action.props.enabled = False
        self.add_action(listen_dest_action)

        suggest_action = Gio.SimpleAction(name="suggest")
        suggest_action.props.enabled = False
        suggest_action.connect("activate", self.ui_suggest)
        self.add_action(suggest_action)

        suggest_ok_action = Gio.SimpleAction(name="suggest-ok")
        suggest_ok_action.connect("activate", self.ui_suggest_ok)
        self.add_action(suggest_ok_action)

        suggest_cancel_action = Gio.SimpleAction(name="suggest-cancel")
        suggest_cancel_action.connect("activate", self.ui_suggest_cancel)
        self.add_action(suggest_cancel_action)

        listen_src_action = Gio.SimpleAction(name="listen-src")
        listen_src_action.connect("activate", self.ui_src_voice)
        listen_src_action.props.enabled = False
        self.add_action(listen_src_action)

        translation_action = Gio.SimpleAction(name="translation")
        translation_action.props.enabled = False
        translation_action.connect("activate", self.translation)
        self.add_action(translation_action)

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Set devel style
        if PROFILE == "Devel":
            self.add_css_class("devel")

        # Theme Switcher
        theme_switcher = ThemeSwitcher()
        menu: Gtk.PopoverMenu = self.menu_btn.props.popover  # type: ignore
        menu.add_child(theme_switcher, "theme")

        # Save settings on close
        self.connect("unrealize", self.save_settings)

        self.setup_selectors()
        self.setup_translation()
        self.set_help_overlay(DialectShortcutsWindow())

        # Load translator
        self.load_translator()
        # Load text to speech
        self.load_tts()

        # Listen to active providers changes
        Settings.get().connect("translator-changed", self._on_active_provider_changed, "trans")
        Settings.get().connect("tts-changed", self._on_active_provider_changed, "tts")

        # Bind text views font size
        self.src_text.bind_property("font-size", self.dest_text, "font-size", GObject.BindingFlags.BIDIRECTIONAL)

        # Set initial saved text view font size
        if Settings.get().custom_default_font_size:
            font_size = Settings.get().default_font_size
            self.set_font_size(font_size)

        # Set src textview mod key requirement
        self.src_text.activate_mod = not bool(Settings.get().translate_accel_value)
        Settings.get().connect(
            "changed::translate-accel",
            lambda s, _k: self.src_text.set_property("activate_mod", not bool(s.translate_accel_value)),
        )

    def setup_selectors(self):
        def lang_names_func(code: str):
            return self.provider["trans"].get_lang_name(code)  # type: ignore

        # Languages models
        self.src_lang_model = LanguagesListModel(lang_names_func)
        self.src_recent_lang_model = LanguagesListModel(lang_names_func)
        self.dest_lang_model = LanguagesListModel(lang_names_func)
        self.dest_recent_lang_model = LanguagesListModel(lang_names_func)

        # Src lang selector
        self.src_lang_selector.bind_models(self.src_lang_model, self.src_recent_lang_model)
        self.src_lang_selector_m.bind_models(self.src_lang_model, self.src_recent_lang_model)

        # Dest lang selector
        self.dest_lang_selector.bind_models(self.dest_lang_model, self.dest_recent_lang_model)
        self.dest_lang_selector_m.bind_models(self.dest_lang_model, self.dest_recent_lang_model)

        self.langs_button_box.props.homogeneous = False

    def setup_translation(self):
        # Src buffer
        self.src_buffer = self.src_text.props.buffer
        self.src_buffer.connect("changed", self.on_src_text_changed)
        self.src_buffer.connect("end-user-action", self.user_action_ended)

        # Dest buffer
        self.dest_buffer = self.dest_text.props.buffer
        self.dest_buffer.props.text = ""
        self.dest_buffer.connect("changed", self.on_dest_text_changed)
        # Translation progress spinner
        self.trans_spinner.hide()
        self.trans_warning.hide()

        self.toggle_voice_spinner(True)

    def load_translator(self):
        def on_done():
            if not self.provider["trans"]:
                return

            # Mistakes support
            if ProviderFeature.MISTAKES not in self.provider["trans"].features:
                self.mistakes.props.reveal_child = False

            # Suggestions support
            self.ui_suggest_cancel(None, None)
            if ProviderFeature.SUGGESTIONS not in self.provider["trans"].features:
                self.edit_btn.props.visible = False
            else:
                self.edit_btn.props.visible = True

            # Pronunciation support
            if ProviderFeature.PRONUNCIATION not in self.provider["trans"].features:
                self.src_pron_revealer.props.reveal_child = False
                self.dest_pron_revealer.props.reveal_child = False
                self.app.lookup_action("pronunciation").props.enabled = False  # type: ignore
            else:
                self.app.lookup_action("pronunciation").props.enabled = True  # type: ignore

            # Update langs
            self.src_lang_model.set_langs(self.provider["trans"].src_languages)
            self.dest_lang_model.set_langs(self.provider["trans"].dest_languages)

            # Update selected langs
            set_auto = Settings.get().src_auto and ProviderFeature.DETECTION in self.provider["trans"].features
            src_lang = self.provider["trans"].src_languages[0]
            if self.src_langs and self.src_langs[0] in self.provider["trans"].src_languages:
                src_lang = self.src_langs[0]
            self.src_lang_selector.selected = "auto" if set_auto else src_lang

            dest_lang = self.provider["trans"].dest_languages[1]
            if self.dest_langs and self.dest_langs[0] in self.provider["trans"].dest_languages:
                dest_lang = self.dest_langs[0]
            self.dest_lang_selector.selected = dest_lang

            # Update chars limit
            if self.provider["trans"].chars_limit == -1:  # -1 means unlimited
                self.char_counter.props.label = ""
            else:
                count = f"{str(self.src_buffer.get_char_count())}/{self.provider['trans'].chars_limit}"
                self.char_counter.props.label = count

            self.translator_loading = False

            self.check_apikey()

        def on_fail(error: ProviderError):
            self.translator_loading = False
            self.loading_failed(error)

        provider = Settings.get().active_translator

        # Show loading view
        self.main_stack.props.visible_child_name = "loading"

        # Translator object
        self.provider["trans"] = TRANSLATORS[provider]()
        # Get saved languages
        self.src_langs = self.provider["trans"].recent_src_langs
        self.dest_langs = self.provider["trans"].recent_dest_langs
        # Do provider init
        self.provider["trans"].init_trans(on_done, on_fail)

        # Connect to provider settings changes
        self.provider["trans"].settings.connect(
            "changed::instance-url", self._on_provider_changed, self.provider["trans"].name
        )
        self.provider["trans"].settings.connect(
            "changed::api-key", self._on_provider_changed, self.provider["trans"].name
        )

    def check_apikey(self):
        def on_done(valid: bool):
            if valid:
                self.main_stack.props.visible_child_name = "translate"
            else:
                self.api_key_failed()

        def on_fail(error: ProviderError):
            self.loading_failed(error)

        if not self.provider["trans"]:
            return

        if ProviderFeature.API_KEY in self.provider["trans"].features:
            if self.provider["trans"].api_key:
                self.provider["trans"].validate_api_key(self.provider["trans"].api_key, on_done, on_fail)
            elif (
                not self.provider["trans"].api_key
                and ProviderFeature.API_KEY_REQUIRED in self.provider["trans"].features
            ):
                self.api_key_failed(required=True)
            else:
                self.main_stack.props.visible_child_name = "translate"
        else:
            self.main_stack.props.visible_child_name = "translate"

    def loading_failed(self, error: ProviderError):
        if not self.provider["trans"]:
            return

        # Api Key error
        if error.code in (ProviderErrorCode.API_KEY_INVALID, ProviderErrorCode.API_KEY_REQUIRED):
            self.api_key_failed(error.code == ProviderErrorCode.API_KEY_REQUIRED)

        # Other errors
        else:
            self.main_stack.props.visible_child_name = "error"

            service = self.provider["trans"].prettyname
            url = self.provider["trans"].instance_url

            title = _("Failed loading the translation service")
            description = _("Please report this in the Dialect bug tracker if the issue persists.")
            if ProviderFeature.INSTANCES in self.provider["trans"].features:
                description = _(
                    (
                        'Failed loading "{url}", check if the instance address is correct or report in the Dialect bug tracker'
                        " if the issue persists."
                    )
                )
                description = description.format(url=url)

            if error.code == ProviderErrorCode.NETWORK:
                title = _("Couldn’t connect to the translation service")
                description = _("We can’t connect to the server. Please check for network issues.")
                if ProviderFeature.INSTANCES in self.provider["trans"].features:
                    description = _(
                        (
                            "We can’t connect to the {service} instance “{url}”.\n"
                            "Please check for network issues or if the address is correct."
                        )
                    )
                    description = description.format(service=service, url=url)

            if error.message:
                description = description + "\n\n<small><tt>" + error.message + "</tt></small>"

            self.error_page.props.title = title
            self.error_page.props.description = description

    def api_key_failed(self, required=False):
        if not self.provider["trans"]:
            return

        if required:
            self.key_page.props.title = _("API key is required to use the service")
            self.key_page.props.description = _("Please set an API key in the preferences.")

        else:
            self.key_page.props.title = _("The provided API key is invalid")
            if ProviderFeature.API_KEY_REQUIRED in self.provider["trans"].features:
                self.key_page.props.description = _("Please set a valid API key in the preferences.")
            else:
                self.key_page.props.description = _(
                    "Please set a valid API key or unset the API key in the preferences."
                )
                self.rmv_key_btn.props.visible = True
                self.error_api_key_btn.props.visible = True

        self.main_stack.props.visible_child_name = "api-key"

    @Gtk.Template.Callback()
    def retry_load_translator(self, _button):
        self.load_translator()

    @Gtk.Template.Callback()
    def remove_key_and_reload(self, _button):
        if self.provider["trans"]:
            self.provider["trans"].reset_api_key()
        self.load_translator()

    def load_tts(self):
        def on_done():
            self.download_speech()

        def on_fail(_error: ProviderError):
            self.on_listen_failed()

        # TTS name
        provider = Settings.get().active_tts

        # Check if TTS is disabled
        if provider != "":
            self.src_voice_btn.props.visible = True
            self.dest_voice_btn.props.visible = True

            # TTS Object
            self.provider["tts"] = TTS[provider]()
            self.provider["tts"].init_tts(on_done, on_fail)

            # Connect to provider settings changes
            self.provider["tts"].settings.connect(
                "changed::instance-url", self._on_provider_changed, self.provider["tts"].name
            )
            self.provider["tts"].settings.connect(
                "changed::api-key", self._on_provider_changed, self.provider["tts"].name
            )
        else:
            self.provider["tts"] = None
            self.src_voice_btn.props.visible = False
            self.dest_voice_btn.props.visible = False

    def on_listen_failed(self):
        if not self.provider["tts"]:
            return

        self.src_voice_btn.error()
        self.dest_voice_btn.error()

        if self.current_speech:
            called_from = self.current_speech["called_from"]
            action = {
                "label": _("Retry"),
                "name": "win.listen-src" if called_from == "src" else "win.listen-dest",
            }
        else:
            action = None

        self.send_notification(_("A network issue has occurred. Please try again."), action=action)

        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)

        if self.provider["tts"].tts_languages:
            self.lookup_action("listen-src").set_enabled(  # type: ignore
                self.src_lang_selector.selected in self.provider["tts"].tts_languages and src_text != ""
            )
            self.lookup_action("listen-dest").set_enabled(  # type: ignore
                self.dest_lang_selector.selected in self.provider["tts"].tts_languages and dest_text != ""
            )
        else:
            self.lookup_action("listen-src").props.enabled = src_text != ""  # type: ignore
            self.lookup_action("listen-dest").props.enabled = dest_text != ""  # type: ignore

    def translate(self, text: str, src_lang: str | None, dest_lang: str | None):
        """
        Translates the given text from auto detected language to last used
        language
        """
        if not self.provider["trans"]:
            return

        # Set src lang to Auto
        if src_lang is None:
            self.src_lang_selector.selected = "auto"
        else:
            self.src_lang_selector.selected = src_lang
        if dest_lang is not None and dest_lang in self.provider["trans"].dest_languages:
            self.dest_lang_selector.selected = dest_lang
            self.dest_lang_selector.emit("user-selection-changed")
        # Set text to src buffer
        self.src_buffer.props.text = text
        # Run translation
        self.translation()

    def translate_selection(self, src_lang: str | None, dest_lang: str | None):
        def on_paste(clipboard, result):
            text = clipboard.read_text_finish(result)
            self.translate(text, src_lang, dest_lang)

        if display := Gdk.Display.get_default():
            display.get_primary_clipboard().read_text_async(None, on_paste)

    def save_settings(self, *args, **kwargs):
        if not self.is_maximized():
            size = self.get_default_size()
            Settings.get().window_size = (size.width, size.height)  # type: ignore
        if self.provider["trans"] is not None:
            self.provider["trans"].recent_src_langs = self.src_langs
            self.provider["trans"].recent_dest_langs = self.dest_langs

    def send_notification(
        self,
        text: str,
        queue: bool | None = False,
        action: dict[str, str] | None = None,
        timeout=5,
        priority=Adw.ToastPriority.NORMAL,
    ):
        """
        Display an in-app notification.

        Args:
            text: The text or message of the notification.
            queue: If True, the notification will be queued.
            action: A dict containing the action to be called.
            timeout: Toast timeout.
            timeout: Toast priority.
        """

        def toast_dismissed(_toast: Adw.Toast):
            self.toast = None

        if not queue and self.toast is not None:
            self.toast.dismiss()
        self.toast = Adw.Toast(title=text)
        self.toast.connect("dismissed", toast_dismissed)
        if action is not None:
            self.toast.props.button_label = action["label"]
            self.toast.props.action_name = action["name"]
        self.toast.props.timeout = timeout
        self.toast.props.priority = priority
        self.toast_overlay.add_toast(self.toast)

    def toggle_voice_spinner(self, active=True):
        if not self.provider["tts"]:
            return

        if active:
            self.lookup_action("listen-src").props.enabled = False  # type: ignore
            self.src_voice_btn.loading()

            self.lookup_action("listen-dest").props.enabled = False  # type: ignore
            self.dest_voice_btn.loading()
        else:
            src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
            self.lookup_action("listen-src").set_enabled(  # type: ignore
                self.src_lang_selector.selected in self.provider["tts"].tts_languages and src_text != ""
            )
            self.src_voice_btn.ready()

            dest_text = self.dest_buffer.get_text(
                self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True
            )
            self.lookup_action("listen-dest").set_enabled(  # type: ignore
                self.dest_lang_selector.selected in self.provider["tts"].tts_languages and dest_text != ""
            )
            self.dest_voice_btn.ready()

    @Gtk.Template.Callback()
    def _on_src_lang_changed(self, _obj, _param):
        """Called on self.src_lang_selector::notify::selected signal"""
        if not self.provider["trans"]:
            return

        code = self.src_lang_selector.selected
        dest_code = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)

        if self.provider["trans"].cmp_langs(code, dest_code):
            # Get first lang from saved src langs that is not current dest
            if valid := first_exclude(self.src_langs, dest_code):
                # Check if it's a valid dest lang
                valid = find_item_match([valid], self.provider["trans"].dest_languages)
            if not valid:  # If not, just get the first lang from the list that is not selected
                valid = first_exclude(self.provider["trans"].dest_languages, dest_code)

            self.dest_lang_selector.selected = valid or ""

        # Disable or enable listen function.
        if self.provider["tts"] and Settings.get().active_tts != "":
            self.lookup_action("listen-src").set_enabled(code in self.provider["tts"].tts_languages and src_text != "")  # type: ignore

        if code in self.provider["trans"].src_languages:
            # Update saved src langs list
            if code in self.src_langs:
                # Bring lang to the top
                self.src_langs.remove(code)
            elif code.lower() in self.src_langs:
                # Bring lang to the top
                self.src_langs.remove(code.lower())
            elif len(self.src_langs) == 4:
                self.src_langs.pop()
            self.src_langs.insert(0, code)

        # Rewrite recent langs
        self.src_recent_lang_model.set_langs(self.src_langs, auto=True)

        self._check_switch_enabled()

    @Gtk.Template.Callback()
    def _on_dest_lang_changed(self, _obj, _param):
        """Called on self.dest_lang_selector::notify::selected signal"""
        if not self.provider["trans"]:
            return

        code = self.dest_lang_selector.selected
        src_code = self.src_lang_selector.selected
        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)

        if self.provider["trans"].cmp_langs(code, src_code):
            # Get first lang from saved dest langs that is not current src
            if valid := first_exclude(self.dest_langs, src_code):
                # Check if it's a valid src lang
                valid = find_item_match([valid], self.provider["trans"].src_languages)
            if not valid:  # If not, just get the first lang from the list that is not selected
                valid = first_exclude(self.provider["trans"].src_languages, src_code)

            self.src_lang_selector.selected = valid or ""

        # Disable or enable listen function.
        if self.provider["tts"] and Settings.get().active_tts != "":
            self.lookup_action("listen-dest").set_enabled(  # type: ignore
                code in self.provider["tts"].tts_languages and dest_text != ""
            )

        # Update saved dest langs list
        if code in self.dest_langs:
            # Bring lang to the top
            self.dest_langs.remove(code)
        elif code.lower() in self.dest_langs:
            # Bring lang to the top
            self.dest_langs.remove(code.lower())
        elif len(self.src_langs) == 4:
            self.dest_langs.pop()
        self.dest_langs.insert(0, code)

        # Rewrite recent langs
        self.dest_recent_lang_model.set_langs(self.dest_langs)

        self._check_switch_enabled()

    def _check_switch_enabled(self):
        if not self.provider["trans"]:
            return

        # Disable or enable switch function.
        self.lookup_action("switch").props.enabled = (  # type: ignore
            self.src_lang_selector.selected in self.provider["trans"].dest_languages
            and self.dest_lang_selector.selected in self.provider["trans"].src_languages
        )

    """
    User interface functions
    """

    def ui_return(self, _action, _param):
        """Go back one step in history."""
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self.history_update()

    def ui_forward(self, _action, _param):
        """Go forward one step in history."""
        if self.current_history != 0:
            self.current_history -= 1
            self.history_update()

    def add_history_entry(self, translation: Translation):
        """Add a history entry to the history list."""
        if not self.provider["trans"]:
            return

        if self.current_history > 0:
            del self.provider["trans"].history[: self.current_history]
            self.current_history = 0
        if len(self.provider["trans"].history) == TRANS_NUMBER:
            self.provider["trans"].history.pop()
        self.provider["trans"].history.insert(0, translation)
        GLib.idle_add(self.reset_return_forward_btns)

    def switch_all(self, src_language: str, dest_language: str, src_text: str, dest_text: str):
        self.src_lang_selector.selected = dest_language
        self.dest_lang_selector.selected = src_language
        self.src_buffer.props.text = dest_text
        self.dest_buffer.props.text = src_text
        self.add_history_entry(Translation(src_text, (dest_text, src_language, dest_language)))

        # Re-enable widgets
        self.langs_button_box.props.sensitive = True
        self.lookup_action("translation").props.enabled = self.src_buffer.get_char_count() != 0  # type: ignore

    def ui_switch(self, _action, _param):
        # Get variables
        self.langs_button_box.props.sensitive = False
        self.lookup_action("translation").props.enabled = False  # type: ignore
        src_language = self.src_lang_selector.selected
        dest_language = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)
        if src_language == "auto":
            return

        # Switch all
        self.switch_all(src_language, dest_language, src_text, dest_text)

    def ui_from(self, _action, _param):
        self.src_lang_selector.button.popup()

    def ui_to(self, _action, _param):
        self.dest_lang_selector.button.popup()

    def ui_clear(self, _action, _param):
        self.src_buffer.props.text = ""
        self.src_buffer.emit("end-user-action")

    def set_font_size(self, size: int):
        self.src_text.font_size = size

    def ui_font_size_inc(self, _action, _param):
        self.src_text.font_size_inc()

    def ui_font_size_dec(self, _action, _param):
        self.src_text.font_size_dec()

    def ui_copy(self, _action, _param):
        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)
        if display := Gdk.Display.get_default():
            display.get_clipboard().set(dest_text)
            self.send_notification(_("Copied to clipboard"), timeout=1)

    def ui_paste(self, _action, _param):
        def on_paste(clipboard: Gdk.Clipboard, result: Gio.AsyncResult):
            text = clipboard.read_text_finish(result)
            if text is not None:
                end_iter = self.src_buffer.get_end_iter()
                self.src_buffer.insert(end_iter, text)
                self.src_buffer.emit("end-user-action")

        if display := Gdk.Display.get_default():
            display.get_clipboard().read_text_async(None, on_paste)

    def ui_suggest(self, _action, _param):
        self.dest_toolbar_stack.props.visible_child_name = "edit"
        self.before_suggest = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True
        )
        self.dest_text.props.editable = True

    def ui_suggest_ok(self, _action, _param):
        def on_done(success):
            self.dest_toolbar_stack.props.visible_child_name = "default"

            if success:
                self.send_notification(_("New translation has been suggested!"))
            else:
                self.send_notification(_("Suggestion failed."))

            self.dest_text.props.editable = False

        def on_fail(error: ProviderError):
            self.dest_toolbar_stack.props.visible_child_name = "default"
            self.send_notification(_("Suggestion failed."))
            self.dest_text.props.editable = False

        if not self.provider["trans"]:
            return

        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)

        src, dest = self.provider["trans"].denormalize_lang(
            self.provider["trans"].history[self.current_history].original[1],
            self.provider["trans"].history[self.current_history].original[2],
        )

        self.provider["trans"].suggest(
            self.provider["trans"].history[self.current_history].original[0], src, dest, dest_text, on_done, on_fail
        )

        self.before_suggest = None

    def ui_suggest_cancel(self, _action, _param):
        self.dest_toolbar_stack.props.visible_child_name = "default"
        if self.before_suggest is not None:
            self.dest_buffer.props.text = self.before_suggest
            self.before_suggest = None
        self.dest_text.props.editable = False

    def ui_src_voice(self, _action, _param):
        if self.current_speech:
            self._voice_reset()
            return

        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        src_language = self.src_lang_selector.selected
        self._pre_speech(src_text, src_language, "src")

    def ui_dest_voice(self, _action, _param):
        if self.current_speech:
            self._voice_reset()
            return

        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)
        dest_language = self.dest_lang_selector.selected
        self._pre_speech(dest_text, dest_language, "dest")

    def _pre_speech(self, text: str, lang: str, called_from: Literal["src", "dest"]):
        if text != "":
            self.voice_loading = True
            self.toggle_voice_spinner(True)

            self.current_speech = {"text": text, "lang": lang, "called_from": called_from}

            self.download_speech()

    def _voice_reset(self):
        if not self.player:
            return

        self.player.set_state(Gst.State.NULL)
        self.current_speech = {}
        self.src_voice_btn.ready()
        self.dest_voice_btn.ready()

    def _on_gst_message(self, _bus, message: Gst.Message):
        if message.type == Gst.MessageType.EOS or message.type == Gst.MessageType.ERROR:
            if message.type == Gst.MessageType.ERROR:
                logging.error("Some error occurred while trying to play.")

            self._voice_reset()

    def _gst_progress_timeout(self):
        if not self.player:
            return False

        if self.current_speech and self.player.get_state(Gst.CLOCK_TIME_NONE) != Gst.State.NULL:
            have_pos, pos = self.player.query_position(Gst.Format.TIME)
            have_dur, dur = self.player.query_duration(Gst.Format.TIME)

            if have_pos and have_dur:
                if self.current_speech["called_from"] == "src":
                    self.src_voice_btn.progress(pos / dur)
                else:
                    self.dest_voice_btn.progress(pos / dur)

            return True

        return False

    def download_speech(self):
        def on_done(file: IO):
            try:
                self._play_audio(file.name)
                file.close()
            except Exception as exc:
                logging.error(exc)
                self.on_listen_failed()
            else:
                self.toggle_voice_spinner(False)
            finally:
                self.voice_loading = False

        def on_fail(_error: ProviderError):
            self.on_listen_failed()
            self.toggle_voice_spinner(False)

        if not self.provider["tts"]:
            return

        if self.current_speech:
            lang: str = self.provider["tts"].denormalize_lang(self.current_speech["lang"])  # type: ignore
            self.provider["tts"].speech(self.current_speech["text"], lang, on_done, on_fail)
        else:
            self.toggle_voice_spinner(False)
            self.voice_loading = False

    def _play_audio(self, path: str):
        if not self.player:
            return

        uri = "file://" + path
        self.player.set_property("uri", uri)
        self.player.set_state(Gst.State.PLAYING)
        GLib.timeout_add(50, self._gst_progress_timeout)

    @Gtk.Template.Callback()
    def _on_key_event(self, _ctrl, keyval: int, _keycode: int, state: Gdk.ModifierType):
        """Called on self.win_key_ctrlr::key-pressed signal"""
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyval)
        if (
            GLib.unichar_isgraph(chr(unicode_key_val))
            and modifiers in (shift_mask, 0)
            and not self.dest_text.props.editable
            and not self.src_text.is_focus()
        ):
            self.src_text.grab_focus()
            end_iter = self.src_buffer.get_end_iter()
            self.src_buffer.insert(end_iter, chr(unicode_key_val))
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    @Gtk.Template.Callback()
    def _on_src_activated(self, _texview):
        """Called on self.src_text::active signal"""
        if not Settings.get().live_translation:
            self.translation()

    @Gtk.Template.Callback()
    def _on_mistakes_clicked(self, _button, _data):
        """Called on self.mistakes_label::activate-link signal"""
        self.mistakes.props.reveal_child = False
        if self.trans_mistakes[1]:
            self.src_buffer.props.text = self.trans_mistakes[1]
        # Run translation again
        self.translation()

        return Gdk.EVENT_STOP

    def on_src_text_changed(self, buffer: Gtk.TextBuffer):
        if not self.provider["trans"]:
            return

        char_count = buffer.get_char_count()

        # If the text is over the highest number of characters allowed, it is truncated.
        # This is done for avoiding exceeding the limit imposed by translation services.
        if self.provider["trans"].chars_limit == -1:  # -1 means unlimited
            self.char_counter.props.label = ""
        else:
            self.char_counter.props.label = f'{str(char_count)}/{self.provider["trans"].chars_limit}'

            if char_count >= self.provider["trans"].chars_limit:
                self.send_notification(_("{} characters limit reached!").format(self.provider["trans"].chars_limit))
                buffer.delete(buffer.get_iter_at_offset(self.provider["trans"].chars_limit), buffer.get_end_iter())

        sensitive = char_count != 0
        self.lookup_action("translation").props.enabled = sensitive  # type: ignore
        self.lookup_action("clear").props.enabled = sensitive  # type: ignore
        if not self.voice_loading and self.provider["tts"]:
            self.lookup_action("listen-src").set_enabled(  # type: ignore
                self.src_lang_selector.selected in self.provider["tts"].tts_languages and sensitive
            )
        elif not self.voice_loading and not self.provider["tts"]:
            self.lookup_action("listen-src").props.enabled = sensitive  # type: ignore

    def on_dest_text_changed(self, buffer: Gtk.TextBuffer):
        if not self.provider["trans"]:
            return

        sensitive = buffer.get_char_count() != 0
        self.lookup_action("copy").props.enabled = sensitive  # type: ignore
        self.lookup_action("suggest").set_enabled(  # type: ignore
            ProviderFeature.SUGGESTIONS in self.provider["trans"].features and sensitive
        )
        if not self.voice_loading and self.provider["tts"]:
            self.lookup_action("listen-dest").set_enabled(  # type: ignore
                self.dest_lang_selector.selected in self.provider["tts"].tts_languages and sensitive
            )
        elif not self.voice_loading and self.provider["tts"] is not None and not self.provider["tts"].tts_languages:
            self.lookup_action("listen-dest").props.enabled = sensitive  # type: ignore

    def user_action_ended(self, _buffer):
        if Settings.get().live_translation:
            self.translation()

    # The history part
    def reset_return_forward_btns(self):
        self.lookup_action("back").props.enabled = self.current_history < len(self.provider["trans"].history) - 1  # type: ignore
        self.lookup_action("forward").props.enabled = self.current_history > 0  # type: ignore

    # Retrieve translation history
    def history_update(self):
        if not self.provider["trans"]:
            return

        self.reset_return_forward_btns()
        translation = self.provider["trans"].history[self.current_history]
        self.src_lang_selector.selected = translation.original[1]
        self.dest_lang_selector.selected = translation.original[2]
        self.src_buffer.props.text = translation.original[0]
        self.dest_buffer.props.text = translation.text

    def appeared_before(self):
        if not self.provider["trans"]:
            return

        src_language = self.src_lang_selector.selected
        dest_language = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        if (
            len(self.provider["trans"].history) >= self.current_history + 1
            and (self.provider["trans"].history[self.current_history].original[1] == src_language or "auto")
            and self.provider["trans"].history[self.current_history].original[2] == dest_language
            and self.provider["trans"].history[self.current_history].original[0] == src_text
        ):
            return True
        return False

    @Gtk.Template.Callback()
    def translation(self, _action=None, _param=None):
        if not self.provider["trans"]:
            return

        # If it's like the last translation then it's useless to continue
        if not self.appeared_before():
            src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
            src_language = self.src_lang_selector.selected
            dest_language = self.dest_lang_selector.selected

            if self.ongoing_trans:
                self.next_trans = {"text": src_text, "src": src_language, "dest": dest_language}
                return

            if self.next_trans:
                src_text = self.next_trans["text"]
                src_language = self.next_trans["src"]
                dest_language = self.next_trans["dest"]
                self.next_trans = {}

            # Show feedback for start of translation.
            self.translation_loading()

            # If the two languages are the same, nothing is done
            if src_language != dest_language:
                if src_text != "":
                    self.ongoing_trans = True

                    src, dest = self.provider["trans"].denormalize_lang(src_language, dest_language)
                    self.provider["trans"].translate(
                        src_text, src, dest, self.on_translation_success, self.on_translation_fail
                    )
                else:
                    self.trans_mistakes = (None, None)
                    self.trans_src_pron = None
                    self.trans_dest_pron = None
                    self.dest_buffer.props.text = ""

                    if not self.ongoing_trans:
                        self.translation_finish()

    def on_translation_success(self, translation: Translation):
        if not self.provider["trans"]:
            return

        self.trans_warning.props.visible = False

        if translation.detected and self.src_lang_selector.selected == "auto":
            if Settings.get().src_auto:
                self.src_lang_selector.set_insight(self.provider["trans"].normalize_lang_code(translation.detected))
            else:
                self.src_lang_selector.selected = translation.detected

        self.dest_buffer.props.text = translation.text

        self.trans_mistakes = translation.mistakes
        self.trans_src_pron = translation.pronunciation[0]
        self.trans_dest_pron = translation.pronunciation[1]

        # Finally, translation is saved in history
        self.add_history_entry(translation)

        # Mistakes
        if ProviderFeature.MISTAKES in self.provider["trans"].features and not self.trans_mistakes == (None, None):
            self.mistakes_label.set_markup(_("Did you mean: ") + f'<a href="#">{self.trans_mistakes[0]}</a>')
            self.mistakes.props.reveal_child = True
        elif self.mistakes.props.reveal_child:
            self.mistakes.props.reveal_child = False

        # Pronunciation
        reveal = Settings.get().show_pronunciation
        if ProviderFeature.PRONUNCIATION in self.provider["trans"].features:
            if self.trans_src_pron is not None and self.trans_mistakes == (None, None):
                self.src_pron_label.props.label = self.trans_src_pron
                self.src_pron_revealer.props.reveal_child = reveal
            elif self.src_pron_revealer.props.reveal_child:
                self.src_pron_revealer.props.reveal_child = False

            if self.trans_dest_pron is not None:
                self.dest_pron_label.props.label = self.trans_dest_pron
                self.dest_pron_revealer.props.reveal_child = reveal
            elif self.dest_pron_revealer.props.reveal_child:
                self.dest_pron_revealer.props.reveal_child = False

        self.ongoing_trans = False
        if self.next_trans:
            self.translation()
        else:
            self.translation_finish()

    def on_translation_fail(self, error: ProviderError):
        if not self.next_trans:
            self.translation_finish()

        self.trans_warning.props.visible = True
        self.lookup_action("copy").props.enabled = False  # type: ignore
        self.lookup_action("listen-src").props.enabled = False  # type: ignore
        self.lookup_action("listen-dest").props.enabled = False  # type: ignore

        match error.code:
            case ProviderErrorCode.NETWORK:
                self.send_notification(
                    _("Translation failed, check for network issues"),
                    action={
                        "label": _("Retry"),
                        "name": "win.translation",
                    },
                )
            case ProviderErrorCode.API_KEY_INVALID:
                self.send_notification(
                    _("The provided API key is invalid"),
                    action={
                        "label": _("Retry"),
                        "name": "win.translation",
                    },
                )
            case ProviderErrorCode.API_KEY_REQUIRED:
                self.send_notification(
                    _("API key is required to use the service"),
                    action={
                        "label": _("Preferences"),
                        "name": "app.preferences",
                    },
                )
            case _:
                self.send_notification(
                    _("Translation failed"),
                    action={
                        "label": _("Retry"),
                        "name": "win.translation",
                    },
                )

    def translation_loading(self):
        self.trans_spinner.show()
        self.dest_box.props.sensitive = False
        self.langs_button_box.props.sensitive = False

    def translation_finish(self):
        self.trans_spinner.hide()
        self.dest_box.props.sensitive = True
        self.langs_button_box.props.sensitive = True

    def reload_translator(self):
        self.translator_loading = True

        # Load translator
        self.load_translator()

    def _on_active_provider_changed(self, _settings: Gio.Settings, _provider: str, kind: str):
        self.save_settings()
        match kind:
            case "trans":
                self.reload_translator()
            case "tts":
                self.load_tts()

    def _on_provider_changed(self, _settings: Gio.Settings, _key: str, name: str):
        if not self.translator_loading:
            if self.provider["trans"] and name == self.provider["trans"].name:
                self.reload_translator()

            if self.provider["tts"] and name == self.provider["tts"].name:
                self.load_tts()
