from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
from collections import Counter
import math


def group_counts_per_second(timestamps_sec: List[float]) -> Dict[int, int]:
    """Cuenta paquetes por segundo (redondeando hacia abajo cada timestamp)."""
    buckets: Dict[int, int] = Counter()
    for ts in timestamps_sec:
        buckets[int(math.floor(ts))] += 1
    return dict(buckets)


def estimate_lambda_from_counts(counts_per_sec: Dict[int, int]) -> float:
    if not counts_per_sec:
        return float('nan')
    total = sum(counts_per_sec.values())
    # duración = número de segundos observados (incluyendo segundos con 0 cuentas)
    secs = (max(counts_per_sec.keys()) - min(counts_per_sec.keys()) + 1)
    return total / secs if secs > 0 else float('nan')


def expand_counts_with_zeros(counts_per_sec: Dict[int, int]) -> List[int]:
    """Devuelve el vector de cuentas por cada segundo del rango observado, rellenando con 0 donde no hay llegadas."""
    if not counts_per_sec:
        return []
    smin, smax = min(counts_per_sec.keys()), max(counts_per_sec.keys())
    return [counts_per_sec.get(s, 0) for s in range(smin, smax + 1)]


def index_of_dispersion(counts: List[int]) -> float:
    """Índice de dispersión = Var(X)/E[X] (≈1 en Poisson). Devuelve NaN si media=0."""
    n = len(counts)
    if n == 0:
        return float('nan')
    mean = sum(counts) / n
    if mean == 0:
        return float('nan')
    var = sum((x - mean) ** 2 for x in counts) / (n - 1) if n > 1 else 0.0
    return var / mean


def interarrival_times(timestamps_sec: List[float]) -> List[float]:
    times = sorted(timestamps_sec)
    if len(times) < 2:
        return []
    return [t2 - t1 for t1, t2 in zip(times[:-1], times[1:])]


def estimate_lambda_from_interarrivals(deltas: List[float]) -> float:
    if not deltas:
        return float('nan')
    mean_delta = sum(deltas) / len(deltas)
    return 1.0 / mean_delta if mean_delta > 0 else float('nan')


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def exponential_pdf(x: float, lam: float) -> float:
    return lam * math.exp(-lam * x) if x >= 0 else 0.0


@dataclass
class Contingency:
    table: Dict[Tuple[str, str], float]
    p_tcp: float
    p_grande: float
    p_grande_given_tcp: float
    independent: bool


def contingency_protocol_size(protocols: List[int], sizes: List[int], threshold: int = 500) -> Contingency:
    """Construye tabla conjunta P(Protocol, Tam) con tamaños discretizados <=threshold (Pequeño) y >threshold (Grande)."""
    if len(protocols) != len(sizes):
        raise ValueError("protocols y sizes deben tener misma longitud")
    n = len(protocols)
    if n == 0:
        return Contingency({}, float('nan'), float('nan'), float('nan'), False)

    def proto_name(p: int) -> str:
        return 'TCP' if p == 6 else ('UDP' if p == 17 else str(p))

    def size_cat(s: int) -> str:
        return 'Pequeño' if s <= threshold else 'Grande'

    pairs = [(proto_name(p), size_cat(s)) for p, s in zip(protocols, sizes)]
    c = Counter(pairs)
    table: Dict[Tuple[str, str], float] = {k: v / n for k, v in c.items()}

    p_tcp = sum(v for (prot, _), v in table.items() if prot == 'TCP')
    p_grande = sum(v for (_, sc), v in table.items() if sc == 'Grande')
    p_tcp_and_grande = table.get(('TCP', 'Grande'), 0.0)
    p_grande_given_tcp = (p_tcp_and_grande / p_tcp) if p_tcp > 0 else float('nan')
    independent = math.isfinite(p_grande_given_tcp) and abs(p_grande_given_tcp - p_grande) < 1e-6

    return Contingency(table, p_tcp, p_grande, p_grande_given_tcp, independent)


def poisson_anomaly_threshold(lam: float, z: float = 3.0) -> int:
    """Umbral k tal que k > lam + z*sqrt(lam) indica anomalía (regla simple)."""
    if lam <= 0:
        return 0
    mean = lam
    std = math.sqrt(lam)
    k = math.floor(mean + z * std)
    return k
