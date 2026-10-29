# Bitácora de uso de IA — Proyecto Clúster F40

## Etapa 0 — Auditoría
- Fecha: 2026-10-29 00:13
- Qué se hizo: se auditó /home/ayocesaar/cluster-f40, confirmando que estaba vacía (sin trabajo
  previo). Se instalaron paquetes de sistema (python3-tk, python3-venv) con sudo del usuario. Se
  creó el entorno virtual .venv y se instalaron pytest, coverage, pillow y python-docx dentro de
  él. Se inicializó el repositorio git y se creó la estructura de carpetas base.
- Comandos ejecutados: ver docs/evidencias/pytest_inicial.txt y el historial de esta sesión.
- Resultado real: entorno listo, sin pruebas aún (no existían).
- Qué generó la IA: la estructura de carpetas, el contenido de este archivo y de docs/auditoria.md,
  y el .gitignore. El usuario (César) ejecutó todos los comandos en su VM y verificó la salida real
  en cada paso.

## Etapa 1 y 2 — Entorno y logica central
- Entorno confirmado en la auditoria inicial: Ubuntu 22.04.5 LTS (jammy), Python 3.10.12, git 2.34.1, tkinter disponible tras instalar python3-tk.
- Se crearon logic/reloj.py (RelojReal, RelojSimulado) y logic/estado.py (EstadoCluster con R01-R08), sin dependencias de Tkinter.
- Decision de diseno documentada: al apagar el motor se apaga tambien el testigo 9 y el ambar del elemento 2, y se reinician sus temporizadores de histeresis, para evitar un falso encendido 1s despues de apagar el motor.
- Qué generó la IA: el contenido completo de ambos archivos. El usuario los guardó y verificó que compilan sin errores de sintaxis.
