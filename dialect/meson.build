gnome = import('gnome')
python = import('python')
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

# Resources
blueprints = custom_target('blueprints',
  input: files(
    'shortcuts.blp',
    'window.blp',
    'widgets/lang_selector.blp',
    'widgets/lang_row.blp',
    'widgets/provider_preferences.blp',
    'widgets/theme_switcher.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gresource_conf = configuration_data()
gresource_conf.set('appstream-path', appstream_file.full_path())
gnome.compile_resources('dialect',
  configure_file(
    input: 'dialect.gresource.xml',
    output: 'dialect.gresource.xml',
    configuration: gresource_conf,
  ),
  dependencies: [blueprints, appstream_file],
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

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