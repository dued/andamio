# -*- coding: utf-8 -*-
import logging
import os
from glob import glob
from pprint import pformat
from subprocess import check_output

import yaml

# Constantes necesarias en scripts
CUSTOM_DIR = "/opt/odoo/custom"
AUTO_DIR = "/opt/odoo/auto"
ADDONS_DIR = os.path.join(AUTO_DIR, "addons")
SRC_DIR = os.path.join(CUSTOM_DIR, "src")

ADDONS_YAML = os.path.join(SRC_DIR, "addons")
if os.path.isfile("%s.yaml" % ADDONS_YAML):
    ADDONS_YAML = "%s.yaml" % ADDONS_YAML
else:
    ADDONS_YAML = "%s.yml" % ADDONS_YAML

REPOS_YAML = os.path.join(SRC_DIR, "repos")
if os.path.isfile("%s.yaml" % REPOS_YAML):
    REPOS_YAML = "%s.yaml" % REPOS_YAML
else:
    REPOS_YAML = "%s.yml" % REPOS_YAML

AUTO_REPOS_YAML = os.path.join(AUTO_DIR, "repos")
if os.path.isfile("%s.yml" % AUTO_REPOS_YAML):
    AUTO_REPOS_YAML = "%s.yml" % AUTO_REPOS_YAML
else:
    AUTO_REPOS_YAML = "%s.yaml" % AUTO_REPOS_YAML

CLEAN = os.environ.get("CLEAN") == "true"
LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
FILE_APT_BUILD = os.path.join(CUSTOM_DIR, "dependencies", "apt_build.txt")
PRIVATE = "private"
CORE = "odoo/addons"
ENTERPRISE = "enterprise"
PRIVATE_DIR = os.path.join(SRC_DIR, PRIVATE)
CORE_DIR = os.path.join(SRC_DIR, CORE)
ODOO_DIR = os.path.join(SRC_DIR, "odoo")
ODOO_VERSION = os.environ["ODOO_VERSION"]
MANIFESTS = ("__manifest__.py", "__openerp__.py")
if ODOO_VERSION in {"8.0", "9.0"}:
    MANIFESTS = MANIFESTS[1:]

# Personalizar el registro (logging) para la compilación
logger = logging.getLogger("andamio")
log_handler = logging.StreamHandler()
log_formatter = logging.Formatter("%(name)s %(levelname)s: %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)
_log_level = os.environ.get("LOG_LEVEL", "")
if _log_level.isdigit():
    _log_level = int(_log_level)
elif _log_level in LOG_LEVELS:
    _log_level = getattr(logging, _log_level)
else:
    if _log_level:
        logger.warning("Valor incorrecto en $LOG_LEVEL, volviendo a INFO")
    _log_level = logging.INFO
logger.setLevel(_log_level)


class AddonsConfigError(Exception):
    def __init__(self, message, *args):
        super(AddonsConfigError, self).__init__(message, *args)
        self.message = message


def addons_config(filtered=True, strict=False):
    """Genera nombre de complemento `addon` y su path desde ``ADDONS_YAML``.

    :param bool filtered:
        Use ``False`` para incluir todas las definiciones de complementos.
        Use ``True``(predeterminado) para incluir solo aquellos que coincidan
        con las clausulas ``ONLY``, si corresponde.

    :param bool strict:
        Use ``True`` para generar una excepcion si no se encuentra ningun
        complemento declarado.

    :return Iterator[str, str]:
        Un generador que produce pares ``(addon, repo)``.
    """
    config = dict()
    missing_glob = set()
    missing_manifest = set()
    all_globs = {}
    try:
        with open(ADDONS_YAML) as addons_file:
            for doc in yaml.safe_load_all(addons_file):
                # Saltar secciones con ONLY y que no coinciden
                only = doc.pop("ONLY", {})
                if not filtered:
                    doc.setdefault(CORE, ["*"])
                    doc.setdefault(PRIVATE, ["*"])
                elif any(
                    os.environ.get(key) not in values for key, values in only.items()
                ):
                    logger.debug("Saltar seccion con ONLY %s", only)
                    continue
                # Acoplar todas las secciones en un solo dict
                for repo, partial_globs in doc.items():
                    if repo == "ENV":
                        continue
                    logger.debug("Procesando %s repo", repo)
                    all_globs.setdefault(repo, set())
                    all_globs[repo].update(partial_globs)
    except IOError:
        logger.debug("No se pudo encontrar la configuracion de complementos yaml.")
    # Agregar valores predeterminados para secciones especiales
    for repo in (CORE, PRIVATE):
        all_globs.setdefault(repo, {"*"})
    logger.debug("Definicion de addons combinados antes de expandir: %r", all_globs)
    # Expandir todos los globs y almacenar la configuración
    for repo, partial_globs in all_globs.items():
        for partial_glob in partial_globs:
            logger.debug("Expandiendo en repo %s glob %s", repo, partial_glob)
            full_glob = os.path.join(SRC_DIR, repo, partial_glob)
            found = glob(full_glob)
            if not found:
                # Los proyectos sin complementos privados nunca deberían fallar
                if (repo, partial_glob) != (PRIVATE, "*"):
                    missing_glob.add(full_glob)
                logger.debug("Omitiendo el globo no expandible '%s'", full_glob)
                continue
            for addon in found:
                if not os.path.isdir(addon):
                    continue
                manifests = (os.path.join(addon, m) for m in MANIFESTS)
                if not any(os.path.isfile(m) for m in manifests):
                    missing_manifest.add(addon)
                    logger.debug(
                        "Omitiendo '%s' ya que no es un Odoo valido " "module", addon
                    )
                    continue
                logger.debug("Registro de complemento %s", addon)
                addon = os.path.basename(addon)
                config.setdefault(addon, set())
                config[addon].add(repo)
    # Ahora falla si se ejecuta en modo estricto
    if strict:
        error = []
        if missing_glob:
            error += ["Complementos no encontrados:", pformat(missing_glob)]
        if missing_manifest:
            error += ["Complementos sin manifiesto:", pformat(missing_manifest)]
        if error:
            raise AddonsConfigError("\n".join(error), missing_glob, missing_manifest)
    logger.debug("Configuracion resultante despues de expandir: %r", config)
    for addon, repos in config.items():
        # Los complementos privados son los más importantes
        if PRIVATE in repos:
            yield addon, PRIVATE
            continue
        # Los complementos del nucleo de Odoo son los menos importantes
        if repos == {CORE}:
            yield addon, CORE
            continue
        repos.discard(CORE)
        # los complementos se encuentran en el medio
        if len(repos) != 1:
            raise AddonsConfigError(
                u"Addon {} defined in several repos {}".format(addon, repos)
            )
        yield addon, repos.pop()


try:
    from shutil import which
except ImportError:
    # Custom con implementacio para Python 2
    def which(binary):
        return check_output(["which", binary]).strip()
