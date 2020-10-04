pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'dialect')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('pkgdatadir', pkgdatadir)

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
]
# Install sources
install_data(sources, install_dir: moduledir)
