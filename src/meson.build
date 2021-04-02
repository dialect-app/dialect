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
subdir('translators')
subdir('tts')

# Python sources
sources = [
  '__init__.py',
  'main.py',
  'define.py',
  'window.py',
  'preferences.py',
  'lang_selector.py',
]
# Install sources
install_data(sources, install_dir: moduledir)
