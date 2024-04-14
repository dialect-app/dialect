python = import('python')

# Generate dialect bin
configure_file(
  input: 'dialect.in',
  output: 'dialect',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

# Generate dialect define module
configure_file(
  input: 'define.in',
  output: 'define.py',
  configuration: conf,
  install: true,
  install_dir: moduledir
)

launcher = join_paths(meson.project_build_root(), 'dialect', meson.project_name())
run_target('run',
  command: [launcher]
)

subdir('search_provider')

# Python sources
sources = [
  '__init__.py',
  'languages.py',
  'main.py',
  'preferences.py',
  'session.py',
  'settings.py',
  'shortcuts.py',
  'utils.py',
  'window.py',
]
# Install sources
install_data(sources, install_dir: moduledir)

# Install custom widgets
install_subdir('widgets', install_dir: moduledir)

# Install providers
install_subdir('providers', install_dir: moduledir)