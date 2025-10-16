# RedTrafficModeling

Prototipo educativo para modelar tráfico de red con colas M/M/1 usando simulación de eventos discretos y una interfaz gráfica básica.

## Objetivos específicos

- Modelar un fenómeno discreto: número de paquetes por segundo ~ Poisson(λ).
- Modelar un fenómeno continuo: tiempo entre llegadas ~ Exponencial(λ).
- Analizar relación conjunta: protocolo (TCP/UDP) vs tamaño (Pequeño/Grande) con tabla de probabilidad conjunta y marginales/condicionales.
- Aplicar modelos: establecer un umbral (3σ) para detectar anomalías en conteos por segundo.

## Objetivo

Tomar un CSV de tráfico (timestamp, tamaño de paquete, protocolo), estimar parámetros de llegada y servicio, y simular una cola M/M/1 para obtener métricas como utilización, esperas y número en sistema.

## Conceptos probabilísticos clave

- Proceso de Poisson: cuenta llegadas por unidad de tiempo con tasa λ; los tiempos entre llegadas son exponenciales con media 1/λ.
- Servicio exponencial: tiempos de servicio con tasa μ (media 1/μ). Memoria-libre, útil para modelar variabilidad alta.
- M/M/1: llegadas Poisson (M), servicio exponencial (M), 1 servidor, disciplina FIFO.
- Estabilidad: requiere ρ = λ/μ < 1. Si ρ ≥ 1, la cola tiende a crecer sin cota.
- Fórmulas teóricas (estado estable):
	- L = ρ / (1 - ρ), Lq = ρ² / (1 - ρ)
	- W = 1 / (μ - λ), Wq = ρ / (μ - λ)
	- Ley de Little: L = λ W, Lq = λ Wq

## Estructura del proyecto

- `src/data/loaders.py`: lectura del CSV y estimación de λ y μ.
- `src/sim/queue_mm1.py`: simulador de eventos discretos para M/M/1.
- `src/analysis/statistics.py`: utilidades de análisis (Poisson, Exponencial, conjunta, anomalías).
- `analysis_cli.py`: script de análisis para Fases 2-3, genera gráficos y CSV.
- `app.py`: interfaz gráfica (Tkinter) para cargar CSV, estimar parámetros y simular.
- `network_traffic.csv`: ejemplo de datos.

## Uso rápido (Windows PowerShell)

1) Asegúrate de tener Python 3.10+ instalado.

2) (Opcional) Crea y activa un venv:

```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
```

3) Instala dependencias (vacío, Tkinter viene con Python en Windows):

```powershell
pip install -r requirements.txt
```

4) Ejecuta la app:

```powershell
python .\app.py
```

5) Ejecutar análisis (Fases 2-3):

```powershell
pip install -r requirements.txt
# Si el timestamp no tiene segundos (p.ej., solo minutos), usa jitter para repartir en el minuto
python .\analysis_cli.py .\network_traffic.csv --out .\out --jitter-seconds 60
```
Se generan:
- `out\poisson_counts.png`: Histograma de paquetes/s con PMF Poisson superpuesta.
- `out\exponential_interarrivals.png`: Hist. de interarribos con PDF Exponencial superpuesta.
- `out\contingency.csv`: Tabla conjunta y probabilidades.
- `out\anomalies.csv`: Intervalos de 1s marcados como anómalos (k > λ + 3√λ).

## Flujo dentro de la app

1) Abre el CSV (Timestamp,Packet_Size,Protocol).
2) Puedes estimar parámetros:
	 - λ (llegadas/seg) se calcula como promedio de llegadas por segundo agregadas por intervalos (default 60s).
	 - μ (servicios/seg) se estima a partir de la media de tiempos de servicio. Si no se provee la media en ms, se usa una heurística con tamaño de paquete y un enlace hipotético de 100 Mbps.
3) Ajusta duración de simulación o límite de llegadas y pulsa “Simular”.
4) Observa las métricas empíricas (W, Wq, L, Lq) y la utilización.

## Notas sobre datos

- El CSV de ejemplo repite un mismo minuto; para mejores estimaciones de λ, usa ventanas de varios minutos u horas.
- Si conoces la capacidad real del enlace o la media de servicio (en ms), introdúcela para mejorar μ.

## Metodología y Fases

Fase 1: Selección y Comprensión del Conjunto de Datos
- `network_traffic.csv` con columnas: `Timestamp` (fecha y hora), `Packet_Size` (bytes), `Protocol` (6=TCP, 17=UDP).

Fase 2: Análisis con Variables Aleatorias
1) Variable discreta (Paquetes por segundo):
	- Agrupar por segundo y contar paquetes.
	- Calcular λ promedio.
	- Hipótesis: Poisson(λ). Graficar histograma y PMF.
2) Variable continua (Tiempo entre llegadas):
	- Diferencias entre timestamps consecutivos (en s).
	- λ = 1 / media de interarribos. Hipótesis: Exponencial(λ). Graficar hist y PDF.
3) Variables conjuntas (Protocolo x Tamaño):
	- Tamaño: Pequeño ≤ 500, Grande > 500.
	- Tabla conjunta, P(TCP), P(Grande), P(Grande|TCP), independencia si P(Grande|TCP)=P(Grande).

Fase 3: Detección de Anomalías
- Umbral simple: k > λ + 3√λ para marcar segundos anómalos.

## Extensiones posibles

- M/M/c (múltiples servidores), colas con buffer finito (M/M/1/K), prioridades, o llegadas/servicios no-exponenciales (G/G/1) vía simulación.
- Integración con pandas y gráficos.
