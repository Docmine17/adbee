pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'adbee'

python = import('python')
gnome = import('gnome')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)
conf.set('APPLICATION_ID', 'io.github.docmine17.adbee')

configure_file(
  input: 'adbee.in',
  output: 'adbee',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

adbee_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'adb_service.py',
  'qr_generator.py',
]

install_data(adbee_sources, install_dir: moduledir)

gnome.compile_resources('adbee',
  'adbee.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)
