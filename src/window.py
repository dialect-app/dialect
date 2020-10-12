# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
from tempfile import NamedTemporaryFile

from gi.repository import Gdk, Gio, GLib, Gtk, Gst, Handy

from googletrans import LANGUAGES, Translator
from gtts import gTTS, lang

from dialect.define import APP_ID, RES_PATH, MAX_LENGTH, TRANS_NUMBER
from dialect.lang_selector import DialectLangSelector


@Gtk.Template(resource_path=f'{RES_PATH}/window.ui')
class DialectWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'DialectWindow'

    # Get widgets
    main_stack = Gtk.Template.Child()
    translator_box = Gtk.Template.Child()

    title_stack = Gtk.Template.Child()
    langs_button_box = Gtk.Template.Child()
    switch_btn = Gtk.Template.Child()
    src_lang_btn = Gtk.Template.Child()
    src_lang_label = Gtk.Template.Child()
    dest_lang_btn = Gtk.Template.Child()
    dest_lang_label = Gtk.Template.Child()

    return_btn = Gtk.Template.Child()
    forward_btn = Gtk.Template.Child()

    menu_btn = Gtk.Template.Child()

    src_text = Gtk.Template.Child()
    clear_btn = Gtk.Template.Child()
    paste_btn = Gtk.Template.Child()
    translate_btn = Gtk.Template.Child()

    dest_box = Gtk.Template.Child()
    dest_text = Gtk.Template.Child()
    trans_spinner = Gtk.Template.Child()
    trans_warning = Gtk.Template.Child()
    copy_btn = Gtk.Template.Child()
    voice_btn = Gtk.Template.Child()

    actionbar = Gtk.Template.Child()
    src_lang_btn2 = Gtk.Template.Child()
    switch_btn2 = Gtk.Template.Child()
    dest_lang_btn2 = Gtk.Template.Child()

    notification_revealer = Gtk.Template.Child()
    notification_label = Gtk.Template.Child()

    # Language values
    lang_codes = list(LANGUAGES.keys())
    lang_names = list(LANGUAGES.values())
    lang_speech = None
    # Current input Text
    current_input_text = ''
    current_history = 0
    history = []
    type_time = 0
    trans_queue = []
    active_thread = None
    # These are for being able to go backspace
    first_key = 0
    second_key = 0
    mobile_mode = False
    # Connectivity issues monitoring
    trans_failed = False
    voice_loading = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # GSettings object
        self.settings = Gio.Settings.new(APP_ID)
        # Get saved languages
        self.src_langs = list(self.settings.get_value('src-langs'))
        self.dest_langs = list(self.settings.get_value('dest-langs'))

        # Google Translate object
        self.translator = Translator()

        # GStreamer playbin object and related setup
        self.player = Gst.ElementFactory.make('playbin', 'player')
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_gst_message)
        self.player_event = threading.Event()  # An event for letting us know when Gst is done playing

        # Clipboard
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # This is only for the Clipboard button

        # Setup window
        self.setup()

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Load saved dark mode
        gtk_settings = Gtk.Settings.get_default()
        dark_mode = self.settings.get_boolean('dark-mode')
        gtk_settings.set_property('gtk-application-prefer-dark-theme',
                                  dark_mode)

        # Connect responsive design function
        self.connect('check-resize', self.responsive_listener)
        self.connect('destroy', self.on_destroy)

        self.setup_headerbar()
        self.setup_actionbar()
        self.setup_translation()
        self.toggle_mobile_mode()

        # Get languages available for speech
        threading.Thread(target=self.load_lang_speech).start()

        # Load saved left lang
        self.src_lang_selector.set_property('selected', self.src_langs[0])
        # Load saved right lang
        self.dest_lang_selector.set_property('selected', self.dest_langs[0])

    def on_listen_failed(self):
        self.voice_btn.set_image(self.voice_warning)
        self.voice_spinner.stop()
        self.voice_btn.set_tooltip_text('A network issue has occured. Retry?')
        self.send_notification('A network issue has occured.\nPlease try again.')
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        if self.lang_speech:
            self.voice_btn.set_sensitive(self.dest_lang_selector.get_property('selected') in self.lang_speech
                                         and dest_text != '')
        else:
            self.voice_btn.set_sensitive(dest_text != '')

    def load_lang_speech(self, listen=False, text=None, language=None):
        """
        Load the language list for gTTS.

        text and language parameters are only needed with listen parameter.
        """
        try:
            self.voice_loading = True
            self.lang_speech = list(lang.tts_langs(tld='com').keys())
            if not listen:
                GLib.idle_add(self.toggle_voice_spinner, False)
            elif language in self.lang_speech and text != '':
                self.voice_download(text, language)

        except RuntimeError as exc:
            GLib.idle_add(self.on_listen_failed)
            print('Error: ' + str(exc))
        finally:
            if not listen:
                self.voice_loading = False

    def setup_headerbar(self):
        # Connect history buttons
        self.return_btn.connect('clicked', self.ui_return)
        self.forward_btn.connect('clicked', self.ui_forward)

        # Left lang selector
        self.src_lang_selector = DialectLangSelector()
        self.src_lang_selector.connect('notify::selected',
                                        self.on_src_lang_changed)
        # Set popover selector to button
        self.src_lang_btn.set_popover(self.src_lang_selector)
        self.src_lang_selector.set_relative_to(self.src_lang_btn)

        # Right lang selector
        self.dest_lang_selector = DialectLangSelector()
        self.dest_lang_selector.connect('notify::selected',
                                         self.on_dest_lang_changed)
        # Set popover selector to button
        self.dest_lang_btn.set_popover(self.dest_lang_selector)
        self.dest_lang_selector.set_relative_to(self.dest_lang_btn)

        # Add languages to both list
        for code, name in LANGUAGES.items():
            self.src_lang_selector.insert(code, name.capitalize())
            self.dest_lang_selector.insert(code, name.capitalize())

        self.langs_button_box.set_homogeneous(False)

        # Switch button
        self.switch_btn.connect('clicked', self.ui_switch)

        # Add menu to menu button
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/menu.ui')
        menu = builder.get_object('app-menu')
        menu_popover = Gtk.Popover.new_from_model(self.menu_btn, menu)
        self.menu_btn.set_popover(menu_popover)

    def setup_actionbar(self):
        # Set popovers to lang buttons
        self.src_lang_btn2.set_popover(self.src_lang_selector)
        self.dest_lang_btn2.set_popover(self.dest_lang_selector)

        # Switch button
        self.switch_btn2.connect('clicked', self.ui_switch)

    def setup_translation(self):
        # Left buffer
        self.src_buffer = self.src_text.get_buffer()
        self.src_buffer.set_text('')
        self.src_buffer.connect('changed', self.text_changed)
        self.src_buffer.connect('end-user-action', self.user_action_ended)
        self.connect('key-press-event', self.update_trans_button)
        # Clear button
        self.clear_btn.connect('clicked', self.ui_clear)
        # Paste button
        self.paste_btn.connect('clicked', self.ui_paste)
        # Translate button
        self.translate_btn.connect('clicked', self.translation)

        # Right buffer
        self.dest_buffer = self.dest_text.get_buffer()
        self.dest_buffer.set_text('')
        # Clipboard button
        self.copy_btn.connect('clicked', self.ui_copy)
        # Translation progress spinner
        self.trans_spinner.hide()
        self.trans_warning.hide()
        # Voice button prep-work
        self.voice_warning = Gtk.Image.new_from_icon_name(
            'dialog-warning-symbolic', Gtk.IconSize.BUTTON)
        self.voice_btn.connect('clicked', self.ui_voice)
        self.voice_image = Gtk.Image.new_from_icon_name(
            'audio-speakers-symbolic', Gtk.IconSize.BUTTON)
        self.voice_spinner = Gtk.Spinner()  # For use while audio is running or still loading.
        self.toggle_voice_spinner(True)

    def responsive_listener(self, _window):
        size = self.get_size()

        if size.width < 600:
            if self.mobile_mode is False:
                self.mobile_mode = True
                self.toggle_mobile_mode()
        else:
            if self.mobile_mode is True:
                self.mobile_mode = False
                self.toggle_mobile_mode()

    def toggle_mobile_mode(self):
        if self.mobile_mode:
            # Show actionbar
            self.actionbar.set_reveal_child(True)
            # Change headerbar title
            self.title_stack.set_visible_child_name('label')
            # Change translation box orientation
            self.translator_box.set_orientation(Gtk.Orientation.VERTICAL)
            # Change lang selectors position
            self.src_lang_selector.set_relative_to(self.src_lang_btn2)
            self.dest_lang_selector.set_relative_to(self.dest_lang_btn2)
        else:
            # Hide actionbar
            self.actionbar.set_reveal_child(False)
            # Reset headerbar title
            self.title_stack.set_visible_child_name('selector')
            # Reset translation box orientation
            self.translator_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            # Reset lang selectors position
            self.src_lang_selector.set_relative_to(self.src_lang_btn)
            self.dest_lang_selector.set_relative_to(self.dest_lang_btn)

    def on_destroy(self, _window):
        self.settings.set_value('src-langs',
                                GLib.Variant('as', self.src_langs))
        self.settings.set_value('dest-langs',
                                GLib.Variant('as', self.dest_langs))

    def send_notification(self, text, timeout=5):
        """
        Display an in-app notification.

        Args:
            text (str): The text or message of the notification.
            timeout (int, optional): The time before the notification disappears. Defaults to 5.
        """
        self.notification_label.set_text(text)
        self.notification_revealer.set_reveal_child(True)

        timer = threading.Timer(
            timeout,
            GLib.idle_add,
            args=[self.notification_revealer.set_reveal_child, False]
        )
        timer.start()

    def toggle_voice_spinner(self, active=True):
        if active:
            self.voice_btn.set_sensitive(False)
            self.voice_btn.set_image(self.voice_spinner)
            self.voice_spinner.start()
        else:
            dest_text = self.dest_buffer.get_text(
                self.dest_buffer.get_start_iter(),
                self.dest_buffer.get_end_iter(),
                True
            )
            self.voice_btn.set_sensitive(self.dest_lang_selector.get_property('selected') in self.lang_speech
                                         and dest_text != '')
            self.voice_btn.set_image(self.voice_image)
            self.voice_spinner.stop()

    def on_src_lang_changed(self, _obj, _param):
        code = self.src_lang_selector.get_property('selected')

        if code in LANGUAGES:
            self.src_lang_label.set_label(LANGUAGES[code].capitalize())
            # Updated saved left langs list
            if code in self.src_langs:
                # Bring lang to the top
                index = self.src_langs.index(code)
                self.src_langs.insert(0, self.src_langs.pop(index))
            else:
                self.src_langs.pop()
                self.src_langs.insert(0, code)
        else:
            self.src_lang_label.set_label('Auto')

        # Rewrite recent langs
        self.src_lang_selector.clear_recent()
        self.src_lang_selector.insert_recent('auto', 'Auto')
        for code in self.src_langs:
            name = LANGUAGES[code].capitalize()
            self.src_lang_selector.insert_recent(code, name)

        # Refresh list
        self.src_lang_selector.refresh_selected()

    def on_dest_lang_changed(self, _obj, _param):
        code = self.dest_lang_selector.get_property('selected')
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )

        # Disable or enable listen function.
        if self.lang_speech:
            self.voice_btn.set_sensitive(code in self.lang_speech
                                         and dest_text != '')

        name = LANGUAGES[code].capitalize()
        self.dest_lang_label.set_label(name)
        # Updated saved right langs list
        if code in self.dest_langs:
            # Bring lang to the top
            index = self.dest_langs.index(code)
            self.dest_langs.insert(0, self.dest_langs.pop(index))
        else:
            self.dest_langs.pop()
            self.dest_langs.insert(0, code)

        # Rewrite recent langs
        self.dest_lang_selector.clear_recent()
        for code in self.dest_langs:
            name = LANGUAGES[code].capitalize()
            self.dest_lang_selector.insert_recent(code, name)

        # Refresh list
        self.dest_lang_selector.refresh_selected()

    """
    User interface functions
    """
    def ui_return(self, _button):
        """Go back one step in history."""
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self.history_update()

    def ui_forward(self, _button):
        """Go forward one step in history."""
        if self.current_history != 0:
            self.current_history -= 1
            self.history_update()

    def add_history_entry(self, src_language, dest_language, src_text, dest_text):
        """Add a history entry to the history list."""
        new_history_trans = {
            'Languages': [src_language, dest_language],
            'Text': [src_text, dest_text]
        }
        if self.current_history > 0:
            del self.history[:self.current_history]
            self.current_history = 0
        if len(self.history) > 0:
            self.return_btn.set_sensitive(True)
        if len(self.history) == TRANS_NUMBER:
            self.history.pop()
        self.history.insert(0, new_history_trans)
        GLib.idle_add(self.reset_return_forward_btns)

    def switch_all(self, src_language, dest_language, src_text, dest_text):
        self.src_lang_selector.set_property('selected', dest_language)
        self.dest_lang_selector.set_property('selected', src_language)
        self.src_buffer.set_text(dest_text)
        self.dest_buffer.set_text(src_text)
        self.add_history_entry(src_language, dest_language, src_text, dest_text)

        # Re-enable widgets
        self.langs_button_box.set_sensitive(True)
        self.translate_btn.set_sensitive(self.src_buffer.get_char_count() != 0)

    def switch_auto_lang(self, dest_language, src_text, dest_text):
        src_language = str(self.translator.detect(src_text).lang)

        # Switch all
        GLib.idle_add(self.switch_all, src_language, dest_language, src_text, dest_text)

    def ui_switch(self, _button):
        # Get variables
        self.langs_button_box.set_sensitive(False)
        self.translate_btn.set_sensitive(False)
        src_language = self.src_lang_selector.get_property('selected')
        dest_language = self.dest_lang_selector.get_property('selected')
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
            if src_text == '':
                src_language = self.src_langs[0]
            else:
                threading.Thread(
                    target=self.switch_auto_lang,
                    args=(dest_language, src_text, dest_text)
                ).start()
                return

        # Switch all
        self.switch_all(src_language, dest_language, src_text, dest_text)

    def ui_clear(self, _button):
        self.src_buffer.set_text('')

    def ui_copy(self, _button):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        self.clipboard.set_text(dest_text, -1)
        self.clipboard.store()

    def ui_paste(self, _button):
        text = self.clipboard.wait_for_text()
        if text is not None:
            end_iter = self.src_buffer.get_end_iter()
            self.src_buffer.insert(end_iter, text)

    def ui_voice(self, _button):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        dest_language = self.dest_lang_selector.get_property('selected')
        # Add here code that changes voice button behavior
        if dest_text != '':
            self.toggle_voice_spinner(True)
            if self.lang_speech:
                threading.Thread(
                    target=self.voice_download,
                    args=(dest_text, dest_language)
                ).start()
            else:
                threading.Thread(
                    target=self.load_lang_speech,
                    args=(True, dest_text, dest_language)
                ).start()

    def on_gst_message(self, _bus, message):
        if message.type == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.player_event.set()
        elif message.type == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            self.player_event.set()
            print('Some error occured while trying to play.')

    def voice_download(self, text, language):
        try:
            self.voice_loading = True
            tts = gTTS(text, lang=language, lang_check=False)
            with NamedTemporaryFile() as file_to_play:
                tts.write_to_fp(file_to_play)
                file_to_play.seek(0)
                self.player.set_property('uri', 'file://' + file_to_play.name)
                self.player.set_state(Gst.State.PLAYING)
                self.player_event.wait()
        except Exception as exc:
            print(exc)
            print('Audio download failed.')
            GLib.idle_add(self.on_listen_failed)
        else:
            GLib.idle_add(self.toggle_voice_spinner, False)
        finally:
            self.voice_loading = False

    # This starts the translation if Ctrl+Enter button is pressed
    def update_trans_button(self, button, keyboard):
        modifiers = keyboard.get_state() & Gtk.accelerator_get_default_mod_mask()

        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyboard.keyval)
        if (GLib.unichar_isgraph(chr(unicode_key_val)) and
                modifiers in (shift_mask, 0) and not self.src_text.is_focus()):
            self.src_text.grab_focus()

        if not self.settings.get_boolean('live-translation'):
            if control_mask == modifiers:
                if keyboard.keyval == Gdk.KEY_Return:
                    if not self.settings.get_value('translate-accel'):
                        self.translation(button)
                        return Gdk.EVENT_STOP
                    return Gdk.EVENT_PROPAGATE
            elif keyboard.keyval == Gdk.KEY_Return:
                if self.settings.get_value('translate-accel'):
                    self.translation(button)
                    return Gdk.EVENT_STOP
                return Gdk.EVENT_PROPAGATE

        return Gdk.EVENT_PROPAGATE

    def text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.translate_btn.set_sensitive(sensitive)
        self.clear_btn.set_sensitive(sensitive)

    def user_action_ended(self, _buffer):
        if self.settings.get_boolean('live-translation'):
            self.translation(None)

    # The history part
    def reset_return_forward_btns(self):
        self.return_btn.set_sensitive(self.current_history < len(self.history) - 1)
        self.forward_btn.set_sensitive(self.current_history > 0)

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_btns()
        lang_hist = self.history[self.current_history]
        self.src_lang_selector.set_property('selected',
                                             lang_hist['Languages'][0])
        self.dest_lang_selector.set_property('selected',
                                              lang_hist['Languages'][1])
        self.src_buffer.set_text(lang_hist['Text'][0])
        self.dest_buffer.set_text(lang_hist['Text'][1])

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def appeared_before(self):
        src_language = self.src_lang_selector.get_property('selected')
        dest_language = self.dest_lang_selector.get_property('selected')
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        if (self.history[self.current_history]['Languages'][0] == src_language and
                self.history[self.current_history]['Languages'][1] == dest_language and
                self.history[self.current_history]['Text'][0] == src_text and
                not self.trans_failed):
            return True
        return False

    def translation(self, _button):
        # If it's like the last translation then it's useless to continue
        if len(self.history) == 0 or not self.appeared_before():
            src_text = self.src_buffer.get_text(
                self.src_buffer.get_start_iter(),
                self.src_buffer.get_end_iter(),
                True
            )
            # If the first text is empty, then everything is simply resetted and nothing is saved in history
            if src_text == '':
                self.dest_buffer.set_text('')
            else:
                src_language = self.src_lang_selector.get_property('selected')
                dest_language = self.dest_lang_selector.get_property('selected')

                if self.trans_queue:
                    self.trans_queue.pop(0)
                self.trans_queue.append({
                    'src_text': src_text,
                    'src_language': src_language,
                    'dest_language': dest_language
                })

                # Check if there are any active threads.
                if self.active_thread is None:
                    # Show feedback for start of translation.
                    self.trans_spinner.show()
                    self.trans_spinner.start()
                    self.dest_box.set_sensitive(False)
                    self.langs_button_box.set_sensitive(False)
                    # If there are not any active threads, create one and start it.
                    self.active_thread = threading.Thread(target=self.run_translation)
                    self.active_thread.start()

    def run_translation(self):
        def on_trans_failed():
            self.trans_warning.show()
            self.send_notification('Translation failed.\nPlease check for network issues.')
            self.copy_btn.set_sensitive(False)
            self.voice_btn.set_sensitive(False)

        def on_trans_success():
            self.trans_warning.hide()
            self.copy_btn.set_sensitive(True)
            if not self.voice_loading:
                self.voice_btn.set_sensitive(True)

        def on_trans_done():
            self.trans_spinner.stop()
            self.trans_spinner.hide()
            self.dest_box.set_sensitive(True)
            self.langs_button_box.set_sensitive(True)

        while self.trans_queue:
            # If the first language is revealed automatically, let's set it
            trans_dict = self.trans_queue.pop(0)
            src_text = trans_dict['src_text']
            src_language = trans_dict['src_language']
            dest_language = trans_dict['dest_language']
            if src_language == 'auto' and src_text != '':
                src_language = str(self.translator.detect(src_text).lang)
                GLib.idle_add(self.src_lang_selector.set_property,
                              'selected', src_language)
                self.src_langs[0] = src_language
            # If the two languages are the same, nothing is done
            if src_language != dest_language:
                dest_text = ''
                # If the text is over the highest number of characters allowed, it is truncated.
                # This is done for avoiding exceeding the limit imposed by Google.
                if len(src_text) > 100:
                    src_text = src_text[:MAX_LENGTH]
                # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                try:
                    dest_text = self.translator.translate(
                        src_text,
                        src=src_language,
                        dest=dest_language
                    ).text
                    self.trans_failed = False
                except Exception:
                    self.trans_failed = True
                GLib.idle_add(self.dest_buffer.set_text, dest_text)

                # Finally, everything is saved in history
                self.add_history_entry(src_language, dest_language, src_text, dest_text)
        if self.trans_failed:
            GLib.idle_add(on_trans_failed)
        else:
            GLib.idle_add(on_trans_success)
        GLib.idle_add(on_trans_done)
        self.active_thread = None
