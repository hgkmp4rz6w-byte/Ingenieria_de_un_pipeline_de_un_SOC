# Manual del participante — Ingeniería de un pipeline SOC

**De la telemetría a la detección de amenazas · Taller de 120 minutos**  
**Instructor:** Yoshihito Adachi · TeUno  
**Entorno del laboratorio:** Linux x86_64, Docker Compose y Wazuh Manager 4.14.1.

Al finalizar tendrás un decoder que extrae campos de autenticación, una regla que detecta fallos repetidos y evidencia de que la detección funciona a través del pipeline. Trabajarás con eventos sintéticos de un portal ficticio: no necesitas atacar equipos ni usar credenciales reales.

Este manual se guarda en `docs/06-manual-participante.md`. Todos los comandos se ejecutan **desde la raíz de `soc-pipeline-lab`**, no desde `docs/`. Los bloques de terminal son comandos; los bloques XML se editan en el archivo indicado. Las soluciones están plegadas para que puedas intentar cada ejercicio antes de consultarlas.

## Índice

1. [Preparación antes del taller](#1-preparación-antes-del-taller)
2. [Arrancar y reconocer el entorno](#2-arrancar-y-reconocer-el-entorno)
3. [Entender el evento](#3-entender-el-evento)
4. [Extraer y normalizar campos](#4-extraer-y-normalizar-campos)
5. [Validar el parser y crear reglas individuales](#5-validar-el-parser-y-crear-reglas-individuales)
6. [Construir la correlación](#6-construir-la-correlación)
7. [Probar el pipeline completo](#7-probar-el-pipeline-completo)
8. [Guardar evidencia y cerrar](#8-guardar-evidencia-y-cerrar)
9. [Extensión de ventana temporal](#9-extensión-de-ventana-temporal)
10. [Resolver problemas](#10-resolver-problemas)

## Agenda de la sesión

La preparación se realiza antes de la sesión. Los tiempos incluyen explicación, práctica y revisión conjunta.

| Minutos | Actividad | Punto de control |
|---|---|---|
| 0–10 | Arranque | Manager disponible |
| 10–25 | Recorrido del evento | Fuente y campos comprendidos |
| 25–45 | Decoder | Seis campos extraídos |
| 45–60 | Parser y reglas individuales | FAIL y SUCCESS diferenciados |
| 60–80 | Correlación | Quinto fallo detectado |
| 80–105 | Pruebas completas | Siete escenarios aprobados |
| 105–120 | Evidencia y discusión | Trabajo guardado y limitaciones explicadas |

## 1. Preparación antes del taller

### 1.1 Comprobar los requisitos

- Laptop con 16 GB de RAM, 4 núcleos y 50 GB libres, conforme a la convocatoria.
- Linux x86_64 nativo o en una VM; Ubuntu 24.04 LTS es la referencia.
- Si usas una VM, comienza asignándole 6 GB de RAM y 2 vCPU.
- Docker Engine con Compose v2, Python 3.9 o posterior y un editor de texto.
- Permiso para usar Docker. Si ya funciona con tu usuario, no ejecutes el laboratorio con `sudo`.
- Internet para la preparación inicial, o la imagen exportada entregada por el instructor.

El contenedor tiene límites de 4 GB de RAM y 2 CPU. Son límites configurados, no una garantía de consumo o rendimiento. La plataforma principal es Linux x86_64; equipos ARM necesitan un ensayo específico.

### 1.2 Abrir la carpeta

Descarga o copia la carpeta completa entregada por el instructor. Abre una terminal dentro de `soc-pipeline-lab` y ejecuta:

```bash
pwd
ls
python3 --version
docker --version
docker compose version
```

**Resultado esperado:** ves `README.md`, `scripts/`, `docs/`, `exercises/`, `solutions/`, `fixtures/` y el archivo de Compose. Los tres programas muestran su versión. No continúes desde una carpeta que no contenga `scripts/lab.py`.

### 1.3 Preparar con Internet

Ejecuta cada comando por separado. Si falla uno, resuelve el error antes de continuar.

```bash
python3 scripts/lab.py doctor
python3 scripts/lab.py prepare
python3 scripts/lab.py up
python3 scripts/lab.py validate
```

`doctor` revisa prerrequisitos y crea los archivos de trabajo si faltan. `prepare` construye la imagen. `up` inicia el manager y espera que esté disponible. `validate` comprueba la configuración; **no significa que ya hayas resuelto los ejercicios**.

**Resultado esperado:** imagen preparada, manager disponible y configuración aceptada. La primera descarga puede tardar; hazla antes del taller.

### 1.4 Alternativa sin Internet

Si recibiste `soc-pipeline-manager.tar`, colócalo en `dist/` dentro del proyecto y ejecuta:

```bash
python3 scripts/lab.py doctor
python3 scripts/lab.py load
python3 scripts/lab.py up
python3 scripts/lab.py validate
```

Usa esta alternativa en lugar de `prepare`. `up` no descarga ni construye imágenes: una imagen faltante se debe resolver con `prepare` o `load`.

## 2. Arrancar y reconocer el entorno

### 2.1 Iniciar la sesión

```bash
python3 scripts/lab.py up
python3 scripts/lab.py validate
python3 scripts/lab.py stats
```

**Punto de control:** el manager está disponible y puedes consultar sus recursos. `up` conserva el trabajo previo; no reinicia los ejercicios a su estado inicial.

### 2.2 Entender qué está instalado

```text
Eventos sintéticos
      |
      v
runtime/input/auth.log
      |
      v
Wazuh logcollector -> decoder -> reglas individuales -> correlación
                                                              |
                                                              v
                                                         alerts.json
```

El motor corre en un contenedor. No se incluyen indexador, dashboard, una VM Windows ni un agente adicional. Los archivos de eventos y las herramientas de terminal permiten observar el análisis. `archives.json` permite comprobar la ingesta incluso cuando no se genera una alerta.

### 2.3 Abrir los archivos de trabajo

Abre estos archivos en tu editor:

```text
runtime/decoders/local_decoder.xml
runtime/rules/local_rules.xml
```

Trabaja en `runtime/`. `exercises/` conserva las plantillas y `solutions/` contiene las respuestas. No edites las respuestas para resolver el ejercicio.

## 3. Entender el evento

### 3.1 Leer un registro

```bash
cat fixtures/one-failure.log
```

El formato del evento es:

```text
lab-auth: ts=2026-10-23T16:30:00Z user=ana src=192.0.2.10 result=FAIL service=portal run=ejercicio1
```

Alguien intentó autenticarse como `ana` desde `192.0.2.10` en `portal` y falló. El identificador `run` separa un ensayo de otro.

### 3.2 Acordar el significado de los campos

| Entrada | Campo de Wazuh | Significado |
|---|---|---|
| `ts` | `event_time` | Fecha del evento conservada como texto |
| `user` | `dstuser` | Cuenta a la que se intenta acceder |
| `src` | `srcip` | IPv4 de origen |
| `result` | `status` | Resultado FAIL o SUCCESS |
| `service` | `service` | Aplicación |
| `run` | `run_id` | Ensayo del laboratorio |

`dstuser`, `srcip` y `status` son campos estáticos de Wazuh. Los demás se extraen como campos dinámicos. Llamar a un campo `ip` no le da automáticamente el significado de `srcip`.

**Punto de control:** explica qué representa cada campo y cuál usarías para agrupar intentos dirigidos a la misma cuenta.

## 4. Extraer y normalizar campos

### 4.1 Observar el estado inicial

```bash
python3 scripts/lab.py logtest < fixtures/one-failure.log
```

La plantilla reconoce la fuente `lab-auth`, pero aún no extrae los seis campos. Esta carencia es intencional. No esperes que las pruebas funcionales completas pasen todavía.

### 4.2 Completar el decoder

En `runtime/decoders/local_decoder.xml`, conserva el decoder padre y agrega un hijo con:

1. `parent` igual a `lab-auth`.
2. Una expresión regular de tipo `pcre2` con seis grupos de captura.
3. `order` con los nombres del contrato de campos, en ese mismo orden.
4. Anclas de inicio y final para exigir el formato completo.

<details>
<summary>Ver solución del decoder</summary>

El contenido funcional completo del archivo es:

```xml
<decoder name="lab-auth">
  <prematch>^lab-auth: </prematch>
</decoder>
<decoder name="lab-auth-fields">
  <parent>lab-auth</parent>
  <regex type="pcre2">^lab-auth: ts=(\S+) user=([A-Za-z0-9_.-]+) src=((?:\d{1,3}\.){3}\d{1,3}) result=(FAIL|SUCCESS) service=([A-Za-z0-9_-]+) run=([A-Za-z0-9_-]+)$</regex>
  <order>event_time,dstuser,srcip,status,service,run_id</order>
</decoder>
```

Conserva la expresión regular en una sola línea. El grupo `(?:...)` no captura: sirve para repetir el patrón de la IP sin desplazar los seis campos. Esta expresión reconoce la forma de una IPv4, pero no valida que cada octeto sea menor o igual a 255. El tiempo se conserva como texto, sin validación semántica de fecha.

</details>

### 4.3 Cargar y probar

Guarda el archivo y ejecuta:

```bash
python3 scripts/lab.py apply
python3 scripts/lab.py logtest < fixtures/one-failure.log
```

**Resultado esperado:** la fase de decodificación muestra los seis campos, incluidos `dstuser=ana`, `srcip=192.0.2.10` y `status=FAIL`. La regla base puede continuar en nivel 0: todavía no has creado las detecciones.

**Punto de control:** no avances si la IP o el usuario faltan o están intercambiados.

## 5. Validar el parser y crear reglas individuales

### 5.1 Probar un evento incompleto

```bash
cat fixtures/malformed.log
python3 scripts/lab.py logtest < fixtures/malformed.log
```

El registro no tiene IP. **Resultado esperado:** se reconoce la fuente, pero no se extrae como autenticación válida. Un parser útil también rechaza entradas que no cumplen el contrato.

### 5.2 Crear las reglas de fallo y éxito

En `runtime/rules/local_rules.xml`, conserva la regla base `100100`. Agrega dentro del mismo `<group>`:

- `100101`, nivel 3, hija de `100100`, para `status` exactamente `FAIL`.
- `100102`, nivel 3, hija de `100100`, para `status` exactamente `SUCCESS`.
- Una descripción que incluya usuario e IP.

<details>
<summary>Ver reglas individuales</summary>

Inserta estas reglas antes del cierre `</group>`. No dupliques reglas con el mismo ID.

```xml
<rule id="100101" level="3">
  <if_sid>100100</if_sid>
  <status>^FAIL$</status>
  <description>Fallo de autenticacion: $(dstuser) desde $(srcip).</description>
  <group>authentication_failed,</group>
</rule>
<rule id="100102" level="3">
  <if_sid>100100</if_sid>
  <status>^SUCCESS$</status>
  <description>Autenticacion correcta: $(dstuser) desde $(srcip).</description>
  <group>authentication_success,</group>
</rule>
```

</details>

### 5.3 Probar ambos resultados

```bash
python3 scripts/lab.py apply
python3 scripts/lab.py logtest < fixtures/one-failure.log
python3 scripts/lab.py logtest < fixtures/one-success.log
python3 scripts/lab.py logtest < fixtures/malformed.log
```

**Resultado esperado:** fallo → `100101`; éxito → `100102`; evento incompleto → ninguna de esas dos reglas. Las reglas individuales son de nivel 3 y pueden generar alertas; eso no equivale a haber disparado la correlación.

## 6. Construir la correlación

### 6.1 Formular la hipótesis

> Cinco fallos de autenticación en 60 segundos, con la misma IP, cuenta y servicio, son un patrón que queremos investigar.

La alerta indica posible adivinación de contraseñas, no demuestra por sí sola un compromiso. Se asocia a MITRE ATT&CK `T1110.001`. Un error repetido de un usuario legítimo también puede producir este patrón.

### 6.2 Agregar la regla

En el mismo grupo de `runtime/rules/local_rules.xml`, agrega `100110` con nivel 10, `frequency="5"` y `timeframe="60"`. El antecedente es `100101`.

Agrupa por IP, usuario, servicio y `run_id`. Este último campo es una separación artificial entre ensayos; no es una recomendación de clave para una detección de producción.

<details>
<summary>Ver regla de correlación</summary>

Inserta antes de `</group>`:

```xml
<rule id="100110" level="10" frequency="5" timeframe="60">
  <if_matched_sid>100101</if_matched_sid>
  <same_srcip />
  <same_user />
  <same_field>service</same_field>
  <same_field>run_id</same_field>
  <description>Posible adivinacion de contrasenas: $(dstuser) desde $(srcip) en $(service).</description>
  <mitre><id>T1110.001</id></mitre>
  <group>authentication_failures,</group>
</rule>
```

`if_sid` clasifica el evento actual a partir de otra regla. `if_matched_sid` utiliza coincidencias anteriores para correlacionar. En este laboratorio `same_user` se usa con la cuenta extraída en `dstuser`; las pruebas verifican que usuarios diferentes no se mezclen.

</details>

### 6.3 Ejecutar la suite del motor

```bash
python3 scripts/lab.py apply
python3 scripts/lab.py test
```

**Resultado esperado:** siete casos aprobados. La suite verifica que la correlación aparezca exactamente en el quinto fallo del caso positivo.

Cada escenario utiliza una sesión de `logtest` con estado compartido entre sus eventos. Si abres una sesión nueva por cada línea, no acumulas los antecedentes necesarios. Estas pruebas no introducen eventos en el archivo monitorizado ni escriben las alertas del pipeline real.

## 7. Probar el pipeline completo

### 7.1 Abrir una vista de alertas

En una segunda terminal, ubicada también en la raíz del proyecto:

```bash
python3 scripts/lab.py alerts
```

La vista muestra las últimas alertas y continúa siguiendo las nuevas. Puede incluir resultados anteriores: identifica el `run_id` de la ejecución que estás revisando.

### 7.2 Generar una secuencia controlada

En la primera terminal:

```bash
python3 scripts/lab.py replay --case attack
```

Este comando escribe cinco fallos en `runtime/input/auth.log`. Espera a que Wazuh procese los eventos. Busca en la otra terminal la regla `100110`, nivel 10, con usuario `ana`, IP `192.0.2.10`, servicio `portal` y técnica `T1110.001`.

**Punto de control:** anota el `run_id` mostrado por el ensayo y relaciónalo con la alerta. La estructura JSON puede separar datos estáticos y dinámicos; identifica los valores, no presupongas que todos estarán en la misma ubicación.

### 7.3 Ejecutar las pruebas completas

```bash
python3 scripts/lab.py e2e
```

| Caso | Entrada | ¿Debe aparecer 100110? |
|---|---|---|
| `attack` | 5 fallos de la misma IP, cuenta y servicio | Sí, en el quinto |
| `below` | 4 fallos | No |
| `success` | 5 éxitos | No |
| `different-ip` | 5 fallos con IP diferentes | No |
| `different-user` | 5 fallos con cuentas diferentes | No |
| `different-service` | 5 fallos con servicios diferentes | No |
| `malformed` | 5 registros sin IP | No |

**Resultado esperado:** siete casos aprobados y evidencia en `runtime/evidence/e2e.json`. La suite confirma la llegada de los eventos antes de aceptar un resultado negativo. Los fallos y éxitos individuales pueden seguir generando alertas de nivel 3; la columna pregunta únicamente por `100110`.

### 7.4 Inspeccionar evidencia

```bash
cat runtime/evidence/e2e.json
ls runtime/evidence
```

Para observar la ingesta, puedes abrir otra terminal y ejecutar:

```bash
python3 scripts/lab.py archives
```

Usa `Ctrl+C` para cerrar las vistas `alerts` o `archives`; esto no detiene el manager. Una ausencia de alerta solo es un resultado válido si sabes que los eventos llegaron.

## 8. Guardar evidencia y cerrar

### 8.1 Verificar tu entrega

- [ ] El decoder extrae los seis campos.
- [ ] Un registro sin IP no dispara las reglas de autenticación.
- [ ] FAIL y SUCCESS producen las reglas individuales correctas.
- [ ] `test` aprueba los siete escenarios.
- [ ] `e2e` aprueba los siete escenarios.
- [ ] Puedo relacionar una alerta 100110 con su cuenta, IP, servicio y ensayo.
- [ ] Puedo explicar un falso positivo y una limitación de la regla.

### 8.2 Crear una copia del trabajo

```bash
mkdir -p entrega
cp runtime/decoders/local_decoder.xml entrega/
cp runtime/rules/local_rules.xml entrega/
cp runtime/evidence/e2e.json entrega/
cp runtime/evidence/logtest-*.txt entrega/
```

Los comandos presuponen que completaste ambas suites. `entrega/` es una copia local para conservar o entregar al instructor; no la agregues automáticamente al repositorio público.

### 8.3 Discutir los resultados

1. ¿Qué ocurre si el atacante cambia de IP o de cuenta?
2. ¿Qué cambia cuando varios usuarios comparten una IP NAT?
3. ¿Qué pasa si el portal cambia el orden de sus campos?
4. ¿Un acceso exitoso posterior demuestra que hubo compromiso?
5. ¿Qué información adicional pedirías antes de escalar la alerta?

### 8.4 Detener el laboratorio

Después de guardar tu evidencia:

```bash
python3 scripts/lab.py down
```

El comando elimina el contenedor y sus volúmenes anónimos, incluidas las alertas internas. Conserva los XML, los eventos de entrada y las evidencias exportadas en `runtime/`. La copia de `entrega/` también permanece.

## 9. Extensión de ventana temporal

Realiza esta extensión si queda tiempo o como práctica posterior, con el manager iniciado y la solución aplicada.

```bash
python3 scripts/lab.py replay --case attack --interval 16
```

Los cinco fallos separados 16 segundos abarcan más de 60 segundos. La ejecución tarda aproximadamente 80 segundos. **Resultado esperado:** los cinco eventos llegan, pero ese `run_id` no produce `100110`.

Comprueba la llegada en `archives` y busca ese mismo identificador en `alerts`. No confundas alertas de un ensayo anterior con el actual. Cambiar únicamente `ts` en el texto del evento no prueba esta ventana: `event_time` se conserva como texto y el ensayo debe respetar los intervalos reales de procesamiento.

## 10. Resolver problemas

### Docker no está disponible o no tengo permiso

```bash
python3 scripts/lab.py doctor
```

Comprueba que Docker esté iniciado y que tu usuario pueda usarlo. Resuelve los permisos con el instructor antes de continuar; no cambies arbitrariamente propietarios ni permisos de todo el proyecto.

### El manager no arranca

```bash
python3 scripts/lab.py logs
```

Si falta la imagen, usa `prepare` con Internet o `load` con el archivo entregado. Si el error menciona XML, revisa los archivos de `runtime/`. En ARM, la emulación puede aumentar el tiempo de inicio.

### apply rechaza el XML

Revisa etiquetas de apertura y cierre, comillas, IDs duplicados y ubicación de las reglas dentro de `<group>`. Corrige el archivo y vuelve a ejecutar `apply`.

Si Wazuh rechaza la configuración, `apply` restaura los XML anteriores dentro del contenedor; tu archivo incorrecto sigue en `runtime/` para que puedas corregirlo. No reinicies antes de corregirlo, porque el arranque vuelve a cargar esos archivos.

### logtest funciona pero no veo alertas reales

`logtest` prueba el análisis directamente; no escribe a `alerts.json`. Ejecuta `replay` después de que el manager esté listo. El recolector puede omitir contenido que ya existía antes del arranque.

Comprueba en este orden:

1. El evento está en `runtime/input/auth.log`.
2. El evento llegó a `archives`.
3. El decoder extrae los campos con `logtest`.
4. Guardaste los cambios y ejecutaste `apply`.
5. Los cinco fallos comparten IP, cuenta, servicio y `run_id` y entraron dentro de la ventana.
6. Estás buscando la regla `100110` y el ensayo correcto en `alerts`.

### Necesito recuperar el ritmo de la clase

Con ayuda del instructor, puedes cargar la solución completa:

```bash
python3 scripts/lab.py solution
python3 scripts/lab.py apply
python3 scripts/lab.py test
python3 scripts/lab.py e2e
```

`solution` reemplaza tus XML de trabajo y antes guarda una copia en `runtime/backups/`. Utiliza esta opción como recuperación; revisa después qué cambió para comprender la detección.

## Referencias y alcance

- [Guía de ejercicios](02-ejercicios.md)
- [Operación y diagnóstico](04-operacion.md)
- [Estado de validación del laboratorio](05-validacion.md)
- [Sintaxis de reglas de Wazuh](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html)
- [Pruebas de reglas y decoders](https://documentation.wazuh.com/current/user-manual/ruleset/testing.html)
- [MITRE ATT&CK Password Guessing](https://attack.mitre.org/techniques/T1110/001/)

El manual corresponde a la versión fijada del laboratorio. Las pruebas registradas se ejecutaron en macOS ARM con un contenedor Linux amd64 emulado; antes de la sesión presencial se debe completar el ensayo nativo en Linux x86_64 y la importación sin Internet en un segundo equipo. Este entorno enseña el tramo de análisis y detección de un SOC; no es un despliegue de SIEM completo para producción.
