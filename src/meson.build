python = import('python')

# Generate dialect bin
configure_file(
  input: 'dialect.in',
  output: 'dialect',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

launcher = join_paths(meson.build_root(), 'src', meson.project_name())
run_target('run',
  command: [launcher]
)

subdir('search_provider')

# Python sources
sources = [
  '__init__.py',
  'main.py',
  'define.py',
  'window.py',
  'preferences.py',
  'lang_selector.py',
  'settings.py',
]
# Install sources
install_data(sources, install_dir: moduledir)

# Install translators and tts providers
install_subdir('translators', install_dir: moduledir)
install_subdir('tts', install_dir: moduledir)
