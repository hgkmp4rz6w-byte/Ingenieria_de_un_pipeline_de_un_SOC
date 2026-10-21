# Ingeniería de un pipeline SOC

**De la telemetría a la detección de amenazas — taller práctico de 120 minutos.**

Cada participante construye y valida un decoder y una regla de correlación usando
el motor de Wazuh. El entorno se prepara antes del taller y funciona sin Internet
una vez descargada su imagen. Todos los eventos son sintéticos.

## Requisitos

- Linux x86_64, nativo o dentro de una VM; Ubuntu 24.04 LTS como referencia.
- Equipo con 16 GB de RAM, 4 núcleos y 50 GB libres, según la convocatoria.
- Docker Engine con Compose v2 y Python 3.9 o posterior. `jq` es opcional.
- Permiso para usar Docker. No ejecutar los scripts con `sudo` si Docker ya funciona.
- Para Linux en VM: asignar inicialmente 6 GB de RAM y 2 vCPU a la VM.

El contenedor tiene un límite de 4 GB de RAM y 2 CPU; estos límites no describen
consumo medido ni garantizan rendimiento. La imagen fija la arquitectura amd64.
ARM puede emularla para desarrollo; debe ensayarse por separado antes de usarlo
en clase. Ver [validación](docs/05-validacion.md).

## Arquitectura

```text
Eventos sintéticos → archivo monitorizado → Wazuh logcollector
                                             ↓
                                      decoder / campos
                                             ↓
                                regla individual / correlación
                                             ↓
                                 alerts.json + MITRE ATT&CK
```

Incluye Wazuh Manager 4.14.1, Python estándar y Compose. No necesita una VM de
Windows, un agente adicional, indexador ni dashboard. Es el segmento de análisis
y detección de un SOC; no es un SIEM completo. Los archivos `archives.json`
permiten verificar ingesta incluso cuando un evento no produce alerta.

## Antes del taller (con Internet)

Desde esta carpeta:

```bash
python3 scripts/lab.py doctor
python3 scripts/lab.py prepare
python3 scripts/lab.py up
python3 scripts/lab.py validate
```

`up` no descarga ni construye imágenes: así se detecta cualquier preparación
incompleta antes de la sesión. La primera ejecución copia los ejercicios a
`runtime/`. Los comandos posteriores conservan ese trabajo.

## Durante el taller

1. Abrir [los ejercicios](docs/02-ejercicios.md).
2. Editar `runtime/decoders/local_decoder.xml` y `runtime/rules/local_rules.xml`.
3. Ejecutar `python3 scripts/lab.py apply` para validar y cargar los cambios.
4. Ejecutar `python3 scripts/lab.py test` para las pruebas del motor.
5. Ejecutar `python3 scripts/lab.py e2e` para comprobar el pipeline real.

En otra terminal puedes observar las alertas:

```bash
python3 scripts/lab.py alerts
# Opcional, con jq instalado:
python3 scripts/lab.py alerts | jq --unbuffered '{timestamp,rule,data}'
```

## Ensayo del instructor con la solución

```bash
python3 scripts/lab.py solution
python3 scripts/lab.py up
python3 scripts/lab.py apply
python3 scripts/lab.py test
python3 scripts/lab.py e2e
python3 scripts/lab.py stats
```

`solution` respalda el trabajo anterior en `runtime/backups/` antes de copiar la
respuesta. La versión inicial contiene únicamente el reconocimiento de la
fuente; **las pruebas funcionales deben fallar hasta completar los ejercicios**.

## Distribución sin Internet

En un equipo preparado: `python3 scripts/lab.py export`. Copiar el repositorio y
`dist/soc-pipeline-manager.tar` al participante. Allí ejecutar:

```bash
python3 scripts/lab.py load
python3 scripts/lab.py up
```

El archivo de imagen es grande: distribuirlo como activo de una release o por
un medio local, no incluirlo en el historial Git. `runtime/` también está excluido.

## Guías

- [Diseño y agenda](docs/01-diseno.md)
- [Ejercicios y contrato de campos](docs/02-ejercicios.md)
- [Guía del instructor](docs/03-instructor.md)
- [Operación y diagnóstico](docs/04-operacion.md)
- [Estado de validación](docs/05-validacion.md)

Para detener: `python3 scripts/lab.py down`. Elimina el contenedor y sus volúmenes
anónimos, incluidas alertas internas. Conserva ejercicios, eventos de entrada y
evidencias exportadas en `runtime/`. No se publica ningún puerto del contenedor.

## Referencias

- [Requisitos del servidor Wazuh](https://documentation.wazuh.com/current/installation-guide/wazuh-server/index.html)
- [Pruebas de decoders y reglas](https://documentation.wazuh.com/current/user-manual/ruleset/testing.html)
- [Sintaxis de reglas](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html)
- [MITRE ATT&CK T1110.001](https://attack.mitre.org/techniques/T1110/001/)
- [Imagen oficial: código de la versión fijada](https://github.com/wazuh/wazuh-docker/tree/v4.14.1)

Este repositorio está preparado para una futura publicación, pero no incluye
licencia propia todavía. El titular debe elegirla antes de distribuirlo
públicamente; Wazuh y los demás componentes conservan sus licencias originales.
