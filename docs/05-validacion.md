# Estado de validación

## Entorno

Fecha: 20 de octubre de 2026 en America/Guayaquil (21 de octubre UTC).
Host macOS ARM64, Docker Linux aarch64, contenedor Linux amd64 bajo emulación.
Wazuh Manager 4.14.1. Imagen base fijada por versión y digest:

```text
sha256:a6df0df2831ad80d3d390626b1fd1d14fc91429b7196fe9df189d96899209e33
```

## Comprobaciones realizadas

- Imagen derivada construida y manager arrancado.
- Configuración aceptada por analysisd y logcollector.
- Siete escenarios de logtest aprobados; quinto fallo verificado exactamente.
- Siete escenarios del pipeline real aprobados, con 34 eventos de entrada.
- Para todos los negativos, ingesta confirmada en archives.json.
- Alerta 100110 con usuario, IP y MITRE T1110.001 comprobados.
- Prueba temporal adicional: cinco fallos separados 16 segundos, ingesta de los
  cinco confirmada, sin correlación fuera de la ventana de 60 segundos.
- Compilación del script Python y lectura de XML correctas.
- Enlaces locales de las guías comprobados.
- Ejercicios iniciales y comando apply probados: reconocen lab-auth con regla
  100100 de nivel 0, sin entregar los campos ni la detección ya resueltos.

Las evidencias sintéticas se conservan en `validation/`; no contienen datos de
equipos monitorizados ni credenciales. `runtime/` se excluye de la entrega limpia.

## Recursos observados

Una captura de `docker stats` después de las pruebas mostró **411 MiB / 4 GiB** y
45,63 % de CPU. No es un promedio, un máximo ni un benchmark. Excluye el coste de
Docker Desktop y del sistema anfitrión; no reemplaza el ensayo con las laptops.

## Pendientes y observaciones

- Ensayo nativo en Linux x86_64 con 16 GB RAM, 4 núcleos y 50 GB libres.
- Ensayo de distribución/importación del tar en un segundo equipo sin Internet.
- Algunas advertencias de Inventory Harvester/IndexerConnector aparecen aunque
  el indexador y la recolección de inventario están deshabilitados. No impidieron
  las pruebas; no hay indexador en esta variante. Los módulos internos de Wazuh
  pueden iniciarse aunque sus funciones de recolección estén deshabilitadas.
- Esta entrega no constituye una validación de producción ni de todas las
  arquitecturas posibles de los asistentes.
