FROM python:3.10.13-slim-bullseye as base

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generar configuración regional C.UTF-8 para postgres & locale generales
ENV LANG en_US.UTF-8

# Obtiene la arquitectura de destino para instalar wkhtmltopdf correcto
ARG TARGETARCH

# Instala dependencias Oficiales de la version 17.0 para producción
RUN apt-get -qq update &&\
    DEBIAN_FRONTEND=noninteractive \
    apt-get -qq install -y --no-install-recommends \
        ca-certificates \
        curl \
        dirmngr \
        fonts-noto-cjk \
        libssl-dev \
        gnupg \
        node-less \
        npm \
        python3-magic \
        python3-num2words \
        python3-odf \
        python3-pdfminer \
        python3-pip \
        python3-phonenumbers \
        python3-pyldap \
        python3-qrcode \
        python3-renderpm \
        python3-setuptools \
        python3-slugify \
        python3-vobject \
        python3-watchdog \
        python3-xlrd \
        python3-xlwt \
        xz-utils \ 
        # Agregue soporte sudo pal usuario noroot y unzip para CI
        sudo \
        unzip \
        zip &&\
    if [ -z "${TARGETARCH}" ]; then \
        TARGETARCH="$(dpkg --print-architecture)"; \
    fi; \
    WKHTMLTOPDF_ARCH=${TARGETARCH} && \
    case ${TARGETARCH} in \
    "amd64") WKHTMLTOPDF_ARCH=amd64 && WKHTMLTOPDF_SHA=9df8dd7b1e99782f1cfa19aca665969bbd9cc159  ;; \
    "arm64")  WKHTMLTOPDF_SHA=58c84db46b11ba0e14abb77a32324b1c257f1f22  ;; \
    "ppc64le" | "ppc64el") WKHTMLTOPDF_ARCH=ppc64el && WKHTMLTOPDF_SHA=7ed8f6dcedf5345a3dd4eeb58dc89704d862f9cd  ;; \
    esac \
    && curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bullseye_${WKHTMLTOPDF_ARCH}.deb \
    && echo ${WKHTMLTOPDF_SHA} wkhtmltox.deb | sha1sum -c - \
    && apt-get install -y --no-install-recommends ./wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# instala latest postgresql-client
