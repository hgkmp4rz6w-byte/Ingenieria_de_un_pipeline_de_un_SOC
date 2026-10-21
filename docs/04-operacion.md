# Operación y diagnóstico

## Comandos

| Comando (`python3 scripts/lab.py …`) | Efecto |
|---|---|
| doctor | Consulta Docker, Compose, arquitectura y espacio |
| prepare | Construye la imagen; requiere Internet en la primera preparación |
| up | Arranca la imagen existente y espera salud del manager |
| apply | Copia XML, valida y reinicia para activar cambios |
| validate | Comprueba configuración con binarios de Wazuh |
| logtest | Lee eventos de stdin, sin ingresarlos al pipeline |
| test | Ejecuta 7 casos en el motor de reglas |
| replay --case attack | Escribe eventos al archivo monitorizado |
| e2e | Prueba 7 casos reales y exporta evidencias |
| alerts / archives | Sigue salida JSON; Ctrl+C termina la vista |
| logs / stats | Diagnóstico del contenedor / recursos actuales |
| solution | Respalda trabajo y copia solución; requiere apply después |
| export / load | Guarda o carga imagen offline en dist/ |
| down | Elimina este entorno y volúmenes anónimos; conserva runtime |

## Si no arranca

Ejecutar `doctor` y `logs`. Verificar Docker activo y que el usuario pueda usarlo.
Si falta la imagen, ejecutar `prepare` con conexión o `load` con el tar recibido.
`up` falla intencionalmente si falta una imagen preparada. En ARM la emulación
puede tardar más; la plataforma principal del taller es Linux x86_64.

## Si apply rechaza XML

Corregir `runtime/`. El comando restaura los XML anteriores dentro del contenedor
si analysisd los rechaza. No reiniciar hasta corregirlos: el arranque vuelve a
copiar los archivos de runtime. Los errores se muestran en la terminal.

## Si no aparece una alerta

Comprobar, en orden: archivo `runtime/input/auth.log`, `archives`, decoder con
`logtest`, reglas cargadas con `apply`, y finalmente `alerts`. Logtest prueba el
análisis pero no escribe a alerts.json. El replay debe ejecutarse después de que
el manager esté listo: logcollector puede omitir contenido previo al arranque.

La suite usa `run_id` diferentes para no mezclar ensayos; un editor manual debe
conservar un mismo valor dentro de la secuencia que pretende correlacionar.
No usar la ausencia de alerta como prueba negativa sin confirmar ingesta.

## Datos y reinicio

`down` elimina alertas y archivos internos del contenedor. Exportar primero las
evidencias necesarias. `runtime/input/auth.log` y los XML permanecen en el host.
Los contenedores del laboratorio no se reinician automáticamente al encender
Docker. No se modifican otros proyectos ni se ejecuta docker system prune.

## Publicación

El repositorio contiene exclusivamente datos sintéticos e IP de documentación.
No publicar runtime ni archivos tar. La imagen base está fijada por versión;
actualizarla exige repetir las pruebas y revisar compatibilidad del arranque.

Si modificas `config/ossec.conf`, recrea el contenedor con
`docker compose up -d --force-recreate --no-build --pull never` y luego ejecuta
`python3 scripts/lab.py up`. Algunos editores sustituyen el archivo por otro inode;
un simple restart puede conservar el montaje anterior. Esto no afecta los XML
de ejercicios, que se montan como directorios.
