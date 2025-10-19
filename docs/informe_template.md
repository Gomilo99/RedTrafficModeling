# Título del Proyecto

Autor: NOMBRE (CÉDULA)
Fecha: AAAA-MM-DD

## Introducción
Breve descripción del problema, dataset (`Timestamp`, `Packet_Size`, `Protocol`) y objetivos del análisis.

## Análisis Discreto (Poisson)
- Hipótesis: número de paquetes por segundo ~ Poisson(λ).
- Estimación de λ: promedio de paquetes/seg.
- Figura: insertar `out/poisson_counts.png`.
- Discusión del ajuste: comparar histograma vs PMF; índice de dispersión Var/Media ≈ 1 si Poisson. Resultado: ...

## Análisis Continuo (Exponencial)
- Hipótesis: interarribos ~ Exponencial(λ).
- Estimación de λ = 1/mean(interarribos).
- Figura: insertar `out/exponential_interarrivals.png`.
- Discusión del ajuste: comentarios sobre cola pesada, sesgos, etc.

## Análisis Conjunto (Protocolo x Tamaño)
- Discretización: Pequeño ≤ 500, Grande > 500.
- Tabla conjunta: ver `out/contingency.csv`.
- Probabilidades: P(TCP), P(Grande), P(Grande|TCP). ¿Independencia? Verificar si P(Grande|TCP) ≈ P(Grande).

## Detección de Anomalías
- Regla: anómalo si k > λ + 3√λ.
- Umbral y conteo de anomalías: ver `out/summary_metrics.csv` y `out/anomalies.csv`.

## Conclusiones
Reflexión sobre utilidad de modelos probabilísticos y posibles mejoras (más datos, pruebas formales KS/χ², ventanas dinámicas, estacionalidad, etc.).

---

Notas para exportar a PDF:
- Puedes usar un procesador (Word/Google Docs) e insertar las figuras y tablas, o usar Pandoc:
  - pandoc docs/informe_template.md -o Informe_Tecnico.pdf
- Mantén máximo 4 páginas.