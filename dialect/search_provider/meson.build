search_provider_dir = join_paths(get_option('prefix'), get_option('datadir'), 'gnome-shell', 'search-providers')
service_dir = join_paths(get_option('prefix'), get_option('datadir'), 'dbus-1', 'services')

configure_file(
  input: 'app.drey.Dialect.SearchProvider.ini',
  output: '@0@.SearchProvider.ini'.format(application_id),
  configuration: conf,
  install_dir: search_provider_dir,
)

configure_file(
  input: 'app.drey.Dialect.SearchProvider.service.in',
  output: '@0@.SearchProvider.service'.format(application_id),
  configuration: conf,
  install_dir: service_dir,
)

configure_file(
  input: 'search_provider.in',
  output: 'search_provider',
  configuration: conf,
  install_dir: pkgdatadir,
)

