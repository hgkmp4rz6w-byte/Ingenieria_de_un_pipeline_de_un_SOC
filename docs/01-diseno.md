# Diseño del taller

## Resultado observable

El participante entrega un decoder, reglas XML y evidencias de que un conjunto
de eventos entró al pipeline y activó la alerta esperada. También demuestra que
eventos de control no activan la correlación. Reconocer una fuente no equivale a
extraer sus campos; pasar logtest no demuestra que logcollector esté leyendo.

## Caso narrativo

La aplicación ficticia `portal` registra accesos. El SOC observa fallos repetidos
sobre una cuenta desde una misma IP. Se sospecha adivinación de contraseñas.
El ejercicio reproduce registros, no realiza intentos de acceso a sistemas.

Hipótesis: cinco fallos para la misma combinación de IP, usuario y servicio,
procesados dentro de 60 segundos, merecen investigación. `run_id` separa ensayos
del laboratorio. MITRE T1110.001 describe la conducta hipotética; una etiqueta
no prueba intención maliciosa ni cobertura completa de la técnica.

## Agenda: 120 minutos

| Minutos | Actividad | Evidencia |
|---|---|---|
| 0–10 | Objetivo, arquitectura y comprobación de entorno | Manager disponible |
| 10–25 | Leer log crudo y acordar contrato de campos | Tabla de campos |
| 25–50 | Construir decoder y probar datos imperfectos | Campos en logtest |
| 50–70 | Reglas de fallo y éxito individuales | IDs 100101 / 100102 |
| 70–90 | Correlación y mapeo MITRE | ID 100110 en el quinto fallo |
| 90–110 | Pruebas positivas y negativas en el pipeline | e2e.json |
| 110–120 | Falsos positivos, limitaciones y cierre | Explicación de resultados |

La descarga y la instalación de Docker son trabajo previo. Reservar un equipo
preparado o trabajo por parejas para quienes no completen la preparación.

## Decisiones para limitar recursos

Un manager por participante, sin indexador ni dashboard. Se desactivan inventario,
SCA, FIM, rootcheck, vulnerabilidades y respuesta activa. No hay servicio externo
necesario durante la sesión. La lectura de JSON hace visible la salida del motor.
Conservar archivos de archivo completo es útil aquí, pero aumenta almacenamiento;
la configuración no es una recomendación de retención para producción.

## Alcance y límites

- Telemetría ya disponible: se reproduce en un archivo monitorizado.
- Formato textual propio, estable y deliberadamente sencillo.
- Normalización al esquema de Wazuh, no a ECS ni OCSF.
- IPv4 solamente; regex de estructura, sin validación de rango de octetos.
- El campo `event_time` conserva el tiempo de origen. No redefine el reloj de
  correlación: espaciar timestamps en texto no reemplaza esperar tiempo real.
- La regla no detecta por sí sola password spraying ni ataques distribuidos.
- `run_id` es una clave de aislamiento pedagógica. En producción se elimina o
  sustituye por una dimensión auténtica y se vuelve a validar la correlación.
- La ausencia de alertas sólo se considera válida tras comprobar la ingesta.

## Preparación para GitHub

Publicar fuentes, documentación, fixtures y soluciones. Excluir runtime,
credenciales, datos reales e imágenes tar. Fijar una release del laboratorio
después de ensayarla en Linux x86_64; conservar el digest y los resultados de
validación. Decidir licencia y propietario antes de la publicación.
