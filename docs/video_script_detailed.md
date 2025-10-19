# Guion de Video (Detallado)

Duración objetivo: 8–12 min

## 1. Portada e Introducción (30–45s)
- Presentación (nombre, cédula) y título del proyecto.
- Objetivo: modelar el tráfico mediante Poisson (paquetes/s), Exponencial (interarribos), analizar Protocolo×Tamaño e identificar anomalías.

## 2. Datos y Preparación (60–90s)
- Mostrar `network_traffic.csv`: columnas Timestamp, Packet_Size, Protocol (6=TCP, 17=UDP).
- Explicar parsing del timestamp (formato con segundos y AM/PM) en `src/data/loaders.py`.
- Aclarar que ordenamos por Timestamp; para Poisson agregamos por segundo; para Exponencial hacemos diferencias consecutivas.

## 3. Variable Discreta (Poisson) (2–3 min)
- Ejecutar CLI: `analysis_cli.py` con `--seconds-range 1-7` para replicar tu selección.
- Explicar λ_discreto = promedio de paquetes/s en el rango elegido.
- Mostrar `out/counts_per_second.csv` y `out/poisson_histogram_table.csv`.
- Mostrar `out/poisson_counts.png`: histograma con delimitadores y PMF Poisson(λ).
- Comentar índice de dispersión (Var/Media ≈ 1 en Poisson) desde `summary_metrics.csv`.

## 4. Variable Continua (Exponencial) (2–3 min)
- Mostrar cálculo de interarribos (diferencias de timestamps) y λ = 1/mean(interarribos).
- Mostrar `out/interarrival_times.csv` y `out/exponential_interarrivals.png` (histograma con PDF teórica y bordes).
- Mencionar KS opcional (`summary_metrics.csv`), y la cautela con muestras pequeñas.

## 5. Variables Conjuntas (Protocolo × Tamaño) (1.5–2 min)
- Discretizar tamaño: ≤500 Pequeño, >500 Grande.
- Mostrar `out/contingency_full.csv`: 4 combinaciones con conteos y probabilidades.
- Mostrar `out/contingency_heatmap.png` como visual rápida.
- Explicación matemática de independencia: P(TCP,Grande) ≟ P(TCP)·P(Grande) o P(Grande|TCP) ≟ P(Grande).

## 6. Detección de Anomalías (1 min)
- Regla: anómalo si k > λ + 3√λ; mostrar umbral en `summary_metrics.csv` y `out/anomalies.csv`.

## 7. Conclusiones (30–45s)
- Resumen del ajuste y hallazgos.
- Limitaciones (muestra pequeña, resolución temporal) y mejoras.

## 8. Cómo Reproducir (30–45s)
- PowerShell:
  - `python -m venv .venv ; .\.venv\Scripts\Activate.ps1`
  - `pip install -r requirements.txt`
  - `python .\analysis_cli.py .\network_traffic.csv --out .\out --seconds-range 1-7`
  - `python .\generate_report.py`
