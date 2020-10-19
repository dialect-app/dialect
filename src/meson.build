python = import('python')

# Generate dialect bin
configure_file(
  input: 'dialect.in',
  output: 'dialect',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

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
