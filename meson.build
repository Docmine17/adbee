project('adbee',
  version: '1.0.0',
  meson_version: '>= 0.62.0',
  default_options: ['warning_level=2', 'werror=false'],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

py_installation = python.find_installation('python3')

APPLICATION_ID = 'io.github.docmine17.adbee'

conf = configuration_data()
conf.set('APPLICATION_ID', APPLICATION_ID)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', py_installation.full_path())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', get_option('prefix') / get_option('datadir') / meson.project_name())

subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
