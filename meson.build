project('gnabel',
          version: '0.0.0',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

subdir('data')
subdir('src')

meson.add_install_script('build-aux/meson/postinstall.py')
