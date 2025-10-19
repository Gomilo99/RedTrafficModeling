# Guión sugerido para el video

Duración objetivo: 6–10 minutos.

1) Introducción (30s)
- Presentación (nombre y cédula) y título del proyecto.
- Objetivo: modelar tráfico de red con Poisson/Exponencial, analizar TCP/UDP x tamaño y detectar anomalías.

2) Datos y carga (45s)
- Mostrar `network_traffic.csv` (columnas: Timestamp, Packet_Size, Protocol; 6=TCP, 17=UDP).
- Explicar formato de timestamp. Si no tiene segundos precisos, comentar el uso de `--jitter-seconds`.
- Código: función `read_network_csv` en `src/data/loaders.py`.

3) Análisis discreto (Poisson) (2m)
- `analysis_cli.py`: agrupar por segundo, contar paquetes (`group_counts_per_second`).
- Estimar λ por conteos (`estimate_lambda_from_counts`).
- Histograma vs PMF Poisson teórica y `poisson_counts.png`.
- Métrica de ajuste: Índice de dispersión Var/Media ≈ 1 si Poisson.

4) Análisis continuo (Exponencial) (1.5m)
- Calcular interarribos (`interarrival_times`), estimar λ = 1/mean.
- Histograma vs PDF exponencial teórica en `exponential_interarrivals.png`.

5) Análisis conjunto (Protocolo x Tamaño) (1.5m)
- Discretizar tamaño: ≤500 Pequeño, >500 Grande.
- Tabla de prob. conjunta en `out/contingency.csv` y métricas: P(TCP), P(Grande), P(Grande|TCP).
- Independencia si P(Grande|TCP) ≈ P(Grande).

6) Detección de anomalías (1m)
- Regla: k > λ + 3√λ, `poisson_anomaly_threshold`.
- Mostrar `out/anomalies.csv` y el resumen `out/summary_metrics.csv`.

7) Conclusiones (30s)
- Comentarios sobre el ajuste y utilidad de modelos.
- Posibles mejoras (más datos, ventanas variables, tests de bondad de ajuste formales).

8) Cómo reproducir (30s)
- Ejecutar (PowerShell):
  - `python -m venv .venv ; .\.venv\Scripts\Activate.ps1`
  - `pip install -r requirements.txt`
  - `python .\analysis_cli.py .\network_traffic.csv --out .\out --jitter-seconds 60`

Consejos de grabación:
- Captura de pantalla + voz en off.
- Resalta el código y las gráficas generadas.
- Evita pantallas vacías; mantén el ritmo con transiciones breves.