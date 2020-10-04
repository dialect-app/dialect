subdir('resources')

# Install desktop
install_data(
  'com.github.gi_lom.dialect.desktop',
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# Install metainfo
install_data(
  'com.github.gi_lom.dialect.metainfo.xml',
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

# Install gsettings schema
install_data('com.github.gi_lom.dialect.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

# Install colored icon
install_data(
  'com.github.gi_lom.dialect.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

# Install symbolic icon
install_data(
  'com.github.gi_lom.dialect-symbolic.svg',
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)
