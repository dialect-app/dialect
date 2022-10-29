pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
gnome = import('gnome')

blueprints = custom_target('blueprints',
  input: files(
    'about.blp',
    'lang-selector.blp',
    'lang-row.blp',
    'provider-row.blp',
    'providers-list.blp',
    'shortcuts.blp',
    'theme-switcher.blp',
    'window.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('dialect',
  'dialect.gresource.xml',
  dependencies: blueprints,
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)
