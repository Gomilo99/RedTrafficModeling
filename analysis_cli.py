from __future__ import annotations

import argparse
from pathlib import Path
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.loaders import read_network_csv
from src.analysis.statistics import (
    group_counts_per_second,
    estimate_lambda_from_counts,
    expand_counts_with_zeros,
    index_of_dispersion,
    interarrival_times,
    estimate_lambda_from_interarrivals,
    poisson_pmf,
    exponential_pdf,
    contingency_protocol_size,
    poisson_anomaly_threshold,
)


def main():
    ap = argparse.ArgumentParser(description="Análisis de tráfico: Poisson, Exponencial, Conjunta y Anomalías")
    ap.add_argument("csv", type=str, help="Ruta al network_traffic.csv")
    ap.add_argument("--out", type=str, default="out", help="Carpeta de salida para gráficos")
    ap.add_argument("--jitter-seconds", type=float, default=0.0, help="Ruido uniforme [0,j]s para timestamps (ej: 60 si solo hay resolución de minutos)")
    ap.add_argument("--excel-table", action="store_true", help="Exporta tabla lista para Excel con frecuencias observadas y Poisson teórica")
    ap.add_argument("--excel-compact", action="store_true", help="Si se usa con --excel-table, exporta tabla adicional solo con k observados")
    ap.add_argument("--seconds-range", type=str, default=None, help="Rango de segundos a analizar, formato inicio-fin (ej: 1-7)")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # Cargar datos
    records = read_network_csv(args.csv)
    ts_base = [r.timestamp.timestamp() for r in records]  # segundos epoch
    if args.jitter_seconds and args.jitter_seconds > 0:
        rng = np.random.default_rng(12345)
        jitter = rng.uniform(0, args.jitter_seconds, size=len(ts_base))
        ts = [tb + j for tb, j in zip(ts_base, jitter)]
    else:
        ts = ts_base
    sizes = [r.packet_size for r in records]
    protos = [r.protocol for r in records]

    # Fase 2.1: Discreta (Poisson)
    counts_abs = group_counts_per_second(ts)
    # Construir vector completo (rellenando ceros) y operar en segundos relativos [0..N]
    counts_vector_full = expand_counts_with_zeros(counts_abs)
    start_label = 0
    end_label = len(counts_vector_full) - 1
    if args.seconds_range:
        try:
            # Interpretar como 1-based: 1-7 -> índices 0..6
            s_ini_label, s_fin_label = map(int, args.seconds_range.split('-'))
            s_ini = s_ini_label - 1
            s_fin = s_fin_label - 1
        except Exception:
            raise ValueError("Formato de --seconds-range debe ser inicio-fin (1-based), ej: 1-7")
        if s_ini < 0 or s_fin >= len(counts_vector_full) or s_ini > s_fin:
            raise ValueError(
                f"Rango inválido {s_ini_label}-{s_fin_label}. Debe estar dentro de 1-{len(counts_vector_full)} y ini<=fin.")
        counts_vector = counts_vector_full[s_ini:s_fin + 1]
        # Diccionario etiquetado con segundos 1-based del rango solicitado
        counts_rel = {label: counts_vector[idx] for label, idx in zip(range(s_ini_label, s_fin_label + 1), range(0, len(counts_vector)))}
        start_label, end_label = s_ini_label, s_fin_label
    else:
        counts_vector = counts_vector_full
        counts_rel = {i: v for i, v in enumerate(counts_vector)}

    lam_counts = (sum(counts_vector) / len(counts_vector)) if counts_vector else float('nan')
    iod = index_of_dispersion(counts_vector)
    xs = np.arange(0, (max(counts_rel.values()) + 5) if counts_rel else 10)
    pmf = [poisson_pmf(int(k), lam_counts) if math.isfinite(lam_counts) else 0.0 for k in xs]

    # histograma de conteos por segundo
    obs = list(counts_rel.values())
    plt.figure(figsize=(6,4))
    plt.hist(
        obs,
        bins=range(0, max(obs)+2 if obs else 2),
        density=True,
        alpha=0.6,
        label="Datos",
        edgecolor="#333333",
        linewidth=0.8
    )
    plt.plot(xs, pmf, 'o-', label=f"Poisson(lambda={lam_counts:.3f})")
    plt.title("Número de paquetes por segundo")
    plt.xlabel("k paquetes/s")
    plt.ylabel("Probabilidad")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "poisson_counts.png")
    plt.close()

    # Tabla para Excel: frecuencias del número de paquetes por segundo
    if args.excel_table:
        # Construye distribución empírica de k = 0..K
        # Primero contamos cuántas veces aparece cada k en los segundos observados (incluye ceros)
        from collections import Counter
        freq_emp = Counter(counts_vector)
        total_secs = len(counts_vector)
        rows = []
        max_k = max(max(xs), max(freq_emp.keys()) if freq_emp else 0)
        for k in range(0, int(max_k) + 1):
            observed = freq_emp.get(k, 0)
            rel_freq = observed / total_secs if total_secs > 0 else 0.0
            p_theory = poisson_pmf(k, lam_counts) if math.isfinite(lam_counts) else 0.0
            expected = p_theory * total_secs
            rows.append({
                "k_paquetes_por_seg": k,
                "frecuencia_observada": observed,
                "frecuencia_relativa": rel_freq,
                "poisson_pmf_teorica": p_theory,
                "frecuencia_esperada": expected
            })
        df_excel = pd.DataFrame(rows)
        df_excel.to_csv(outdir / "poisson_histogram_table.csv", index=False)
        if args.excel_compact:
            df_excel_compact = df_excel[df_excel["frecuencia_observada"] > 0].copy()
            df_excel_compact.to_csv(outdir / "poisson_histogram_table_compact.csv", index=False)

    # Exportar serie de conteos por segundo (índice relativo) para Excel
    if counts_vector:
        df_counts = pd.DataFrame({
            "segundo": list(range(start_label, end_label + 1)),
            "paquetes_por_seg": counts_vector
        })
        df_counts.to_csv(outdir / "counts_per_second.csv", index=False)

    # Fase 2.2: Continua (Exponencial)
    deltas = interarrival_times(ts)
    lam_inter = estimate_lambda_from_interarrivals(deltas)
    # histograma y pdf exponencial
    if deltas:
        xs_cont = np.linspace(0, max(deltas), 100)
    else:
        xs_cont = np.linspace(0, 1, 100)
    pdf = [exponential_pdf(x, lam_inter) if math.isfinite(lam_inter) else 0.0 for x in xs_cont]
    plt.figure(figsize=(6,4))
    if deltas:
        plt.hist(
            deltas,
            bins=30,
            density=True,
            alpha=0.6,
            label="Datos",
            edgecolor="#333333",
            linewidth=0.8
        )
    plt.plot(xs_cont, pdf, label=f"Exp(lambda={lam_inter:.3f})")
    plt.title("Tiempos entre llegadas")
    plt.xlabel("segundos")
    plt.ylabel("Densidad")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "exponential_interarrivals.png")
    plt.close()

    # Exportar interarribos y PDF teórica para Excel/validación
    if deltas:
        pd.DataFrame({"interarribo_s": deltas}).to_csv(outdir / "interarrival_times.csv", index=False)
    pd.DataFrame({"t_s": xs_cont, "pdf_exponencial": pdf}).to_csv(outdir / "exponential_pdf_table.csv", index=False)

    # Fase 2.3: Conjunta (Protocolo y Tamaño)
    cont = contingency_protocol_size(protos, sizes, threshold=500)
    # Tabla en CSV (probabilidades presentes)
    rows = []
    for (prot, sizecat), prob in sorted(cont.table.items()):
        rows.append({"protocolo": prot, "tam_categoria": sizecat, "probabilidad": prob})
    pd.DataFrame(rows).to_csv(outdir / "contingency.csv", index=False)

    # Tabla completa (4 combinaciones) con conteos y probabilidades
    # Reconstruir categorías
    def proto_name(p: int) -> str:
        return 'TCP' if p == 6 else ('UDP' if p == 17 else str(p))
    def size_cat(s: int) -> str:
        return 'Pequeño' if s <= 500 else 'Grande'
    pairs = [(proto_name(p), size_cat(s)) for p, s in zip(protos, sizes)]
    from collections import Counter
    c_pairs = Counter(pairs)
    total_n = len(pairs)
    combos = [('TCP','Pequeño'), ('TCP','Grande'), ('UDP','Pequeño'), ('UDP','Grande')]
    rows_full = []
    for prot, sc in combos:
        count = c_pairs.get((prot, sc), 0)
        prob = count / total_n if total_n > 0 else float('nan')
        rows_full.append({
            'protocolo': prot,
            'tam_categoria': sc,
            'conteo': count,
            'probabilidad': prob
        })
    pd.DataFrame(rows_full).to_csv(outdir / "contingency_full.csv", index=False)

    # Resumen marginales y condicional
    summary_cont = {
        'P_TCP': cont.p_tcp,
        'P_Grande': cont.p_grande,
        'P_Grande_dado_TCP': cont.p_grande_given_tcp,
        'independencia_TCP_vs_Grande': cont.independent
    }
    pd.DataFrame([summary_cont]).to_csv(outdir / "contingency_summary.csv", index=False)

    # Heatmap de probabilidades conjuntas (fila: protocolo, columna: tamaño)
    try:
        # Matriz de probabilidades
        p_tcp_peq = next((r['probabilidad'] for r in rows_full if r['protocolo']=='TCP' and r['tam_categoria']=='Pequeño'), 0.0)
        p_tcp_gra = next((r['probabilidad'] for r in rows_full if r['protocolo']=='TCP' and r['tam_categoria']=='Grande'), 0.0)
        p_udp_peq = next((r['probabilidad'] for r in rows_full if r['protocolo']=='UDP' and r['tam_categoria']=='Pequeño'), 0.0)
        p_udp_gra = next((r['probabilidad'] for r in rows_full if r['protocolo']=='UDP' and r['tam_categoria']=='Grande'), 0.0)
        mat = np.array([[p_tcp_peq, p_tcp_gra], [p_udp_peq, p_udp_gra]])
        fig, ax = plt.subplots(figsize=(5,3.4))
        im = ax.imshow(mat, cmap='Blues', vmin=0, vmax=max(1e-9, mat.max()))
        ax.set_xticks([0,1], labels=['Pequeño','Grande'])
        ax.set_yticks([0,1], labels=['TCP','UDP'])
        ax.set_title('Probabilidades conjuntas (Protocolo x Tamaño)')
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, f"{mat[i,j]:.3f}", ha='center', va='center', color='black')
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='Probabilidad')
        plt.tight_layout()
        plt.savefig(outdir / 'contingency_heatmap.png')
        plt.close(fig)
    except Exception:
        pass

    # Fase 3: Detección de anomalías
    lam = lam_counts
    k_thresh = poisson_anomaly_threshold(lam, z=3.0)
    anomalies = [(sec, cnt) for sec, cnt in counts_rel.items() if cnt > k_thresh]
    pd.DataFrame(anomalies, columns=["segundo", "paquetes_en_segundo"]).to_csv(outdir / "anomalies.csv", index=False)

    # Figura de anomalías: barras de k(t) y línea horizontal del umbral
    try:
        secs = list(counts_rel.keys())
        vals = list(counts_rel.values())
        if secs and vals:
            plt.figure(figsize=(7,3.2))
            plt.bar(secs, vals, color="#4C78A8", edgecolor="#333333", linewidth=0.6)
            plt.axhline(y=k_thresh, color="#E45756", linestyle="--", linewidth=1.2, label=f"Umbral k>{k_thresh}")
            plt.title("Detección de anomalías (k por segundo)")
            plt.xlabel("segundo (etiqueta relativa)")
            plt.ylabel("k paquetes/s")
            plt.legend()
            plt.tight_layout()
            plt.savefig(outdir / "anomalies_plot.png")
            plt.close()
    except Exception:
        pass

    # Guardar resumen de métricas
    # KS test opcional (si hay datos y lambda válido)
    ks_stat = float('nan')
    ks_pvalue = float('nan')
    try:
        if deltas and math.isfinite(lam_inter) and lam_inter > 0:
            from scipy.stats import kstest, expon
            # Exponencial con loc=0 y scale=1/lambda
            ks = kstest(deltas, 'expon', args=(0, 1.0/lam_inter))
            ks_stat, ks_pvalue = ks.statistic, ks.pvalue
    except Exception:
        pass

    summary = {
        "lambda_conteos": lam_counts,
        "lambda_interarribos": lam_inter,
        "indice_dispersion": iod,
        "umbral_anomalia_k": k_thresh,
        "anomalias_encontradas": len(anomalies),
        "ks_estadistico_expon": ks_stat,
        "ks_pvalor_expon": ks_pvalue
    }
    pd.DataFrame([summary]).to_csv(outdir / "summary_metrics.csv", index=False)

    # Reporte breve en consola
    print("Fase 2.1 Poisson:")
    print(f"  lambda (por conteos) = {lam_counts:.6f}")
    print(f"  Indice de dispersion Var/Media ~= {iod:.3f} (~=1 si Poisson)")
    print("Fase 2.2 Exponencial:")
    print(f"  lambda (por interarribos) = {lam_inter:.6f}")
    print("Fase 2.3 Conjunta (TCP/UDP x Tamano <=/> 500):")
    print(f"  P(TCP) = {cont.p_tcp:.6f}")
    print(f"  P(Grande) = {cont.p_grande:.6f}")
    print(f"  P(Grande|TCP) = {cont.p_grande_given_tcp:.6f}")
    print(f"  Independencia (TCP vs Grande): {cont.independent}")
    print("Fase 3 Umbral de anomalia (3*sigma):")
    print(f"  Umbral k > {k_thresh} (con lambda={lam:.6f})")
    print(f"  Anomalías encontradas: {len(anomalies)}")


if __name__ == "__main__":
    main()
