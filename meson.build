project('dialect',
          version: '1.4.1',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

python = import('python')
i18n = import('i18n')

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'dialect')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('BIN', join_paths(get_option('prefix'), get_option('bindir'), meson.project_name()))
conf.set('pkgdatadir', pkgdatadir)
conf.set('datadir', get_option('datadir'))
conf.set('prefix', get_option('prefix'))
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))

message('Looking for dependencies')
py_installation = python.find_installation('python3')
if not py_installation.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif

dependency('gobject-introspection-1.0', version: '>= 1.35.0')
dependency('gtk+-3.0', version: '>= 3.22')
dependency('glib-2.0')
dependency('pygobject-3.0', version: '>= 3.29.1')

subdir('data')
subdir('dialect')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')

