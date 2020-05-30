# [Andamio](https://hub.docker.com/r/dued/andamio)

[![](https://images.microbadger.com/badges/version/dued/andamio:latest.svg)](https://microbadger.com/images/dued/andamio:latest "Get your own version badge on microbadger.com")
[![](https://images.microbadger.com/badges/image/dued/andamio:latest.svg)](https://microbadger.com/images/dued/andamio:latest "Get your own image badge on microbadger.com")
[![](https://images.microbadger.com/badges/commit/dued/andamio:latest.svg)](https://microbadger.com/images/dued/andamio:latest "Get your own commit badge on microbadger.com")
[![](https://images.microbadger.com/badges/license/dued/andamio.svg)](https://microbadger.com/images/dued/andamio "Get your own license badge on microbadger.com")
![ci](https://github.com/dued/andamio/workflows/ci/badge.svg)
![ci](https://github.com/dued/andamio/workflows/ci/badge.svg?event=deployment)
![ci](https://github.com/dued/andamio/workflows/ci/badge.svg?event=registry_package)

¡CUIDADO !, este proyecto está en etapa beta . está en dinámica de cambio de forma
constante.

## ¿Que hace andamio?

Andamio es un entorno estandarizado para su proyecto DUED. Desarrollo test y producción
con buenas prácticas y herramientas para permitir que su equipo tenga una estructura
provisional (de alli su nombre) que luego le permitirá orquestar en la nube.

## ¿Por que?

El enfoque de andamio es la infraestructura. esta pensado para trabajar con cubos
[maxive](), el andamio permite construir de forma rápida un entorno imperativo para
DUED. La idea es lograr implementaciones basadas en la migración de proyectos hacia
infraestructuras no dependientes. Andamio provee escalabilidad de una instancia de
producción y un proceso mas eficiente de adaptación.

## ¿Como lo hace?

Sobre una imagen base definimos una estructura de directorio que se configura de forma
dinámica tal que Dued pueda administrar con eficiencia todo el ciclo del proyecto.