RUN apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends \
    lsb-release \
    && echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && GNUPGHOME="$(mktemp -d)" \
    && export GNUPGHOME \
    && repokey='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
    && gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "${repokey}" \
    && gpg --batch --armor --export "${repokey}" > /etc/apt/trusted.gpg.d/pgdg.gpg.asc \
    && gpgconf --kill all \
    && rm -rf "$GNUPGHOME" \
    && apt-get -qq install -y --no-install-recommends postgresql-client libpq-dev \
    && rm -f /etc/apt/sources.list.d/pgdg.list \
    && rm -rf /var/lib/apt/lists/*

# Install rtlcss (on Debian buster)
RUN npm install -g rtlcss \
    && rm -Rf ~/.npm /tmp/*

FROM base as builder

# Instala dependencias duras (duras significa que el programa
# se romperá si ese paquete no está allí) y las 
# dependencias blandas (blandas significa que es posible que el
# programa no se vea afectado fatalmente)?
RUN pip install --upgrade pip

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Dependencias para pip requirements.txt
        build-essential \
        libldap2-dev \
        libsasl2-dev \
        # Dependencias de operación
        # chromium \
        git-core \
        htop \
        locales \
        ssh \
        vim \
        # Dependencias de desarrollo
        ffmpeg \
        fonts-liberation2 \
        apt-utils dialog \
        apt-transport-https \
        libfreetype6-dev \
        libfribidi-dev \
        libghc-zlib-dev \
        libharfbuzz-dev \
        libjpeg-dev \
        libgeoip-dev \
        libmaxminddb-dev \
        liblcms2-dev \
        libopenjp2-7-dev \
        libtiff5-dev \
        libxml2-dev \
        libxslt1-dev \
        libwebp-dev \
        tcl-dev \
        tk-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Instala desde el codigo fuente de  Odoo dentro del contenedor con herramientas adicionales
ENV ODOO_VERSION ${ODOO_VERSION:-17.0}

RUN pip3 install --prefix=/usr/local --no-cache-dir --upgrade --requirement https://raw.githubusercontent.com/odoo/odoo/${ODOO_VERSION}/requirements.txt \
    && pip3 -qq install --prefix=/usr/local --no-cache-dir --upgrade \
    'websocket-client~=0.56' \
    astor \
    black \
    pylint-odoo \
    flake8 \
    pydevd-odoo \
    psycogreen \
    python-magic \
    python-stdnum \
    click-odoo-contrib \
    git-aggregator \
    inotify \
    python-json-logger \
    wdb \
    redis \
    reportlab \
    && apt-get autopurge -yqq \
    && rm -rf /var/lib/apt/lists/* /tmp/*

RUN git clone --depth 1 -b ${ODOO_VERSION} https://github.com/dued/dued.git /opt/odoo \
    && pip3 install --editable /opt/odoo \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Cuando el código esta presente
# COPY ./dued /opt/odoo

RUN pip3 install --editable /opt/odoo \
    && rm -rf /var/lib/apt/lists/* /tmp/*

FROM base as production

# PIP auto-install requirements.txt (change value to "1" to auto-install)
ENV PIP_AUTO_INSTALL=${PIP_AUTO_INSTALL:-"0"}

# Run tests for all the modules in the custom addons
ENV RUN_TESTS=${RUN_TESTS:-"0"}

# Run tests for all installed modules
ENV WITHOUT_TEST_TAGS=${WITHOUT_TEST_TAGS:-"0"}

# Upgrade all databases visible to this Odoo instance
ENV UPGRADE_ODOO=${UPGRADE_ODOO:-"0"}

    # Create app user
ENV ODOO_USER odoo
ENV ODOO_BASEPATH ${ODOO_BASEPATH:-/opt/odoo}
ARG APP_UID
ENV APP_UID ${APP_UID:-1000}

ARG APP_GID
ENV APP_GID ${APP_UID:-1000}

RUN addgroup --system --gid ${APP_GID} ${ODOO_USER} \
    && adduser --system --uid ${APP_UID} --ingroup ${ODOO_USER} --home ${ODOO_BASEPATH} --disabled-login --shell /sbin/nologin ${ODOO_USER} \
    && echo ${ODOO_USER} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${ODOO_USER}\
    && chmod 0440 /etc/sudoers.d/${ODOO_USER}

# Odoo Configuration file variables and defaults
ARG ADMIN_PASSWORD
ARG PGHOST
ARG PG_USER
ARG PG_PORT
ARG PGPASSWORD
ARG DB_TEMPLATE
ARG HTTP_INTERFACE
ARG HTTP_PORT
ARG DBFILTER
ARG DBNAME
ARG SERVER_WIDE_MODULES

ENV \
    ADMIN_PASSWORD=${ADMIN_PASSWORD:-my-weak-password} \
    ODOO_DATA_DIR=${ODOO_DATA_DIR:-/var/lib/odoo/data} \
    DB_PORT_5432_TCP_ADDR=${PGHOST:-db} \
    DB_MAXCONN=${DB_MAXCONN:-64} \
    DB_ENV_POSTGRES_PASSWORD=${PGPASSWORD:-odoo} \
    DB_PORT_5432_TCP_PORT=${PG_PORT:-5432} \
    DB_SSLMODE=${DB_SSLMODE:-prefer} \
    DB_TEMPLATE=${DB_TEMPLATE:-template1} \
    DB_ENV_POSTGRES_USER=${PG_USER:-odoo} \
    DBFILTER=${DBFILTER:-.*} \
    DBNAME=${DBNAME} \
    HTTP_INTERFACE=${HTTP_INTERFACE:-0.0.0.0} \
    HTTP_PORT=${HTTP_PORT:-8069} \
    LIMIT_REQUEST=${LIMIT_REQUEST:-8196} \
    LIMIT_MEMORY_HARD=${LIMIT_MEMORY_HARD:-2684354560} \
    LIMIT_MEMORY_SOFT=${LIMIT_MEMORY_SOFT:-2147483648} \
    LIMIT_TIME_CPU=${LIMIT_TIME_CPU:-60} \
    LIMIT_TIME_REAL=${LIMIT_TIME_REAL:-120} \
    LIMIT_TIME_REAL_CRON=${LIMIT_TIME_REAL_CRON:-0} \
    LIST_DB=${LIST_DB:-True} \
    LOG_DB=${LOG_DB:-False} \
    LOG_DB_LEVEL=${LOG_DB_LEVEL:-warning} \
    LOGFILE=${LOGFILE:-None} \
    LOG_HANDLER=${LOG_HANDLER:-:INFO} \
    LOG_LEVEL=${LOG_LEVEL:-info} \
    MAX_CRON_THREADS=${MAX_CRON_THREADS:-2} \
    PROXY_MODE=${PROXY_MODE:-False} \
    SERVER_WIDE_MODULES=${SERVER_WIDE_MODULES:-base,web} \
    SMTP_PASSWORD=${SMTP_PASSWORD:-False} \
    SMTP_PORT=${SMTP_PORT:-25} \
    SMTP_SERVER=${SMTP_SERVER:-localhost} \
    SMTP_SSL=${SMTP_SSL:-False} \
    SMTP_USER=${SMTP_USER:-False} \
    TEST_ENABLE=${TEST_ENABLE:-False} \
    UNACCENT=${UNACCENT:-False} \
    WITHOUT_DEMO=${WITHOUT_DEMO:-False} \
    WORKERS=${WORKERS:-0}

# camptocamp variables (to be used on cloud deployments)
# Sessions in Redis
ARG ODOO_SESSION_REDIS
ARG ODOO_SESSION_REDIS_HOST
ARG ODOO_SESSION_REDIS_PASSWORD
ARG ODOO_SESSION_REDIS_PREFIX
# JSON logging
ARG ODOO_LOGGING_JSON
# Attachments in the Object Storage S3
ARG AWS_HOST
ARG AWS_REGION
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_BUCKETNAME
# Metrics (Statsd/Prometheus for Grafana)
ARG ODOO_STATSD
ARG STATSD_CUSTOMER
ARG STATSD_ENVIRONMENT
ARG STATSD_HOST
ARG STATSD_PORT
# Automatic Configuration Startup checks
ARG ODOO_CLOUD_PLATFORM_UNSAFE
ARG RUNNING_ENV

ENV \
    ODOO_SESSION_REDIS=${ODOO_SESSION_REDIS:-0} \
    ODOO_SESSION_REDIS_HOST=${ODOO_SESSION_REDIS_HOST} \
    ODOO_SESSION_REDIS_PASSWORD=${ODOO_SESSION_REDIS_PASSWORD} \
    ODOO_SESSION_REDIS_PREFIX=${ODOO_SESSION_REDIS_PREFIX} \
    ODOO_LOGGING_JSON=${ODOO_LOGGING_JSON:-0} \
    AWS_HOST=${AWS_HOST} \
    AWS_REGION=${AWS_REGION} \
    AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
    AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
    AWS_BUCKETNAME=${AWS_BUCKETNAME} \
    ODOO_STATSD=${ODOO_STATSD} \
    STATSD_CUSTOMER=${STATSD_CUSTOMER} \
    STATSD_ENVIRONMENT=${STATSD_ENVIRONMENT} \
    STATSD_HOST=${STATSD_HOST} \
    STATSD_PORT=${STATSD_PORT} \
    RUNNING_ENV=${RUNNING_ENV}

# Define all needed directories
ENV ODOO_RC ${ODOO_RC:-/etc/odoo/odoo.conf}
ENV ODOO_DATA_DIR ${ODOO_DATA_DIR:-/var/lib/odoo/data}
ENV ODOO_LOGS_DIR ${ODOO_LOGS_DIR:-/var/lib/odoo/logs}
ENV ODOO_EXTRA_ADDONS ${ODOO_EXTRA_ADDONS:-/mnt/extra-addons}
ENV ODOO_ADDONS_BASEPATH ${ODOO_BASEPATH}/addons
ENV ODOO_CMD ${ODOO_BASEPATH}/odoo-bin

RUN mkdir -p ${ODOO_DATA_DIR} ${ODOO_LOGS_DIR} ${ODOO_EXTRA_ADDONS} /etc/odoo/

# Own folders    //-- docker-compose creates named volumes owned by root:root. Issue: https://github.com/docker/compose/issues/3270
RUN chown -R ${ODOO_USER}:${ODOO_USER} ${ODOO_DATA_DIR} ${ODOO_LOGS_DIR} ${ODOO_EXTRA_ADDONS} ${ODOO_BASEPATH} /etc/odoo

VOLUME ["${ODOO_DATA_DIR}", "${ODOO_LOGS_DIR}", "${ODOO_EXTRA_ADDONS}"]

ARG EXTRA_ADDONS_PATHS
ENV EXTRA_ADDONS_PATHS ${EXTRA_ADDONS_PATHS}

ARG EXTRA_MODULES
ENV EXTRA_MODULES ${EXTRA_MODULES}

COPY --chown=${ODOO_USER}:${ODOO_USER} --from=builder /usr/local /usr/local
COPY --chown=${ODOO_USER}:${ODOO_USER} --from=builder /opt/odoo ${ODOO_BASEPATH}

# Copy from build env
COPY --chown=${ODOO_USER}:${ODOO_USER} ./resources/entrypoint.sh /
COPY --chown=${ODOO_USER}:${ODOO_USER} ./resources/getaddons.py /

# This is needed to fully build with modules and python requirements
# Copy custom modules from the custom folder, if any.
ARG HOST_CUSTOM_ADDONS
ENV HOST_CUSTOM_ADDONS ${HOST_CUSTOM_ADDONS:-./custom}
COPY --chown=${ODOO_USER}:${ODOO_USER} ${HOST_CUSTOM_ADDONS} ${ODOO_EXTRA_ADDONS}

RUN chmod u+x /entrypoint.sh

EXPOSE 8069 8071 8072

# Docker healthcheck command
HEALTHCHECK CMD curl --fail http://127.0.0.1:8069/web_editor/static/src/xml/ace.xml || exit 1

ENTRYPOINT ["/entrypoint.sh"]

USER ${ODOO_USER}

CMD ["/opt/odoo/odoo-bin"]