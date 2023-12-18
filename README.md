<br>
<div align="center">
  <a href="https://github.com/dued/dued">
    <img src="https://raw.githubusercontent.com/dued/co-data/master/static/dued_logo.svg" alt="Dued Logo" height="60">
  </a>

<h3 align="center">Dispositivo Unificado de Economia Digital</h3>

  <p align="center">
    <a href="https://hub.docker.com/r/dued" target="_blank">Docker Hub</a> - 
    <a href="https://github.com/dued/dued">Referencia</a>  </p>

</div>

<!-- Ver la chuleta Dued Andamio en NCGApple-Notes  -->

[![Dued Provision](https://github.com/dued/andamio/actions/workflows/provision.yaml/badge.svg)](https://github.com/dued/andamio/actions/workflows/provision.yaml)

# Dued Andamio

Planteamos el Problema con la imagen oficial de Odoo en kubernetes: Odoo lanza
regularmente nuevas [imágenes de Docker](https://github.com/odoo/docker) y las
publica en [Docker Hub](https://hub.docker.com/_/odoo). Estas imágenes facilitan
la instalación y prueban Odoo rápidamente. Sin embargo, para uso en producción
dockerizada, se requieren algunos ajustes y ajustes de configuración:

- **Configuración de volúmenes** para archivos persistentes
- **Etiquetas de imagen inmutables** para garantizar implementaciones
  reproducibles
- _Regeneración inteligente_ de paquetes de activos

**la solución**: Con un enfoque ampliatorio es hacer modificaciones sustanciales
a la construcción oficial y probarla en nuestro entorno local de desarrollo (en
este caso de desarrollo de contenedor no de odoo como aplicación si se entiende)
