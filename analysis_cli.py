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
    counts = group_counts_per_second(ts)
    lam_counts = estimate_lambda_from_counts(counts)
    xs = np.arange(0, max(counts.values()) + 5 if counts else 10)
    pmf = [poisson_pmf(int(k), lam_counts) if math.isfinite(lam_counts) else 0.0 for k in xs]

    # histograma de conteos por segundo
    obs = list(counts.values())
    plt.figure(figsize=(6,4))
    plt.hist(obs, bins=range(0, max(obs)+2 if obs else 2), density=True, alpha=0.6, label="Datos")
    plt.plot(xs, pmf, 'o-', label=f"Poisson(λ={lam_counts:.3f})")
    plt.title("Número de paquetes por segundo")
    plt.xlabel("k paquetes/s")
    plt.ylabel("Probabilidad")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "poisson_counts.png")
    plt.close()

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
        plt.hist(deltas, bins=30, density=True, alpha=0.6, label="Datos")
    plt.plot(xs_cont, pdf, label=f"Exp(λ={lam_inter:.3f})")
    plt.title("Tiempos entre llegadas")
    plt.xlabel("segundos")
    plt.ylabel("Densidad")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "exponential_interarrivals.png")
    plt.close()

    # Fase 2.3: Conjunta (Protocolo y Tamaño)
    cont = contingency_protocol_size(protos, sizes, threshold=500)
    # Tabla en CSV
    rows = []
    for (prot, sizecat), prob in sorted(cont.table.items()):
        rows.append({"protocol": prot, "size_cat": sizecat, "prob": prob})
    df = pd.DataFrame(rows)
    df.to_csv(outdir / "contingency.csv", index=False)

    # Fase 3: Detección de anomalías
    lam = lam_counts
    k_thresh = poisson_anomaly_threshold(lam, z=3.0)
    anomalies = [(sec, cnt) for sec, cnt in counts.items() if cnt > k_thresh]
    pd.DataFrame(anomalies, columns=["second", "count"]).to_csv(outdir / "anomalies.csv", index=False)

    # Reporte breve en consola
    print("Fase 2.1 Poisson:")
    print(f"  λ (por conteos) = {lam_counts:.6f}")
    print("Fase 2.2 Exponencial:")
    print(f"  λ (por interarribos) = {lam_inter:.6f}")
    print("Fase 2.3 Conjunta (TCP/UDP x Tamaño≤/>500):")
    print(f"  P(TCP) = {cont.p_tcp:.6f}")
    print(f"  P(Grande) = {cont.p_grande:.6f}")
    print(f"  P(Grande|TCP) = {cont.p_grande_given_tcp:.6f}")
    print(f"  Independencia (TCP vs Grande): {cont.independent}")
    print("Fase 3 Umbral de anomalía (3σ):")
    print(f"  Umbral k > {k_thresh} (con λ={lam:.6f})")
    print(f"  Anomalías encontradas: {len(anomalies)}")


if __name__ == "__main__":
    main()
