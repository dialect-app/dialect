serarch_provider_dir = join_paths('/usr/share', 'gnome-shell', 'search-providers')
service_dir = join_paths('/usr/share', 'dbus-1', 'services')

install_data(
  'com.github.gi_lom.dialect.SearchProvider.ini',
  install_dir: serarch_provider_dir,
)

configure_file(
  input: 'com.github.gi_lom.dialect.SearchProvider.service.in',
  output: 'com.github.gi_lom.dialect.SearchProvider.service',
  configuration: conf,
  install_dir: service_dir,
)

configure_file(
  input: 'search_provider.in',
  output: 'search_provider',
  configuration: conf,
  install_dir: pkgdatadir,
)

