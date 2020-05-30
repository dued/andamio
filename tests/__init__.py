#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ejecuta pruebas para esta imagen base

Cada prueba debe ser un archivo valido docker-compose.yaml con un servicio ``odoo``.
"""
import logging
import unittest
from itertools import product
from os import environ
from os.path import dirname, join
from subprocess import Popen

logging.basicConfig(level=logging.DEBUG)

DIR = dirname(__file__)
ODOO_PREFIX = ("odoo", "--stop-after-init", "--workers=0")
ODOO_VERSIONS = frozenset(
    environ.get("DOCKER_TAG", "7.0 8.0 9.0 10.0 11.0 12.0 13.0").split()
)
PG_VERSIONS = frozenset(environ.get("PG_VERSIONS", "12").split())
SCAFFOLDINGS_DIR = join(DIR, "scaffoldings")
GEIOP_CREDENTIALS_PROVIDED = environ.get("GEOIP_LICENSE_KEY", False) and environ.get(
    "GEOIP_ACCOUNT_ID", False
)

# Este decorador omite las pruebas que fallaran hasta que algunas ramas
# y/o complementos se migren a la próxima versión. Se utiliza en situaciones
# en las que Andamio esta preparando el prelanzamiento para la próxima
# versión de Odoo, que aún no se ha lanzado.
prerelease_skip = unittest.skipIf(
    ODOO_VERSIONS == {"13.0"}, "Pruebas no soportadas en pre-release"
)


def matrix(
    odoo=ODOO_VERSIONS, pg=PG_VERSIONS, odoo_skip=frozenset(), pg_skip=frozenset()
):
    """Todas las combinaciones posibles.

    Calculamos la matriz variable aqui en lugar de en ``.travis.yml`` porque
    esto genera compilaciones mas rapidas, dado que los scripts encontrados
    en el directorio ``hooks`` ya son compatibles con la compilacion de
    multiples versiones.
    """
    return map(
        dict,
        product(
            product(("ODOO_MINOR",), ODOO_VERSIONS & odoo - odoo_skip),
            product(("DB_VERSION",), PG_VERSIONS & pg - pg_skip),
        ),
    )


class ScaffoldingCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.compose_run = ("docker-compose", "run", "--rm", "odoo")

    def popen(self, *args, **kwargs):
        """Acceso directo para abrir un subproceso y asegurarse de que funciona."""
        logging.info("Ejecucion de subprueba: %s", self.subTest)
        self.assertFalse(Popen(*args, **kwargs).wait())

    def compose_test(self, workdir, sub_env, *commands):
        """Ejecuta comandos en un entorno docker-compose.

        :param workdir:
            Ruta donde se ejecutaran los comandos docker compose. Debe
            contener un archivo valido ``docker-compose.yaml``.

        :param dict sub_env:
            Variables de entorno especificas que se agregaran a las actuales
            para ejecutar las pruebas de ``docker-compose``.

            Puede establecer en este diccionario una clave ``COMPOSE_FILE``
            para elegir diferentes archivos docker-compose en el mismo directorio

        :param tuple()... commands:
            Lista de comandos para probar en el contenedor de odoo.
        """
        full_env = dict(environ, **sub_env)
        with self.subTest(PWD=workdir, **sub_env):
            try:
                self.popen(("docker-compose", "build"), cwd=workdir, env=full_env)
                for command in commands:
                    with self.subTest(command=command):
                        self.popen(
                            self.compose_run + command, cwd=workdir, env=full_env
                        )
            finally:
                self.popen(("docker-compose", "down", "-v"), cwd=workdir, env=full_env)

    def test_addons_filtered(self):
        """PRUEBA los addons con la palabra clave ``ONLY`` en ``addons.yaml``."""
        project_dir = join(SCAFFOLDINGS_DIR, "dotd")
        for sub_env in matrix():
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="prod"),
                ("test", "-e", "auto/addons/web"),
                ("test", "-e", "auto/addons/private_addon"),
                (
                    "bash",
                    "-xc",
                    'test "$(addons list -p)" == disabled_addon,private_addon',
                ),
                ("bash", "-xc", 'test "$(addons list -ip)" == private_addon'),
                ("bash", "-xc", "addons list -c | grep ,crm,"),
                # absent_addon falta y debería fallar
                ("bash", "-xc", "! addons list -px"),
                # Prueba de inclusión de complementos, exclusión, dependencias ...
                (
                    "bash",
                    "-xc",
                    'test "$(addons list -dw private_addon)" == base,dummy_addon,website',
                ),
                (
                    "bash",
                    "-xc",
                    'test "$(addons list -dwprivate_addon -Wwebsite)" == base,dummy_addon',
                ),
                (
                    "bash",
                    "-xc",
                    'test "$(addons list -dw private_addon -W dummy_addon)" == base,website',
                ),
                ("bash", "-xc", 'test "$(addons list -nd)" == base,iap',),
                (
                    "bash",
                    "-xc",
                    'test "$(addons list --enterprise)" == make_odoo_rich',
                ),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_private"),
                ("test", "-e", "auto/addons/web"),
                ("test", "!", "-e", "auto/addons/private_addon"),
                ("bash", "-xc", 'test -z "$(addons list -p)"'),
                (
                    "bash",
                    "-xc",
                    '[ "$(addons list -s. -pwfake1 -wfake2)" == fake1.fake2 ]',
                ),
                ("bash", "-xc", "! addons list -wrepeat -Wrepeat"),
                ("bash", "-xc", "addons list -c | grep ,crm,"),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_core"),
                ("test", "!", "-e", "auto/addons/web"),
                ("test", "!", "-e", "auto/addons/private_addon"),
                ("bash", "-xc", 'test -z "$(addons list -p)"'),
                ("bash", "-xc", 'test "$(addons list -c)" == crm,sale'),
            )
        # Omita las versiones de Odoo que no admiten archivos __manifest__.py
        for sub_env in matrix(odoo_skip={"7.0", "8.0", "9.0"}):
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="prod"),
                ("bash", "-xc", 'test "$(addons list -ped)" == base,web,website'),
                # ``dummy_addon`` y ``private_addon`` existen
                ("test", "-d", "auto/addons/dummy_addon"),
                ("test", "-h", "auto/addons/dummy_addon"),
                ("test", "-f", "auto/addons/dummy_addon/__init__.py"),
                ("test", "-e", "auto/addons/dummy_addon"),
                # El complemento del repositorio adicional tiene mayor prioridad
                # que la versión principal
                ("realpath", "auto/addons/product"),
                (
                    "bash",
                    "-xc",
                    'test "$(realpath auto/addons/product)" == '
                    "/opt/odoo/custom/src/otro-andamio/odoo/src/private/product",
                ),
                ("bash", "-xc", 'test "$(addons list -e)" == dummy_addon,product'),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_private"),
                ("test", "-e", "auto/addons/dummy_addon"),
                ("bash", "-xc", 'test "$(addons list -e)" == dummy_addon,product'),
            )
            self.compose_test(
                project_dir,
                dict(sub_env, DBNAME="limited_core"),
                ("test", "-e", "auto/addons/dummy_addon"),
                (
                    "bash",
                    "-xc",
                    '[ "$(addons list -s. -pwfake1 -wfake2)" == fake1.fake2 ]',
                ),
                ("bash", "-xc", 'test "$(addons list -e)" == dummy_addon,product'),
                ("bash", "-xc", 'test "$(addons list -c)" == crm,sale'),
                ("bash", "-xc", 'test "$(addons list -cWsale)" == crm'),
            )

    @prerelease_skip
    def test_qa(self):
        """PRUEBA que herramientas QA esten en su lugar y funcionen como se espera."""
        folder = join(SCAFFOLDINGS_DIR, "settings")
        commands = (
            ("./custom/scripts/qa-insider-test",),
            ("/qa/node_modules/.bin/eslint", "--version"),
            ("/qa/venv/bin/flake8", "--version"),
            ("/qa/venv/bin/pylint", "--version"),
            ("/qa/venv/bin/python", "--version"),
            ("/qa/venv/bin/python", "-c", "import pylint_odoo"),
            ("test", "-d", "/qa/mqt"),
        )
        for sub_env in matrix():
            self.compose_test(folder, sub_env, *commands)

    @prerelease_skip
    def test_settings(self):
        """PRUEBA que la configuracion se complete OK"""
        folder = join(SCAFFOLDINGS_DIR, "settings")
        commands = (
            # Odoo debería instalar
            ("--stop-after-init",),
            # Odoo ajustes de trabajo
            ("./custom/scripts/test_settings.py",),
        )
        # Odoo 8.0 no tiene shell, y --load-language no funciona bien en 9.0
        for sub_env in matrix(odoo={"9.0"}):
            self.compose_test(folder, sub_env, *commands)
        # Extra tests para versions>= 10.0, que soportan --load-language sutil
        commands += (
            # DB was created with the correct language
            (
                "bash",
                "-xc",
                """test "$(psql -Atqc "SELECT code FROM res_lang
                                    WHERE active = TRUE")" == es_ES""",
            ),
        )
        for sub_env in matrix(odoo_skip={"7.0", "8.0", "9.0"}):
            self.compose_test(folder, sub_env, *commands)

    def test_smallest(self):
        """PRUEBA para el entorno mas pequeno posible."""
        liberation = 'Liberation{0}-Regular.ttf: "Liberation {0}" "Regular"'
        commands = (
            # Debe generar un archivo de configuración
            ("test", "-f", "/opt/odoo/auto/odoo.conf"),
            ("test", "-d", "/opt/odoo/custom/src/private"),
            ("test", "-d", "/opt/odoo/custom/ssh"),
            ("addons", "list", "-cpix"),
            ("pg_activity", "--version"),
            # Las fuentes predeterminadas deben ser `liberation`
            (
                "bash",
                "-xc",
                """test "$(fc-match monospace)" == '{}'""".format(
                    liberation.format("Mono")
                ),
            ),
            (
                "bash",
                "-xc",
                """test "$(fc-match sans-serif)" == '{}'""".format(
                    liberation.format("Sans")
                ),
            ),
            (
                "bash",
                "-xc",
                """test "$(fc-match serif)" == '{}'""".format(
                    liberation.format("Serif")
                ),
            ),
            # Debe poder instalar el complemento base
            ODOO_PREFIX + ("--init", "base"),
            # El actualizador automático debe funcionar
            ("click-odoo-update",),
            # Existen herramientas necesarias
            ("curl", "--version"),
            ("git", "--version"),
            ("pg_activity", "--version"),
            ("psql", "--version"),
            ("msgmerge", "--version"),
            ("ssh", "-V"),
            ("python", "-c", "import plumbum"),
            # Somos capaces de volcar
            ("pg_dump", "-f/var/lib/odoo/prod.sql", "prod"),
            # Geoip no debe activarse
            ("bash", "-xc", 'test "$(which geoipupdate)" != ""'),
            ("test", "!", "-e", "/usr/share/GeoIP/GeoLite2-City.mmdb"),
            ("bash", "-xc", "! geoipupdate"),
        )
        smallest_dir = join(SCAFFOLDINGS_DIR, "smallest")
        for sub_env in matrix(odoo_skip={"7.0", "8.0"}):
            self.compose_test(
                smallest_dir, sub_env, *commands, ("python", "-c", "import watchdog")
            )
        for sub_env in matrix(odoo={"8.0"}):
            self.compose_test(
                smallest_dir,
                sub_env,
                # Odoo <= 8.0 no crea automáticamente la base de datos
                ("createdb",),
                *commands,
            )

    def test_addons_env(self):
        """PRUEBA variables de entorno en addons.yaml"""
        # Las versiones antiguas están esquivadas porque no admiten
        # __manifest__.py, y la PRUEBA está hackeando ODOO_VERSION
        # para anclar un commit o confirmación
        for sub_env in matrix(odoo_skip={"7.0", "8.0", "9.0"}):
            self.compose_test(
                join(SCAFFOLDINGS_DIR, "addons_env"),
                sub_env,
                # comprobar módulo desde el repositorio custom personalizado
                ("test", "-d", "custom/src/misc-addons"),
                ("test", "-d", "custom/src/misc-addons/web_debranding"),
                ("test", "-e", "auto/addons/web_debranding"),
                # La carpeta de migraciones solo está en OpenUpgrade
                ("test", "-e", "auto/addons/crm"),
                ("test", "-d", "auto/addons/crm/migrations"),
            )

    def test_dotd(self):
        """PRUEBA entorno con directorio common ``*.d``."""
        for sub_env in matrix():
            self.compose_test(
                join(SCAFFOLDINGS_DIR, "dotd"),
                sub_env,
                # ``custom/build.d`` fue ejecutado correctamente
                ("test", "-f", "/home/odoo/created-at-build"),
                # ``custom/entrypoint.d`` fue ejecutado correctamente
                ("test", "-f", "/home/odoo/created-at-entrypoint"),
                # ``custom/conf.d`` Está adecuadamente concatenado
                ("grep", "test-conf", "auto/odoo.conf"),
                # ``custom/dependencies`` fueron instalados
                ("test", "!", "-e", "/usr/sbin/sshd"),
                ("test", "!", "-e", "/var/lib/apt/lists/lock"),
                ("busybox", "whoami"),
                ("bash", "-xc", "echo $NODE_PATH"),
                ("node", "-e", "require('test-npm-install')"),
                ("aloha_world",),
                ("python", "-xc", "import Crypto; print(Crypto.__version__)"),
                ("sh", "-xc", "rst2html.py --version | grep 'Docutils 0.14'"),
                # ``requirements.txt`` de repositorios adicionales se procesaron
                ("python", "-c", "import cfssl"),
                # Binarios ejecutables locales encontrados en $PATH
                ("sh", "-xc", "pip install --user -q flake8 && which flake8"),
                # La limpieza de complementos funciona correctamente
                ("test", "!", "-e", "custom/src/private/dummy_addon"),
                ("test", "!", "-e", "custom/src/dummy_repo/dummy_link"),
                ("test", "-d", "custom/src/private/private_addon"),
                ("test", "-f", "custom/src/private/private_addon/__init__.py"),
                ("test", "-e", "auto/addons/private_addon"),
                # comando ``odoo`` funciona
                ("odoo", "--version"),
                # El comando implícito `` odoo`` también funciona
                ("--version",),
            )

    # TODO Elimine el decorador cuando se publique OCB 13.0 y server-tools
    # 13.0 tenga un modulo válido para probar
    @prerelease_skip
    def test_dependencies(self):
        """PRUEBA la instalacion de dependencias."""
        dependencies_dir = join(SCAFFOLDINGS_DIR, "dependencies")
        for sub_env in matrix(odoo_skip={"7.0"}):
            self.compose_test(
                dependencies_dir,
                sub_env,
                ("test", "!", "-f", "custom/dependencies/apt.txt"),
                ("test", "!", "-f", "custom/dependencies/gem.txt"),
                ("test", "!", "-f", "custom/dependencies/npm.txt"),
                ("test", "!", "-f", "custom/dependencies/pip.txt"),
                # Debería tener module_auto_update disponible
                ("test", "-d", "custom/src/server-tools/module_auto_update"),
                # Versión parcheada de Werkzeug
                (
                    "bash",
                    "-xc",
                    (
                        'test "$(python -c "import werkzeug; '
                        'print(werkzeug.__version__)")" == 0.14.1'
                    ),
                ),
                # apt_build.txt
                ("test", "-f", "custom/dependencies/apt_build.txt"),
                ("test", "!", "-e", "/usr/sbin/sshd"),
                # apt-without-sequence.txt
                ("test", "-f", "custom/dependencies/apt-without-sequence.txt"),
                ("test", "!", "-e", "/bin/busybox"),
                # 070-apt-bc.txt
                ("test", "-f", "custom/dependencies/070-apt-bc.txt"),
                ("test", "-e", "/usr/bin/bc"),
                # 150-npm-aloha_world-install.txt
                (
                    "test",
                    "-f",
                    ("custom/dependencies/" "150-npm-aloha_world-install.txt"),
                ),
                ("node", "-e", "require('test-npm-install')"),
                # 200-pip-without-ext
                ("test", "-f", "custom/dependencies/200-pip-without-ext"),
                ("python", "-c", "import Crypto; print(Crypto.__version__)"),
                ("sh", "-xc", "rst2html.py --version | grep 'Docutils 0.14'"),
                # 270-gem.txt
                ("test", "-f", "custom/dependencies/270-gem.txt"),
                ("aloha_world",),
            )

    def test_modified_uids(self):
        """PRUEBA si podemos construir una imagen con uid personalizado y gid de odoo"""
        uids_dir = join(SCAFFOLDINGS_DIR, "uids_1001")
        for sub_env in matrix():
            self.compose_test(
                uids_dir,
                sub_env,
                # Verifica que el usuario de odoo tenga los id.
                ("bash", "-xc", 'test "$(id -u)" == "1001"'),
                ("bash", "-xc", 'test "$(id -g)" == "1002"'),
                ("bash", "-xc", 'test "$(id -u -n)" == "odoo"'),
                # todos esos directorios deben pertenecer a odoo (usuario o grupo odoo)
                (
                    "bash",
                    "-xc",
                    'test "$(stat -c \'%U:%G\' /var/lib/odoo)" == "odoo:odoo"',
                ),
                (
                    "bash",
                    "-xc",
                    'test "$(stat -c \'%U:%G\' /opt/odoo/auto/addons)" == "root:odoo"',
                ),
                (
                    "bash",
                    "-xc",
                    'test "$(stat -c \'%U:%G\' /opt/odoo/custom/src)" == "root:odoo"',
                ),
            )

    def test_uids_mac_os(self):
        """PRUEBA si podemos construir una imagen con un uid personalizado y gid de odoo mac os"""
        uids_dir = join(SCAFFOLDINGS_DIR, "uids_mac_os")
        for sub_env in matrix():
            self.compose_test(
                uids_dir,
                sub_env,
                # Verifica que el usuario de odoo tenga los id.
                ("bash", "-c", 'test "$(id -u)" == "501"'),
                ("bash", "-c", 'test "$(id -g)" == "20"'),
                ("bash", "-c", 'test "$(id -u -n)" == "odoo"'),
                # todos esos directorios deben pertenecer a odoo (usuario o grupo odoo / dialout)
                (
                    "bash",
                    "-c",
                    'test "$(stat -c \'%U:%g\' /var/lib/odoo)" == "odoo:20"',
                ),
                (
                    "bash",
                    "-c",
                    'test "$(stat -c \'%U:%g\' /opt/odoo/auto/addons)" == "root:20"',
                ),
                (
                    "bash",
                    "-c",
                    'test "$(stat -c \'%U:%g\' /opt/odoo/custom/src)" == "root:20"',
                ),
            )

    def test_default_uids(self):
        uids_dir = join(SCAFFOLDINGS_DIR, "uids_default")
        for sub_env in matrix():
            self.compose_test(
                uids_dir,
                sub_env,
                # Verifica que la usuario de odoo tenga los id.
                ("bash", "-xc", 'test "$(id -u)" == "1000"'),
                ("bash", "-xc", 'test "$(id -g)" == "1000"'),
                ("bash", "-xc", 'test "$(id -u -n)" == "odoo"'),
                # todos esos directorios deben pertenecer a odoo (usuario o grupo odoo)
                (
                    "bash",
                    "-xc",
                    'test "$(stat -c \'%U:%G\' /var/lib/odoo)" == "odoo:odoo"',
                ),
                (
                    "bash",
                    "-xc",
                    'test "$(stat -c \'%U:%G\' /opt/odoo/auto/addons)" == "root:odoo"',
                ),
                (
                    "bash",
                    "-xc",
                    'test "$(stat -c \'%U:%G\' /opt/odoo/custom/src)" == "root:odoo"',
                ),
            )

    @unittest.skipIf(
        not GEIOP_CREDENTIALS_PROVIDED, "Faltan credenciales de GeoIP en el entorno"
    )
    def test_geoip(self):
        geoip_dir = join(SCAFFOLDINGS_DIR, "geoip")
        for sub_env in matrix():
            self.compose_test(
                geoip_dir,
                sub_env,
                # verifica que geoipupdate funcione después de esperar que el punto de
                # entrada termine su actualización
                (
                    "bash",
                    "-c",
                    "timeout 60s bash -c 'while (ls -l /proc/*/exe 2>&1 | grep geoipupdate); do sleep 1; done' &&"
                    " geoipupdate",
                ),
                # verifica que la base de datos de geoip existe después de que el
                # punto de entrada finalizó su actualización usando ls y /proc
                # porque falta ps en la imagen para 13.0
                (
                    "bash",
                    "-c",
                    "timeout 60s bash -c 'while (ls -l /proc/*/exe 2>&1 | grep geoipupdate); do sleep 1; done' &&"
                    " test -e /opt/odoo/auto/geoip/GeoLite2-City.mmdb",
                ),
                # verifica que la base de datos geoip esté configurada
                (
                    "grep",
                    "-R",
                    "geoip_database = /opt/odoo/auto/geoip/GeoLite2-City.mmdb",
                    "/opt/odoo/auto/odoo.conf",
                ),
            )


if __name__ == "__main__":
    unittest.main()
