from __future__ import annotations

import pandas as pd
from pathlib import Path

OUT = Path('out')


def fmt(x, n=6):
    try:
        return f"{float(x):.{n}f}"
    except Exception:
        return str(x)


def main():
    OUT.mkdir(exist_ok=True)
    # Cargar resúmenes
    summary = pd.read_csv(OUT / 'summary_metrics.csv') if (OUT / 'summary_metrics.csv').exists() else pd.DataFrame()
    cont_sum = pd.read_csv(OUT / 'contingency_summary.csv') if (OUT / 'contingency_summary.csv').exists() else pd.DataFrame()

    lam_counts = fmt(summary.get('lambda_counts', [None])[0]) if not summary.empty else 'N/A'
    lam_inter = fmt(summary.get('lambda_interarrivals', [None])[0]) if not summary.empty else 'N/A'
    iod = fmt(summary.get('index_of_dispersion', [None])[0]) if not summary.empty else 'N/A'
    ks_stat = fmt(summary.get('ks_stat_expon', [None])[0]) if not summary.empty else 'N/A'
    ks_p = fmt(summary.get('ks_pvalue_expon', [None])[0]) if not summary.empty else 'N/A'

    p_tcp = fmt(cont_sum.get('P_TCP', [None])[0]) if not cont_sum.empty else 'N/A'
    p_grande = fmt(cont_sum.get('P_Grande', [None])[0]) if not cont_sum.empty else 'N/A'
    p_grande_tcp = fmt(cont_sum.get('P_Grande_given_TCP', [None])[0]) if not cont_sum.empty else 'N/A'
    indep = str(cont_sum.get('independent_TCP_vs_Grande', [None])[0]) if not cont_sum.empty else 'N/A'

    md = []
    md.append('# Informe Técnico')
    md.append('')
    md.append('Portada (rellenar manualmente): Nombre, cédula, título del proyecto, fecha.')
    md.append('')
    md.append('## Índice')
    md.append('- [Introducción](#introducción)')
    md.append('- [Datos y Metodología](#datos-y-metodología)')
    md.append('- [Resultados](#resultados)')
    md.append('  - [Variable Discreta (Poisson)](#variable-discreta-poisson)')
    md.append('  - [Variable Continua (Exponencial)](#variable-continua-exponencial)')
    md.append('  - [Variables Conjuntas (Protocolo × Tamaño)](#variables-conjuntas-protocolo--tamaño)')
    md.append('- [Detección de Anomalías](#detección-de-anomalías)')
    md.append('- [Conclusiones](#conclusiones)')
    md.append('- [Anexos](#anexos)')
    md.append('')
    md.append('## Introducción')
    md.append('Modelamos un tráfico de red a partir de un CSV con marcas de tiempo, tamaños de paquete y protocolo. Se analiza:')
    md.append('- Variable discreta: número de paquetes por segundo, con hipótesis Poisson(λ).')
    md.append('- Variable continua: tiempo entre llegadas, con hipótesis Exponencial(λ).')
    md.append('- Variables conjuntas: Protocolo (TCP/UDP) × Tamaño (Pequeño/Grande), con tabla de probabilidades y pruebas de independencia.')
    md.append('')
    md.append('## Datos y Metodología')
    md.append('- Columnas: Timestamp (fecha-hora), Packet_Size (bytes), Protocol (6=TCP, 17=UDP).')
    md.append('- Preprocesamiento: orden por Timestamp; agregación por segundo para conteos; diferencias consecutivas para interarribos.')
    md.append('- Estimaciones: λ_discreto como promedio de paquetes/seg en el rango; λ_expon = 1 / media(interarribos).')
    md.append('- Gráficos: histograma de conteos con PMF Poisson; histograma de interarribos con PDF Exponencial. Mapa de calor para conjuntas.')
    md.append('')
    md.append('## Resultados')
    md.append('### Variable Discreta (Poisson)')
    md.append(f'- λ por conteos (rango seleccionado) = **{lam_counts}** 1/s.')
    md.append(f'- Índice de dispersión Var/Media ≈ **{iod}** (≈1 en Poisson).')
    md.append('- Figura:')
    md.append('  ![Histograma paquetes/s con PMF Poisson](poisson_counts.png)')
    md.append('Interpretación: la curva Poisson(λ) superpuesta indica el grado de ajuste. Var/Media cercano a 1 sugiere congruencia con un proceso de Poisson; desviaciones notables indican sub/sobredispersión o muestra pequeña.')
    md.append('')
    md.append('### Variable Continua (Exponencial)')
    md.append(f'- λ por interarribos = **{lam_inter}** 1/s (λ = 1/mean).')
    md.append(f'- KS test exponencial (opcional): estadístico = **{ks_stat}**, p-valor = **{ks_p}**.')
    md.append('- Figura:')
    md.append('  ![Histograma de interarribos con PDF exponencial](exponential_interarrivals.png)')
    md.append('Interpretación: si la PDF Exp(λ) describe razonablemente el histograma, el modelo exponencial es plausible. El p-valor del KS se interpreta con cautela cuando n es pequeño.')
    md.append('')
    md.append('### Variables Conjuntas (Protocolo × Tamaño)')
    md.append(f'- P(TCP) = **{p_tcp}**; P(Grande) = **{p_grande}**; P(Grande | TCP) = **{p_grande_tcp}**.')
    md.append('- Figura (mapa de calor):')
    md.append('  ![Mapa de calor Protocolo × Tamaño](contingency_heatmap.png)')
    md.append('Explicación matemática de independencia:')
    md.append('- Sean A = {protocolo es TCP} y B = {tamaño es Grande}. A y B son independientes si P(A ∩ B) = P(A)·P(B), equivalente a P(B|A)=P(B) cuando P(A)>0.')
    md.append('- A partir de la tabla conjunta estimamos P(TCP), P(Grande) y P(TCP,Grande); entonces comprobamos si P(TCP,Grande) ≈ P(TCP)·P(Grande) (o si P(Grande|TCP) ≈ P(Grande)).')
    md.append('')
    md.append('## Detección de Anomalías')
    md.append('- Regla: marcar anómalo un segundo si k > λ + 3√λ (con λ=μ y Var=λ en Poisson).')
    md.append('- Ver `summary_metrics.csv` (umbral y conteos) y `anomalies.csv` (segundos marcados).')
    md.append('')
    md.append('## Conclusiones')
    md.append('- Los modelos Poisson/Exponencial proveen una base simple para caracterizar llegadas y tiempos. Con muestras pequeñas o resolución pobre (p. ej. segundos), se recomienda cautela y validar con más datos.')
    md.append('- La relación Protocolo × Tamaño se resume en la tabla 2×2; la independencia se decide comparando P(Grande|TCP) con P(Grande).')
    md.append('- Extensiones: ventanas móviles, estacionalidad, pruebas χ² o KS con mayor n, o modelos alternativos (p. ej., Gamma o Lognormal en tiempos).')
    md.append('')
    md.append('## Funciones y código utilizado')
    md.append('- `src/data/loaders.py`')
    md.append('  - `read_network_csv`: lee CSV con columnas Timestamp, Packet_Size, Protocol. Soporta formatos con/ sin segundos y AM/PM. Devuelve una lista de registros tipados.')
    md.append('- `src/analysis/statistics.py`')
    md.append('  - `group_counts_per_second(timestamps_sec)`: cuenta paquetes por segundo (floor de timestamp).')
    md.append('  - `expand_counts_with_zeros(counts_per_sec)`: construye el vector de conteos por cada segundo del rango, rellenando con 0 los segundos sin llegadas.')
    md.append('  - `estimate_lambda_from_counts(counts_per_sec)`: estima λ como total de llegadas dividido por duración (en segundos).')
    md.append('  - `index_of_dispersion(counts)`: Var/Media (≈1 en Poisson).')
    md.append('  - `interarrival_times(timestamps_sec)`: diferencias consecutivas (s).')
    md.append('  - `estimate_lambda_from_interarrivals(deltas)`: λ = 1/ media(Δ).')
    md.append('  - `poisson_pmf(k, λ)`: e^{-λ} λ^k / k!.')
    md.append('  - `exponential_pdf(x, λ)`: λ e^{-λx} (x≥0).')
    md.append('  - `contingency_protocol_size(protocols, sizes, threshold)`: tabla conjunta Protocolo×Tamaño con P(TCP), P(Grande), P(Grande|TCP) e indicador de independencia.')
    md.append('  - `poisson_anomaly_threshold(λ, z)`: umbral k > λ + z√λ (z=3 por defecto).')
    md.append('- `analysis_cli.py` (script principal de análisis)')
    md.append('  - Parámetros relevantes:')
    md.append('    - `--seconds-range a-b`: analiza solo los segundos relativos [a..b] para la parte discreta.')
    md.append('    - `--excel-table` y `--excel-compact`: exportan tablas listas para Excel.')
    md.append('  - Genera: figuras PNG, CSV de resumen y tablas (counts, histograma Poisson, interarribos, conjuntas, anomalías).')
    md.append('- `generate_report.py`: compone este informe a partir de los CSV generados.')
    md.append('')
    md.append('## Notas sobre imágenes y exportación a PDF')
    md.append('- Para que las imágenes aparezcan incrustadas (no como vínculos), usa la sintaxis Markdown de imagen: `![texto alternativo](ruta.png)`. Este informe ya la utiliza para todas las figuras.')
    md.append('- Al convertir a PDF con Pandoc, asegúrate de que el conversor encuentre los recursos. Desde la carpeta raíz del proyecto:')
    md.append('  - En PowerShell:')
    md.append('    ```powershell')
    md.append('    pandoc .\out\Informe_Tecnico.md -o .\out\Informe_Tecnico.pdf --from gfm --resource-path=out')
    md.append('    ```')
    md.append('  - `--resource-path=out` indica dónde están las imágenes relativas. Como el informe y las imágenes están ambos en `out/`, las rutas simples (p.ej. `poisson_counts.png`) funcionarán.')
    md.append('- Alternativas:')
    md.append('  - Extensión de VS Code “Markdown PDF”: exporta a PDF mostrando las imágenes incrustadas automáticamente.')
    md.append('  - Imprimir desde el preview de Markdown a “Microsoft Print to PDF”.')
    md.append('')
    md.append('## Anexos')
    md.append('- Discreta: counts_per_second.csv, poisson_histogram_table.csv, poisson_histogram_table_compact.csv')
    md.append('- Continua: interarrival_times.csv, exponential_pdf_table.csv')
    md.append('- Conjunta: contingency.csv, contingency_full.csv, contingency_summary.csv')

    (OUT / 'Informe_Tecnico.md').write_text('\n'.join(md), encoding='utf-8')
    print('Reporte generado en out/Informe_Tecnico.md')


if __name__ == '__main__':
    main()
