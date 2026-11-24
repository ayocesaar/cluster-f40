#!/usr/bin/env bash
# Analizador de bitacoras del cluster F40 (tema 2.3, programacion del shell).
#
# Uso: tools/diagnostico.sh CARPETA_LOGS [REPORTE]
#   CARPETA_LOGS  carpeta con eventos.log y errores.log (y sus respaldos .1, .2 ...)
#   REPORTE       archivo de salida (por defecto reporte_diagnostico.txt)
#
# Codigos de salida: 0 reporte generado, 1 uso incorrecto, 2 la carpeta no existe
# o no se puede leer, 3 la carpeta no tiene bitacoras del cluster.
# Clasificacion (didactica, como en la clase): 0 errores SIN ERRORES; 1 a 5 REVISION
# RECOMENDADA; mas de 5 CRITICO. Un testigo de seguridad encendido (9 o 10) agrega
# ALERTA DE SEGURIDAD aunque no haya errores.

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Uso: $0 CARPETA_LOGS [REPORTE]" >&2
    exit 1
fi

carpeta="$1"
reporte="${2:-reporte_diagnostico.txt}"

if [[ ! -d "$carpeta" || ! -r "$carpeta" ]]; then
    echo "Error: no existe o no se puede leer la carpeta: $carpeta" >&2
    exit 2
fi

shopt -s nullglob
eventos=("$carpeta"/eventos.log*)
errores=("$carpeta"/errores.log*)
shopt -u nullglob
if [[ ${#eventos[@]} -eq 0 && ${#errores[@]} -eq 0 ]]; then
    echo "Error: $carpeta no contiene eventos.log ni errores.log" >&2
    exit 3
fi

# contar PATRON ARCHIVO...: lineas que contienen el patron (0 si no hay archivos)
contar() {
    local patron="$1"
    shift
    if [[ $# -eq 0 ]]; then
        echo 0
        return
    fi
    cat -- "$@" | grep -c -- "$patron"
}

n_errores=$(contar " ERROR " "${errores[@]}")
n_warn=$(contar " WARN " "${eventos[@]}")
n_info=$(contar " INFO " "${eventos[@]}")
n_rechazos=$(contar "resultado=rechazado" "${errores[@]}")
n_t9=$(contar "testigo_9_encendido" "${eventos[@]}")
n_t10=$(contar "testigo_10_encendido" "${eventos[@]}")
n_odo=$(contar "odometro_actualizado" "${eventos[@]}")

if [[ "$n_errores" -eq 0 ]]; then
    estado="SIN ERRORES"
elif [[ "$n_errores" -le 5 ]]; then
    estado="REVISION RECOMENDADA"
else
    estado="CRITICO"
fi
if [[ "$n_t9" -gt 0 || "$n_t10" -gt 0 ]]; then
    estado="$estado + ALERTA DE SEGURIDAD"
fi

{
    echo "REPORTE DE DIAGNOSTICO - CLUSTER F40"
    echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Usuario: $(whoami)"
    echo "Kernel: $(uname -r)"
    echo "Carpeta analizada: $carpeta"
    echo "Archivos: ${#eventos[@]} de eventos, ${#errores[@]} de errores"
    echo "INFO: $n_info"
    echo "WARN: $n_warn"
    echo "ERROR: $n_errores (rechazados: $n_rechazos)"
    echo "Testigo 9 encendido: $n_t9 veces"
    echo "Testigo 10 encendido: $n_t10 veces"
    echo "Kilometros registrados: $n_odo"
    echo "Estado: $estado"
    if [[ "$n_errores" -gt 0 ]]; then
        echo "TIPOS DE ERROR (cantidad)"
        cat -- "${errores[@]}" | awk '{print $4}' | sort | uniq -c | sort -rn
        echo "ULTIMOS ERRORES"
        cat -- "${errores[@]}" | grep -n " ERROR " | tail -n 10
    fi
} > "$reporte"

echo "Reporte generado: $reporte ($estado)"
exit 0
