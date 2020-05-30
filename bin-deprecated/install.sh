#!/bin/bash
# Tenga en cuenta que este archivo solo se usa en odoo v7-10
set -ex

reqs=https://raw.githubusercontent.com/$ODOO_SOURCE/$ODOO_VERSION/requirements.txt
if [ "$ODOO_VERSION" == "7.0" ]; then
    # V7 no tiene archivo de requisitos, pero casi coincide con v8
    reqs=https://raw.githubusercontent.com/$ODOO_SOURCE/8.0/requirements.txt
    # Estas son las únicas diferencias.
    pip install python-chart 'pywebdav<0.9.8'
fi
apt_deps="python-dev build-essential"
apt-get update

# lxml
apt_deps="$apt_deps libxml2-dev libxslt1-dev"
# Pillow
apt_deps="$apt_deps libjpeg-dev libfreetype6-dev
    liblcms2-dev libopenjpeg-dev libtiff5-dev tk-dev tcl-dev"
# psutil
apt_deps="$apt_deps linux-headers-amd64"
# psycopg2
apt_deps="$apt_deps libpq-dev"
# python-ldap
apt_deps="$apt_deps libldap2-dev libsasl2-dev"

apt-get install -y --no-install-recommends $apt_deps

# Descargue el archivo de requisitos para poder parchearlo
curl -SLo /tmp/requirements.txt $reqs
reqs=/tmp/requirements.txt

if [ "$ODOO_VERSION" == "8.0" ]; then
    # Paquetes ya instalados que entran en conflicto con otros
    sed -ir 's/pyparsing|six/#\0/' $reqs
    # Dependencias adicionales para Odoo en tiempo de ejecución
    apt-get install -y --no-install-recommends file
    # Dependencias adicionales para 'document' (soporte para documentos y pdf)
    apt-get install -y --no-install-recommends antiword poppler-utils
    # Dependencias adicionales para informes de flujo de trabajo
    apt-get install -y --no-install-recommends graphviz ghostscript
fi

# Construye e instala dependencias de Odoo con pip
pip install --requirement $reqs
if [ "$ODOO_VERSION" == "9.0" -o "$ODOO_VERSION" == "10.0" ]; then
    pip install watchdog
fi
if [ "$ODOO_VERSION" == "10.0" ]; then
    pip install astor
fi

# Eliminar toda la basura instalada
apt-get -y purge $apt_deps
apt-get -y autoremove
rm -Rf /var/lib/apt/lists/* /tmp/* || true
