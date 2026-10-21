# Ejercicios del participante

Trabaja en `runtime/`, nunca en `solutions/`. Todos los comandos se ejecutan desde
la raíz del repositorio. El entorno debe estar preparado antes de comenzar.

## 1. Entender la fuente

```text
lab-auth: ts=2026-10-23T16:30:00Z user=ana src=192.0.2.10 result=FAIL service=portal run=ejercicio1
```

| Entrada | Campo Wazuh | Interpretación |
|---|---|---|
| `ts` | `event_time` | Tiempo de origen conservado como texto |
| `user` | `dstuser` | Cuenta sobre la que se intenta autenticar |
| `src` | `srcip` | IP de origen IPv4 |
| `result` | `status` | `FAIL` o `SUCCESS` |
| `service` | `service` | Aplicación que genera el evento |
| `run` | `run_id` | Identificador del ensayo |

Identifica cuáles son campos estáticos de Wazuh y cuáles son dinámicos.
Explica por qué un campo llamado `ip` no equivale automáticamente a `srcip`.

## 2. Extraer y normalizar

El decoder padre ya reconoce `lab-auth:`. Agrega un hijo con `parent`, una
expresión `regex type="pcre2"` y `order`. Usa seis grupos de captura en el orden
de la tabla. Ancla la expresión completa para evitar campos parciales.

```bash
python3 scripts/lab.py apply
python3 scripts/lab.py logtest < fixtures/one-failure.log
```

Criterio: fase 2 muestra los seis campos, con `dstuser=ana` y
`srcip=192.0.2.10`. La fase 3 puede seguir en la regla base de nivel 0.
Prueba también `fixtures/malformed.log`: debe reconocerse la fuente, pero no
interpretarse como fallo válido porque falta la IP.

## 3. Crear detecciones individuales

En `runtime/rules/local_rules.xml`, agrega:

- `100101`, nivel 3: hija de 100100, `status` exactamente `FAIL`.
- `100102`, nivel 3: hija de 100100, `status` exactamente `SUCCESS`.

Incluye una descripción con usuario e IP. Aplica cambios y prueba los archivos
`one-failure.log` y `one-success.log`. Los niveles deben permitir guardar las
alertas y mantener los fallos como antecedentes de correlación.

## 4. Correlacionar

Agrega `100110`, nivel 10, `frequency="5"`, `timeframe="60"` y antecedente
`if_matched_sid=100101`. Usa `same_srcip`, `same_user` y `same_field` para
`service` y `run_id`. Agrega el mapeo MITRE `T1110.001`.

```bash
python3 scripts/lab.py apply
python3 scripts/lab.py test
```

Se ejecuta una sesión independiente de logtest por escenario. Dentro de cada
sesión todos los eventos comparten estado. Abrir logtest para cada línea impediría
acumular antecedentes. Verifica que el quinto fallo dispara, no sólo que algún
evento de una secuencia larga lo hace.

## 5. Validar el pipeline real

```bash
python3 scripts/lab.py e2e
```

| Caso | Eventos | Correlación 100110 |
|---|---:|---|
| attack | 5 fallos, misma IP/cuenta/servicio | Sí, en el quinto |
| below | 4 fallos | No |
| success | 5 éxitos | No |
| different-ip | 5 fallos, distintas IP | No |
| different-user | 5 fallos, distintas cuentas | No |
| different-service | 5 fallos, distintos servicios | No |
| malformed | 5 registros sin IP | No |

Los fallos individuales y éxitos generan alertas de nivel 3; «No» se refiere
específicamente a la correlación de nivel 10. Los registros malformados siguen
visibles en el archivo de eventos, pero no disparan las reglas de autenticación.

La prueba comprueba que llegaron todos los eventos antes de aceptar resultados
negativos. Guarda `runtime/evidence/e2e.json`, los resultados de logtest y tus XML.

## Extensión: ventana temporal

```bash
python3 scripts/lab.py replay --case attack --interval 16
```

Cinco fallos espaciados 16 segundos abarcan más de 60 segundos: no deberían
producir 100110. Examina el `run_id` mostrado y confirma que los cinco eventos
llegaron. Esta prueba dura aproximadamente 80 segundos y no se incluye en la
suite rápida. Cambiar solamente `ts` en un archivo no comprueba esta condición.

## Preguntas de cierre

¿Qué cambia si muchos usuarios comparten una IP NAT? ¿Qué ocurre si la aplicación
cambia el orden de campos? ¿Un éxito posterior demuestra compromiso? ¿Qué datos
adicionales necesitaría el analista para investigar?
