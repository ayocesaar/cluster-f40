#!/usr/bin/env bash
# Evidencia real de los temas de la materia sobre el cluster en ejecucion (Linux).
# Uso (desde la raiz del proyecto, con el entorno activado):
#   xvfb-run -a bash tools/evidencia_so.sh
# Escribe docs/evidencias/so/*.txt. Trabaja en una carpeta temporal: no toca datos/ ni logs/.
set -u
raiz="$(cd "$(dirname "$0")/.." && pwd)"
salida="$raiz/docs/evidencias/so"
trabajo="$(mktemp -d /tmp/evidencia_so.XXXXXX)"
mkdir -p "$salida" "$trabajo/config" "$trabajo/datos"
printf '[intervalos]\nlectura_ms = 100\nrefresco_ms = 50\n' > "$trabajo/config/cluster.ini"
datos="$trabajo/datos/vehiculo.conf"
py="${PYTHON:-python}"
encabezado() { echo "== $1 =="; echo "Comando: $2"; echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S')  Kernel: $(uname -r)"; echo; }

# 1.2 Codificacion: bytes reales del archivo de datos (ASCII y un caracter de 3 bytes en UTF-8)
"$py" "$raiz/tools/escribir_dato.py" --archivo "$datos" motor=1 velocidad=120 rpm=3000 presion_aceite=5 \
    temp_agua=90 presion_turbo=0.8 > /dev/null
printf 'velocidad=\xef\xbc\x95\n' > "$trabajo/digito_no_ascii.conf"
{
    encabezado "Codificacion del archivo de datos (tema 1.2)" "hexdump -C"
    echo "-- datos/vehiculo.conf: texto ASCII, un byte por caracter; 0a es el salto de linea --"
    hexdump -C "$datos" | head -n 8
    echo
    echo "-- 'velocidad=５': el digito de ancho completo ocupa 3 bytes UTF-8 (ef bc 95); el lector lo rechaza (DEF-14) --"
    hexdump -C "$trabajo/digito_no_ascii.conf"
} > "$salida/codificacion_hexdump.txt"

# 2.1 Llamadas al sistema y 4.1 inodo: escritura atomica de escribir_dato.py
ls -li "$datos" > "$trabajo/inodo_antes.txt"
strace -f -e trace=openat,write,fsync,chmod,fchmod,fchmodat,rename,flock -o "$trabajo/strace.txt" \
    "$py" "$raiz/tools/escribir_dato.py" --archivo "$datos" velocidad=88 > /dev/null
ls -li "$datos" > "$trabajo/inodo_despues.txt"
{
    encabezado "Llamadas al sistema de una escritura atomica (temas 2.1, 4.3 y 4.4)" \
        "strace -f -e trace=openat,write,fsync,chmod,fchmod,fchmodat,rename,flock python tools/escribir_dato.py velocidad=88"
    echo "Se muestran solo las llamadas sobre el archivo de datos, su temporal y su candado:"
    grep -E 'vehiculo|\.tmp|lock|fsync|flock|rename|write\([0-9]+, "# Datos' "$trabajo/strace.txt" | grep -v ENOENT | sed 's/^[0-9]* *//'
    echo
    echo "Lectura: flock(LOCK_EX) serializa escritores; write+fsync guardan el temporal; rename lo publica de forma atomica."
} > "$salida/llamadas_al_sistema.txt"
{
    encabezado "Inodo antes y despues del reemplazo atomico (tema 4.1)" "ls -li; stat"
    echo "Antes:   $(cat "$trabajo/inodo_antes.txt")"
    echo "Despues: $(cat "$trabajo/inodo_despues.txt")"
    echo
    echo "El numero de inodo (primera columna) cambia: rename() publica un archivo nuevo. Por eso el lector"
    echo "incluye el inodo en su firma (DEF-10)."
    echo
    stat "$datos"
} > "$salida/inodo.txt"

# 3.1, 3.2, 3.4, 5.3, 4.4 y senales: la aplicacion real con un productor externo
"$py" "$raiz/tools/simulador.py" --archivo "$datos" --periodo-ms 100 --duracion-s 20 > /dev/null &
sim=$!
"$py" "$raiz/main.py" --proyecto "$trabajo" > /dev/null 2>&1 &
app=$!
sleep 6
{
    encabezado "Procesos e hilos del cluster (temas 3.1, 3.2 y 3.4)" "ps, pstree, /proc/PID/status"
    echo "Shell (PID $$) -> fork+exec de dos procesos: simulador (productor, PID $sim) y cluster (consumidor, PID $app)"
    echo
    ps -o pid,ppid,stat,ni,pri,nlwp,rss,vsz,cmd -p "$sim","$app"
    echo
    echo "-- Hilos del cluster (ps -L): principal (Tkinter), lector (HiloLector) y uno interno de la biblioteca Tcl/Tk --"
    ps -L -o pid,lwp,stat,pcpu,comm -p "$app"
    echo
    echo "-- Arbol de procesos --"
    pstree -p "$$" | sed 's/[[:space:]]*$//'
    echo
    echo "-- Memoria virtual y residente (tema 5.3): /proc/$app/status --"
    grep -E '^(Name|State|Threads|VmPeak|VmSize|VmRSS|VmSwap|voluntary_ctxt_switches|nonvoluntary_ctxt_switches)' "/proc/$app/status"
    echo
    echo "-- Archivos abiertos por el cluster (descriptores, tema 4.3) --"
    ls -l "/proc/$app/fd" 2>/dev/null | awk 'NR>1 {print $9, $10, $11}' | grep -E 'log|lock|vehiculo|odometro' || true
} > "$salida/procesos_hilos_memoria.txt"
{
    encabezado "Candado de instancia unica (tema 4.4)" "flock -n datos/odometro.txt.lock"
    if flock -n "$trabajo/datos/odometro.txt.lock" -c true; then
        echo "Con el cluster abierto: el candado estaba LIBRE (inesperado)"
    else
        echo "Con el cluster abierto: flock -n no obtiene el candado (codigo $?): otra ventana no puede tomarlo."
    fi
} > "$salida/candado.txt"
kill -TERM "$app"
wait "$app"
codigo=$?
{
    encabezado "Terminacion por senal (tema 3.2)" "kill -TERM PID; wait PID; echo \$?"
    echo "kill -TERM $app -> codigo de salida del cluster: $codigo (0 = cierre ordenado)"
    echo
    echo "-- Ultimas lineas de eventos.log --"
    tail -n 4 "$trabajo/logs/eventos.log"
    echo
    echo "-- Kilometraje guardado al cerrar (tema 5.1: lo que debe sobrevivir al apagado) --"
    cat "$trabajo/datos/odometro.txt"
} > "$salida/senales.txt"
if flock -n "$trabajo/datos/odometro.txt.lock" -c true; then
    echo "Despues de cerrar el cluster: flock -n SI obtiene el candado (el sistema lo libero)." >> "$salida/candado.txt"
fi
wait "$sim" 2>/dev/null

# 6.1 Permisos y privilegio minimo
{
    encabezado "Permisos y privilegio minimo (tema 6.1)" "id; ls -l; stat -c"
    echo "Usuario que ejecuta el cluster: $(id)"
    echo
    stat -c '%A %a %U:%G %n' "$trabajo/logs" "$trabajo"/logs/*.log "$datos" "$trabajo/datos/odometro.txt" \
        | sed "s#$trabajo/##"
    echo
    echo "logs/ 750 y bitacoras 640: el grupo puede leer, otros no. Un archivo de datos 666 se rechaza (CP-102)."
} > "$salida/permisos.txt"

# 2.3 Script de diagnostico sobre las bitacoras de esta corrida
bash "$raiz/tools/diagnostico.sh" "$trabajo/logs" "$salida/reporte_diagnostico.txt" > /dev/null
rm -rf "$trabajo"
ls -1 "$salida"
[[ $codigo -eq 0 ]]
