# Copyright 2020 gi-lom
# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# Copyright 2023 Libretto
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import random

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gst, Gtk

from dialect.define import APP_ID, PROFILE, RES_PATH, TRANS_NUMBER
from dialect.languages import LanguagesListModel
from dialect.providers import TRANSLATORS, TTS, ProviderFeature, ProviderError, ProviderErrorCode
from dialect.providers.base import BaseProvider, Translation
from dialect.settings import Settings
from dialect.shortcuts import DialectShortcutsWindow
from dialect.widgets import LangSelector, TextView, ThemeSwitcher


@Gtk.Template(resource_path=f'{RES_PATH}/window.ui')
class DialectWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'DialectWindow'

    # Properties
    translator_loading = GObject.Property(type=bool, default=True)

    # Child widgets
    menu_btn: Gtk.MenuButton = Gtk.Template.Child()
    main_stack: Gtk.Stack = Gtk.Template.Child()
    error_page: Adw.StatusPage = Gtk.Template.Child()
    translator_box: Gtk.Box = Gtk.Template.Child()
    key_page: Adw.StatusPage = Gtk.Template.Child()
    rmv_key_btn: Gtk.Button = Gtk.Template.Child()
    error_api_key_btn: Gtk.Button = Gtk.Template.Child()

    title_stack: Gtk.Stack = Gtk.Template.Child()
    langs_button_box: Gtk.Box = Gtk.Template.Child()
    switch_btn: Gtk.Button = Gtk.Template.Child()
    src_lang_selector: LangSelector = Gtk.Template.Child()
    dest_lang_selector: LangSelector = Gtk.Template.Child()

    return_btn: Gtk.Button = Gtk.Template.Child()
    forward_btn: Gtk.Button = Gtk.Template.Child()

    src_pron_revealer: Gtk.Revealer = Gtk.Template.Child()
    src_pron_label: Gtk.Label = Gtk.Template.Child()
    mistakes: Gtk.Revealer = Gtk.Template.Child()
    mistakes_label: Gtk.Label = Gtk.Template.Child()
    char_counter: Gtk.Label = Gtk.Template.Child()
    src_text: TextView = Gtk.Template.Child()
    clear_btn: Gtk.Button = Gtk.Template.Child()
    paste_btn: Gtk.Button = Gtk.Template.Child()
    src_voice_btn: Gtk.Button = Gtk.Template.Child()
    translate_btn: Gtk.Button = Gtk.Template.Child()

    dest_box: Gtk.Box = Gtk.Template.Child()
    dest_pron_revealer: Gtk.Revealer = Gtk.Template.Child()
    dest_pron_label: Gtk.Label = Gtk.Template.Child()
    dest_text: TextView = Gtk.Template.Child()
    dest_toolbar_stack: Gtk.Stack = Gtk.Template.Child()
    trans_spinner: Gtk.Spinner = Gtk.Template.Child()
    trans_warning: Gtk.Image = Gtk.Template.Child()
    edit_btn: Gtk.Button = Gtk.Template.Child()
    copy_btn: Gtk.Button = Gtk.Template.Child()
    dest_voice_btn: Gtk.Button = Gtk.Template.Child()

    actionbar: Gtk.ActionBar = Gtk.Template.Child()
    src_lang_selector_m: LangSelector = Gtk.Template.Child()
    dest_lang_selector_m: LangSelector = Gtk.Template.Child()

    toast: Adw.Toast | None = None  # for notification management
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()

    win_key_ctrlr: Gtk.EventControllerKey = Gtk.Template.Child()

    # Providers objects
    provider: dict[str, BaseProvider] = {
        'trans': None,
        'tts': None
    }

    # Text to speech
    current_speech = {}
    voice_loading = False  # tts loading status

    # Preset language values
    src_langs = []
    dest_langs = []

    current_history = 0  # for history management

    # Translation-related variables
    next_trans = {}  # for ongoing translation
    ongoing_trans = False  # for ongoing translation
    trans_failed = False  # for monitoring connectivity issues
    trans_mistakes = [None, None]  # "mistakes" suggestions
    # Pronunciations
    trans_src_pron = None
    trans_dest_pron = None
    # Suggestions
    before_suggest = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Application object
        self.app = kwargs['application']

        # GStreamer playbin object and related setup
        self.player = Gst.ElementFactory.make('playbin', 'player')
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_gst_message)

        # Setup window
        self.setup_actions()
        self.setup()

    def setup_actions(self):
        back = Gio.SimpleAction.new('back', None)
        back.props.enabled = False
        back.connect('activate', self.ui_return)
        self.add_action(back)

        forward_action = Gio.SimpleAction.new('forward', None)
        forward_action.props.enabled = False
        forward_action.connect('activate', self.ui_forward)
        self.add_action(forward_action)

        switch_action = Gio.SimpleAction.new('switch', None)
        switch_action.connect('activate', self.ui_switch)
        self.add_action(switch_action)

        from_action = Gio.SimpleAction.new('from', None)
        from_action.connect('activate', self.ui_from)
        self.add_action(from_action)

        to_action = Gio.SimpleAction.new('to', None)
        to_action.connect('activate', self.ui_to)
        self.add_action(to_action)

        clear_action = Gio.SimpleAction.new('clear', None)
        clear_action.props.enabled = False
        clear_action.connect('activate', self.ui_clear)
        self.add_action(clear_action)

        font_size_inc_action = Gio.SimpleAction.new('font-size-inc', None)
        font_size_inc_action.connect('activate', self.ui_font_size_inc)
        self.add_action(font_size_inc_action)

        font_size_dec_action = Gio.SimpleAction.new('font-size-dec', None)
        font_size_dec_action.connect('activate', self.ui_font_size_dec)
        self.add_action(font_size_dec_action)

        paste_action = Gio.SimpleAction.new('paste', None)
        paste_action.connect('activate', self.ui_paste)
        self.add_action(paste_action)

        copy_action = Gio.SimpleAction.new('copy', None)
        copy_action.props.enabled = False
        copy_action.connect('activate', self.ui_copy)
        self.add_action(copy_action)

        listen_dest_action = Gio.SimpleAction.new('listen-dest', None)
        listen_dest_action.connect('activate', self.ui_dest_voice)
        self.add_action(listen_dest_action)

        suggest_action = Gio.SimpleAction.new('suggest', None)
        suggest_action.props.enabled = False
        suggest_action.connect('activate', self.ui_suggest)
        self.add_action(suggest_action)

        suggest_ok_action = Gio.SimpleAction.new('suggest-ok', None)
        suggest_ok_action.connect('activate', self.ui_suggest_ok)
        self.add_action(suggest_ok_action)

        suggest_cancel_action = Gio.SimpleAction.new('suggest-cancel', None)
        suggest_cancel_action.connect('activate', self.ui_suggest_cancel)
        self.add_action(suggest_cancel_action)

        listen_src_action = Gio.SimpleAction.new('listen-src', None)
        listen_src_action.connect('activate', self.ui_src_voice)
        self.add_action(listen_src_action)

        translation_action = Gio.SimpleAction.new('translation', None)
        translation_action.props.enabled = False
        translation_action.connect('activate', self.translation)
        self.add_action(translation_action)

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Set devel style
        if PROFILE == 'Devel':
            self.add_css_class('devel')

        # Theme Switcher
        theme_switcher = ThemeSwitcher()
        self.menu_btn.props.popover.add_child(theme_switcher, 'theme')

        # Save settings on close
        self.connect('unrealize', self.save_settings)

        self.setup_selectors()
        self.setup_translation()
        self.set_help_overlay(DialectShortcutsWindow())

        # Load translator
        self.load_translator()
        # Load text to speech
        self.load_tts()

        # Listen to active providers changes
        Settings.get().connect('translator-changed', self._on_active_provider_changed, 'trans')
        Settings.get().connect('tts-changed', self._on_active_provider_changed, 'tts')

        # Bind text views font size
        self.src_text.bind_property('font-size', self.dest_text, 'font-size', GObject.BindingFlags.BIDIRECTIONAL)

        # Set initial saved text view font size
        if Settings.get().custom_default_font_size:
            font_size = Settings.get().default_font_size
            self.set_font_size(font_size)

        # Set src textview mod key requirement
        self.src_text.activate_mod = not bool(Settings.get().translate_accel_value)
        Settings.get().connect(
            'changed::translate-accel',
            lambda s, _k: self.src_text.set_property('activate_mod', not bool(s.translate_accel_value))
        )

    def setup_selectors(self):
        # Languages models
        self.src_lang_model = LanguagesListModel(self._lang_names_func)
        self.src_recent_lang_model = LanguagesListModel(self._lang_names_func)
        self.dest_lang_model = LanguagesListModel(self._lang_names_func)
        self.dest_recent_lang_model = LanguagesListModel(self._lang_names_func)

        # Src lang selector
        self.src_lang_selector.bind_models(self.src_lang_model, self.src_recent_lang_model)
        self.src_lang_selector_m.bind_models(self.src_lang_model, self.src_recent_lang_model)

        # Dest lang selector
        self.dest_lang_selector.bind_models(self.dest_lang_model, self.dest_recent_lang_model)
        self.dest_lang_selector_m.bind_models(self.dest_lang_model, self.dest_recent_lang_model)

        self.langs_button_box.props.homogeneous = False

    def _lang_names_func(self, code):
        return self.provider['trans'].get_lang_name(code)

    def setup_translation(self):
        # Src buffer
        self.src_buffer = self.src_text.props.buffer
        self.src_buffer.connect('changed', self.on_src_text_changed)
        self.src_buffer.connect('end-user-action', self.user_action_ended)

        # Dest buffer
        self.dest_buffer = self.dest_text.props.buffer
        self.dest_buffer.props.text = ''
        self.dest_buffer.connect('changed', self.on_dest_text_changed)
        # Translation progress spinner
        self.trans_spinner.hide()
        self.trans_warning.hide()

        # Voice buttons prep-work
        self.src_voice_warning = Gtk.Image.new_from_icon_name('dialog-warning-symbolic')
        self.src_voice_image = Gtk.Image.new_from_icon_name('audio-speakers-symbolic')
        self.src_voice_spinner = Gtk.Spinner()  # For use while audio is running or still loading.

        self.dest_voice_warning = Gtk.Image.new_from_icon_name('dialog-warning-symbolic')
        self.dest_voice_image = Gtk.Image.new_from_icon_name('audio-speakers-symbolic')
        self.dest_voice_spinner = Gtk.Spinner()

        self.toggle_voice_spinner(True)

    def load_translator(self):
        def on_done():
            # Mistakes support
            if ProviderFeature.MISTAKES not in self.provider['trans'].features:
                self.mistakes.props.reveal_child = False

            # Suggestions support
            self.ui_suggest_cancel(None, None)
            if ProviderFeature.SUGGESTIONS not in self.provider['trans'].features:
                self.edit_btn.props.visible = False
            else:
                self.edit_btn.props.visible = True

            # Pronunciation support
            if ProviderFeature.PRONUNCIATION not in self.provider['trans'].features:
                self.src_pron_revealer.props.reveal_child = False
                self.dest_pron_revealer.props.reveal_child = False
                self.app.lookup_action('pronunciation').props.enabled = False
            else:
                self.app.lookup_action('pronunciation').props.enabled = True

            # Update langs
            self.src_lang_model.set_langs(self.provider['trans'].languages)
            self.dest_lang_model.set_langs(self.provider['trans'].languages)

            # Update selected langs
            set_auto = Settings.get().src_auto and ProviderFeature.DETECTION in self.provider['trans'].features
            src_lang = self.provider['trans'].languages[0]
            if self.src_langs and self.src_langs[0] in self.provider['trans'].languages:
                src_lang = self.src_langs[0]
            self.src_lang_selector.selected = 'auto' if set_auto else src_lang

            dest_lang = self.provider['trans'].languages[1]
            if self.dest_langs and self.dest_langs[0] in self.provider['trans'].languages:
                dest_lang = self.dest_langs[0]
            self.dest_lang_selector.selected = dest_lang

            # Update chars limit
            if self.provider['trans'].chars_limit == -1:  # -1 means unlimited
                self.char_counter.props.label = ''
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
        self.main_stack.props.visible_child_name = 'loading'

        # Translator object
        self.provider['trans'] = TRANSLATORS[provider]()
        # Get saved languages
        self.src_langs = self.provider['trans'].src_langs
        self.dest_langs = self.provider['trans'].dest_langs
        # Do provider init
        self.provider['trans'].init_trans(on_done, on_fail)

        # Connect to provider settings changes
        self.provider['trans'].settings.connect(
            'changed::instance-url', self._on_provider_changed, self.provider['trans'].name
        )
        self.provider['trans'].settings.connect(
            'changed::api-key', self._on_provider_changed, self.provider['trans'].name
        )

    def check_apikey(self):
        def on_done(valid):
            if valid:
                self.main_stack.props.visible_child_name = 'translate'
            else:
                self.key_page.props.title = _('The provided API key is invalid')
                if ProviderFeature.API_KEY_REQUIRED in self.provider['trans'].features:
                    self.key_page.props.description = _('Please set a valid API key in the preferences.')
                else:
                    self.key_page.props.description = _(
                        'Please set a valid API key or unset the API key in the preferences.'
                    )
                    self.rmv_key_btn.props.visible = True
                    self.error_api_key_btn.props.visible = True
                self.main_stack.props.visible_child_name = 'api-key'

        def on_fail(error: ProviderError):
            self.loading_failed(error)

        if ProviderFeature.API_KEY in self.provider['trans'].features:
            if self.provider['trans'].api_key:
                self.provider['trans'].validate_api_key(self.provider['trans'].api_key, on_done, on_fail)
            elif (
                not self.provider['trans'].api_key
                and ProviderFeature.API_KEY_REQUIRED in self.provider['trans'].features
            ):
                self.key_page.props.title = _('API key is required to use the service')
                self.key_page.props.description = _('Please set an API key in the preferences.')
                self.main_stack.props.visible_child_name = 'api-key'
            else:
                self.main_stack.props.visible_child_name = 'translate'
        else:
            self.main_stack.props.visible_child_name = 'translate'

    def loading_failed(self, error: ProviderError):
        self.main_stack.props.visible_child_name = 'error'

        service = self.provider['trans'].prettyname
        url = self.provider['trans'].instance_url

        title = _('Failed loading the translation service')
        description = _('Please report this in the Dialect bug tracker if the issue persists.')
        if ProviderFeature.INSTANCES in self.provider['trans'].features:
            description = _((
                'Failed loading "{url}", check if the instance address is correct or report in the Dialect bug tracker'
                ' if the issue persists.'
            ))
            description = description.format(url=url)

        if error.code == ProviderErrorCode.NETWORK:
            title = _('Couldn’t connect to the translation service')
            description = _('We can’t connect to the server. Please check for network issues.')
            if ProviderFeature.INSTANCES in self.provider['trans'].features:
                description = _((
                    'We can’t connect to the {service} instance "{url}".\n'
                    'Please check for network issues or if the address is correct.'
                ))
                description = description.format(service=service, url=url)

        if error.message:
            description = description + '\n\n<small><tt>' + error.message + '</tt></small>'

        self.error_page.props.title = title
        self.error_page.props.description = description

    @Gtk.Template.Callback()
    def retry_load_translator(self, _button):
        self.load_translator()

    @Gtk.Template.Callback()
    def remove_key_and_reload(self, _button):
        self.provider['trans'].reset_api_key()
        self.load_translator()

    def load_tts(self):
        def on_done():
            self.download_speech()

        def on_fail(_error: ProviderError):
            self.on_listen_failed()

        # TTS name
        provider = Settings.get().active_tts

        # Check if TTS is disabled
        if provider != '':
            self.src_voice_btn.props.visible = True
            self.dest_voice_btn.props.visible = True

            # TTS Object
            self.provider['tts'] = TTS[provider]()
            self.provider['tts'].init_tts(on_done, on_fail)

            # Connect to provider settings changes
            self.provider['tts'].settings.connect(
                'changed::instance-url', self._on_provider_changed, self.provider['tts'].name
            )
            self.provider['tts'].settings.connect(
                'changed::api-key', self._on_provider_changed, self.provider['tts'].name
            )
        else:
            self.provider['tts'] = None
            self.src_voice_btn.props.visible = False
            self.dest_voice_btn.props.visible = False

    def on_listen_failed(self):
        self.src_voice_btn.props.child = self.src_voice_warning
        self.src_voice_spinner.stop()

        self.dest_voice_btn.props.child = self.dest_voice_warning
        self.dest_voice_spinner.stop()

        tooltip_text = _('A network issue has occurred. Retry?')
        self.src_voice_btn.props.tooltip_text = tooltip_text
        self.dest_voice_btn.props.tooltip_text = tooltip_text

        if self.current_speech:
            called_from = self.current_speech['called_from']
            action = {
                'label': _('Retry'),
                'name': 'win.listen-src' if called_from == 'src' else 'win.listen-dest',
            }
        else:
            action = None

        self.send_notification(
            _('A network issue has occurred. Please try again.'),
            action=action
        )

        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )

        if self.provider['tts'].tts_languages:
            self.lookup_action('listen-src').set_enabled(
                self.src_lang_selector.selected in self.provider['tts'].tts_languages
                and src_text != ''
            )
            self.lookup_action('listen-dest').set_enabled(
                self.dest_lang_selector.selected in self.provider['tts'].tts_languages
                and dest_text != ''
            )
        else:
            self.lookup_action('listen-src').props.enabled = src_text != ''
            self.lookup_action('listen-dest').props.enabled = dest_text != ''

    def translate(self, text, src_lang, dest_lang):
        """
        Translates the given text from auto detected language to last used
        language
        """
        # Set src lang to Auto
        if src_lang is None:
            self.src_lang_selector.selected = 'auto'
        else:
            self.src_lang_selector.selected = src_lang
        if dest_lang is not None and dest_lang in self.provider['trans'].languages:
            self.dest_lang_selector.selected = dest_lang
            self.dest_lang_selector.emit('user-selection-changed')
        # Set text to src buffer
        self.src_buffer.props.text = text
        # Run translation
        self.translation()

    def translate_selection(self, src_lang, dest_lang):
        def on_paste(clipboard, result):
            text = clipboard.read_text_finish(result)
            self.translate(text, src_lang, dest_lang)
        
        clipboard = Gdk.Display.get_default().get_primary_clipboard()
        clipboard.read_text_async(None, on_paste)

    def save_settings(self, *args, **kwargs):
        if not self.is_maximized():
            size = self.get_default_size()
            Settings.get().window_size = (size.width, size.height)
        if self.provider['trans'] is not None:
            self.provider['trans'].src_langs = self.src_langs
            self.provider['trans'].dest_langs = self.dest_langs

    def send_notification(self, text, queue=False, action=None, timeout=5, priority=Adw.ToastPriority.NORMAL):
        """
        Display an in-app notification.

        Args:
            text (str): The text or message of the notification.
            queue (bool, optional): If True, the notification will be queued.
            action (dict, optional): A dict containing the action to be called.
        """
        if not queue and self.toast is not None:
            self.toast.dismiss()
        self.toast = Adw.Toast.new(text)
        self.toast.connect('dismissed', self._toast_dismissed)
        if action is not None:
            self.toast.props.button_label = action['label']
            self.toast.props.action_name = action['name']
        self.toast.props.timeout = timeout
        self.toast.props.priority = priority
        self.toast_overlay.add_toast(self.toast)

    def _toast_dismissed(self, toast):
        self.toast = None

    def toggle_voice_spinner(self, active=True):
        if active:
            self.lookup_action('listen-src').props.enabled = False
            self.src_voice_btn.props.child = self.src_voice_spinner
            self.src_voice_spinner.start()

            self.lookup_action('listen-dest').props.enabled = False
            self.dest_voice_btn.props.child = self.dest_voice_spinner
            self.dest_voice_spinner.start()
        else:
            src_text = self.src_buffer.get_text(
                self.src_buffer.get_start_iter(),
                self.src_buffer.get_end_iter(),
                True
            )
            self.lookup_action('listen-src').set_enabled(
                self.src_lang_selector.selected in self.provider['tts'].tts_languages
                and src_text != ''
            )
            self.src_voice_btn.props.child = self.src_voice_image
            self.src_voice_spinner.stop()

            dest_text = self.dest_buffer.get_text(
                self.dest_buffer.get_start_iter(),
                self.dest_buffer.get_end_iter(),
                True
            )
            self.lookup_action('listen-dest').set_enabled(
                self.dest_lang_selector.selected in self.provider['tts'].tts_languages
                and dest_text != ''
            )
            self.dest_voice_btn.props.child = self.dest_voice_image
            self.dest_voice_spinner.stop()

    @Gtk.Template.Callback()
    def _on_src_lang_changed(self, _obj, _param):
        """ Called on self.src_lang_selector::notify::selected signal """

        code = self.src_lang_selector.selected
        dest_code = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )

        if self.provider['trans'].cmp_langs(code, dest_code):
            if len(self.dest_langs) >= 2:
                code = self.dest_langs[1] if code == self.src_langs[0] else dest_code
            if self.src_langs:
                self.dest_lang_selector.selected = self.src_langs[0]
            else:
                options = list(self.provider['trans'].languages)
                options.remove(code)
                self.dest_lang_selector.selected = random.choice(options)

        # Disable or enable listen function.
        if self.provider['tts'] and Settings.get().active_tts != '':
            self.lookup_action('listen-src').set_enabled(
                code in self.provider['tts'].tts_languages and src_text != ''
            )

        # Disable or enable switch function.
        self.lookup_action('switch').props.enabled = code != 'auto'

        if code in self.provider['trans'].languages:
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

    @Gtk.Template.Callback()
    def _on_dest_lang_changed(self, _obj, _param):
        """ Called on self.dest_lang_selector::notify::selected signal """

        code = self.dest_lang_selector.selected
        src_code = self.src_lang_selector.selected
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )

        if self.provider['trans'].cmp_langs(code, src_code):
            self.src_lang_selector.selected = self.dest_langs[0]

        # Disable or enable listen function.
        if self.provider['tts'] and Settings.get().active_tts != '':
            self.lookup_action('listen-dest').set_enabled(
                code in self.provider['tts'].tts_languages and dest_text != ''
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
        if self.current_history > 0:
            del self.provider['trans'].history[: self.current_history]
            self.current_history = 0
        if len(self.provider['trans'].history) == TRANS_NUMBER:
            self.provider['trans'].history.pop()
        self.provider['trans'].history.insert(0, translation)
        GLib.idle_add(self.reset_return_forward_btns)

    def switch_all(self, src_language, dest_language, src_text, dest_text):
        self.src_lang_selector.selected = dest_language
        self.dest_lang_selector.selected = src_language
        self.src_buffer.props.text = dest_text
        self.dest_buffer.props.text = src_text
        self.add_history_entry(Translation(src_text, (dest_text, src_language, dest_language)))

        # Re-enable widgets
        self.langs_button_box.props.sensitive = True
        self.lookup_action('translation').props.enabled = self.src_buffer.get_char_count() != 0

    def ui_switch(self, _action, _param):
        # Get variables
        self.langs_button_box.props.sensitive = False
        self.lookup_action('translation').props.enabled = False
        src_language = self.src_lang_selector.selected
        dest_language = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        if src_language == 'auto':
            return

        # Switch all
        self.switch_all(src_language, dest_language, src_text, dest_text)

    def ui_from(self, _action, _param):
        self.src_lang_selector.button.popup()

    def ui_to(self, _action, _param):
        self.dest_lang_selector.button.popup()

    def ui_clear(self, _action, _param):
        self.src_buffer.props.text = ''
        self.src_buffer.emit('end-user-action')

    def set_font_size(self, size):
        self.src_text.font_size = size

    def ui_font_size_inc(self, _action, _param):
        self.src_text.font_size_inc()

    def ui_font_size_dec(self, _action, _param):
        self.src_text.font_size_dec()

    def ui_copy(self, _action, _param):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(dest_text)

    def ui_paste(self, _action, _param):
        clipboard = Gdk.Display.get_default().get_clipboard()

        def on_paste(_clipboard, result):
            text = clipboard.read_text_finish(result)
            if text is not None:
                end_iter = self.src_buffer.get_end_iter()
                self.src_buffer.insert(end_iter, text)
                self.src_buffer.emit('end-user-action')

        cancellable = Gio.Cancellable()
        clipboard.read_text_async(cancellable, on_paste)

    def ui_suggest(self, _action, _param):
        self.dest_toolbar_stack.props.visible_child_name = 'edit'
        self.before_suggest = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        self.dest_text.props.editable = True

    def ui_suggest_ok(self, _action, _param):
        def on_done(success):
            self.dest_toolbar_stack.props.visible_child_name = 'default'

            if success:
                self.send_notification(_('New translation has been suggested!'))
            else:
                self.send_notification(_('Suggestion failed.'))

            self.dest_text.props.editable = False

        def on_fail(error: ProviderError):
            self.dest_toolbar_stack.props.visible_child_name = 'default'
            self.send_notification(_('Suggestion failed.'))
            self.dest_text.props.editable = False

        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )

        src, dest = self.provider['trans'].denormalize_lang(
            self.provider['trans'].history[self.current_history].original[1],
            self.provider['trans'].history[self.current_history].original[2]
        )

        self.provider['trans'].suggest(
            self.provider['trans'].history[self.current_history].original[0],
            src,
            dest,
            dest_text,
            on_done,
            on_fail
        )

        self.before_suggest = None

    def ui_suggest_cancel(self, _action, _param):
        self.dest_toolbar_stack.props.visible_child_name = 'default'
        if self.before_suggest is not None:
            self.dest_buffer.props.text = self.before_suggest
            self.before_suggest = None
        self.dest_text.props.editable = False       

    def ui_src_voice(self, _action, _param):
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        src_language = self.src_lang_selector.selected
        self._pre_speech(src_text, src_language, 'src')

    def ui_dest_voice(self, _action, _param):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        dest_language = self.dest_lang_selector.selected
        self._pre_speech(dest_text, dest_language, 'dest')

    def _pre_speech(self, text, lang, called_from):
        if text != '':
            self.voice_loading = True
            self.toggle_voice_spinner(True)

            self.current_speech = {
                'text': text,
                'lang': lang,
                'called_from': called_from
            }

            self.download_speech()

    def on_gst_message(self, _bus, message):
        if message.type == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
        elif message.type == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            logging.error('Some error occurred while trying to play.')

    def download_speech(self):
        def on_done(file):
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
                self.current_speech = {}

        def on_fail(_error: ProviderError):
            self.on_listen_failed()
            self.toggle_voice_spinner(False)

        if self.current_speech:
            lang = self.provider['tts'].denormalize_lang(self.current_speech['lang'])
            self.provider['tts'].speech(self.current_speech['text'], lang, on_done, on_fail)
        else:
            self.toggle_voice_spinner(False)
            self.voice_loading = False

    def _play_audio(self, path):
        uri = 'file://' + path
        self.player.set_property('uri', uri)
        self.player.set_state(Gst.State.PLAYING)

    @Gtk.Template.Callback()
    def _on_key_event(self, _button, keyval, _keycode, state):
        """ Called on self.win_key_ctrlr::key-pressed signal """
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyval)
        if (GLib.unichar_isgraph(chr(unicode_key_val))
                and modifiers in (shift_mask, 0)
                and not self.dest_text.props.editable
                and not self.src_text.is_focus()):
            self.src_text.grab_focus()
            end_iter = self.src_buffer.get_end_iter()
            self.src_buffer.insert(end_iter, chr(unicode_key_val))
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    @Gtk.Template.Callback()
    def _on_src_activated(self, _texview):
        """ Called on self.src_text::active signal """
        if not Settings.get().live_translation:
            self.translation()

    @Gtk.Template.Callback()
    def _on_mistakes_clicked(self, _button, _data):
        """ Called on self.mistakes_label::activate-link signal """
        self.mistakes.props.reveal_child = False
        self.src_buffer.props.text = self.trans_mistakes[1]
        # Run translation again
        self.translation()

        return Gdk.EVENT_STOP

    def on_src_text_changed(self, buffer):
        char_count = buffer.get_char_count()

        # If the text is over the highest number of characters allowed, it is truncated.
        # This is done for avoiding exceeding the limit imposed by translation services.
        if self.provider['trans'].chars_limit == -1:  # -1 means unlimited
            self.char_counter.props.label = ''
        else:
            self.char_counter.props.label = f'{str(char_count)}/{self.provider["trans"].chars_limit}'

            if char_count >= self.provider['trans'].chars_limit:
                self.send_notification(_('{} characters limit reached!').format(self.provider['trans'].chars_limit))
                buffer.delete(
                    buffer.get_iter_at_offset(self.provider['trans'].chars_limit),
                    buffer.get_end_iter()
                )

        sensitive = char_count != 0
        self.lookup_action('translation').props.enabled = sensitive
        self.lookup_action('clear').props.enabled = sensitive
        if not self.voice_loading and self.provider['tts']:
            self.lookup_action('listen-src').set_enabled(
                self.src_lang_selector.selected in self.provider['tts'].tts_languages
                and sensitive
            )
        elif not self.voice_loading and not self.provider['tts']:
            self.lookup_action('listen-src').props.enabled = sensitive

    def on_dest_text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.lookup_action('copy').props.enabled = sensitive
        self.lookup_action('suggest').set_enabled(
            ProviderFeature.SUGGESTIONS in self.provider['trans'].features
            and sensitive
        )
        if not self.voice_loading and self.provider['tts']:
            self.lookup_action('listen-dest').set_enabled(
                self.dest_lang_selector.selected in self.provider['tts'].tts_languages
                and sensitive
            )
        elif not self.voice_loading and self.provider['tts'] is not None and not self.provider['tts'].tts_languages:
            self.lookup_action('listen-dest').props.enabled = sensitive

    def user_action_ended(self, _buffer):
        if Settings.get().live_translation:
            self.translation()

    # The history part
    def reset_return_forward_btns(self):
        self.lookup_action('back').props.enabled = self.current_history < len(self.provider['trans'].history) - 1
        self.lookup_action('forward').props.enabled = self.current_history > 0

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_btns()
        translation = self.provider['trans'].history[self.current_history]
        self.src_lang_selector.selected = translation.original[1]
        self.dest_lang_selector.selected = translation.original[2]
        self.src_buffer.props.text = translation.original[0]
        self.dest_buffer.props.text = translation.text

    def appeared_before(self):
        src_language = self.src_lang_selector.selected
        dest_language = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        if (
            len(self.provider['trans'].history) >= self.current_history + 1
            and (self.provider['trans'].history[self.current_history].original[1] == src_language or 'auto')
            and self.provider['trans'].history[self.current_history].original[2] == dest_language
            and self.provider['trans'].history[self.current_history].original[0] == src_text
        ):
            return True
        return False

    @Gtk.Template.Callback()
    def translation(self, _action=None, _param=None):
        # If it's like the last translation then it's useless to continue
        if not self.appeared_before():
            src_text = self.src_buffer.get_text(
                self.src_buffer.get_start_iter(),
                self.src_buffer.get_end_iter(),
                True
            )
            src_language = self.src_lang_selector.selected
            dest_language = self.dest_lang_selector.selected

            if self.ongoing_trans:
                self.next_trans = {
                    'text': src_text,
                    'src': src_language,
                    'dest': dest_language
                }
                return

            if self.next_trans:
                src_text = self.next_trans['text']
                src_language = self.next_trans['src']
                dest_language = self.next_trans['dest']
                self.next_trans = {}

            # Show feedback for start of translation.
            self.translation_loading()

            # If the two languages are the same, nothing is done
            if src_language != dest_language:
                if src_text != '':
                    self.ongoing_trans = True

                    src, dest = self.provider['trans'].denormalize_lang(src_language, dest_language)
                    self.provider['trans'].translate(
                        src_text,
                        src,
                        dest,
                        self.on_translation_success,
                        self.on_translation_fail
                    )
                else:
                    self.trans_mistakes = (None, None)
                    self.trans_src_pron = None
                    self.trans_dest_pron = None
                    self.dest_buffer.props.text = ''

                    if not self.ongoing_trans:
                        self.translation_finish()

    def on_translation_success(self, translation: Translation):
        self.trans_warning.props.visible = False

        if translation.detected and self.src_lang_selector.selected == 'auto':
            if Settings.get().src_auto:
                self.src_lang_selector.set_insight(translation.detected)
            else:
                self.src_lang_selector.selected = translation.detected

        self.dest_buffer.props.text = translation.text

        self.trans_mistakes = translation.mistakes
        self.trans_src_pron = translation.pronunciation[0]
        self.trans_dest_pron = translation.pronunciation[1]

        # Finally, translation is saved in history
        self.add_history_entry(translation)

        # Mistakes
        if ProviderFeature.MISTAKES in self.provider['trans'].features and not self.trans_mistakes == (None, None):
            self.mistakes_label.set_markup(_('Did you mean: ') + f'<a href="#">{self.trans_mistakes[0]}</a>')
            self.mistakes.props.reveal_child = True
        elif self.mistakes.props.reveal_child:
            self.mistakes.props.reveal_child = False

        # Pronunciation
        reveal = Settings.get().show_pronunciation
        if ProviderFeature.PRONUNCIATION in self.provider['trans'].features:
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
        self.lookup_action('copy').props.enabled = False
        self.lookup_action('listen-src').props.enabled = False
        self.lookup_action('listen-dest').props.enabled = False

        match error.code:
            case ProviderErrorCode.NETWORK:
                self.send_notification(
                    _('Translation failed, check for network issues'),
                    action={
                        'label': _('Retry'),
                        'name': 'win.translation',
                    }
                )
            case ProviderErrorCode.API_KEY_INVALID:
                self.send_notification(
                    _('Translation failed, check for network issues'),
                    action={
                        'label': _('Retry'),
                        'name': 'win.translation',
                    }
                )
            case ProviderErrorCode.API_KEY_REQUIRED:
                self.send_notification(
                    _('API key is required to use the service'),
                    action={
                        'label': _('Preferences'),
                        'name': 'app.preferences',
                    }
                )
            case _:
                self.send_notification(
                    _('Translation failed'),
                    action={
                        'label': _('Retry'),
                        'name': 'win.translation',
                    }
                )            

    def translation_loading(self):
        self.trans_spinner.show()
        self.trans_spinner.start()
        self.dest_box.props.sensitive = False
        self.langs_button_box.props.sensitive = False

    def translation_finish(self):
        self.trans_spinner.stop()
        self.trans_spinner.hide()
        self.dest_box.props.sensitive = True
        self.langs_button_box.props.sensitive = True

    def reload_translator(self):
        self.translator_loading = True

        # Load translator
        self.load_translator()

    def _on_active_provider_changed(self, _settings, _provider, kind):
        self.save_settings()
        match kind:
            case 'trans':
                self.reload_translator()
            case 'tts':
                self.load_tts()

    def _on_provider_changed(self, _settings, _key, name):
        if not self.translator_loading:
            if name == self.provider['trans'].name:
                self.reload_translator()

            if name == self.provider['tts'].name:
                self.load_tts()
