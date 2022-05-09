serarch_provider_dir = join_paths(get_option('prefix'), get_option('datadir'), 'gnome-shell', 'search-providers')
service_dir = join_paths(get_option('prefix'), get_option('datadir'), 'dbus-1', 'services')

install_data(
  'app.drey.Dialect.SearchProvider.ini',
  install_dir: serarch_provider_dir,
)

configure_file(
  input: 'app.drey.Dialect.SearchProvider.service.in',
  output: 'app.drey.Dialect.SearchProvider.service',
  configuration: conf,
  install_dir: service_dir,
)

configure_file(
  input: 'search_provider.in',
  output: 'search_provider',
  configuration: conf,
  install_dir: pkgdatadir,
)

