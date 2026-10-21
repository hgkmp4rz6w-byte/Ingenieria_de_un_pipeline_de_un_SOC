# Guía del instructor

## Antes del evento

Preparar la imagen y ensayar en una máquina Linux x86_64 con los recursos de la
convocatoria. Ejecutar solución, pruebas, e2e y medir con `stats`. Confirmar que
funciona sin Internet. Distribuir el repositorio y la imagen antes del evento;
no depender del Wi-Fi del recinto. Separar el tar de Docker del ZIP de fuentes.

La carpeta de entrega debe iniciar sin `runtime/`: así cada alumno recibe los
ejercicios, aunque la solución permanezca disponible como ayuda. No enviar tus
archivos de runtime con respuestas ya instaladas. No hacen falta cuentas cloud,
credenciales del banco ni registros corporativos.

## Puntos de control

En minuto 25: todos pueden explicar el contrato. En minuto 50: extracción lista.
En minuto 70: reglas individuales listas. En minuto 90: correlación validada.
En minuto 110: pruebas reales terminadas.

Si alguien se atasca, comparar sólo la parte correspondiente en `solutions/`.
Para recuperar todo: `python3 scripts/lab.py solution`, seguido de `apply`.
Este comando respalda el trabajo previo. Después pedir que explique qué cambió.

## Demostraciones útiles

1. Decoder padre sin hijo: el evento se reconoce, pero no extrae campos.
2. Regla individual sin correlación: hay fallos, pero no señal agregada.
3. Cinco IP distintas: la cantidad sola no basta para disparar la hipótesis.
4. Evento malformado: demostrar que llegó aunque no produjo alerta.
5. Misma cuenta/IP/servicio: verificar la quinta observación y el mapeo MITRE.

## Evaluación

El participante entrega los dos XML y `e2e.json`. Debe justificar campos,
agrupación, ventana temporal y al menos un posible falso positivo. El éxito de
la suite no demuestra cobertura de ataques reales ni robustez ante cualquier log.

## Antes de publicar

Elegir licencia y propietario; revisar nombres y contenido; añadir enlace real
del repositorio a la convocatoria; adjuntar imagen exportada y su SHA-256 como
activo de release; completar el ensayo Linux nativo. Las automatizaciones CI
no están configuradas para evitar anunciar validación que todavía no ocurrió.
