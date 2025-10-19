from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Tuple
import csv


@dataclass
class TrafficRecord:
    timestamp: datetime
    packet_size: int
    protocol: int


def read_network_csv(path: str, tz: Optional[str] = None) -> List[TrafficRecord]:
    """
    Reads CSV with columns: Timestamp,Packet_Size,Protocol
    Timestamp format example: 20/02/2018 08:31 (day/month/year HH:MM)
    """
    records: List[TrafficRecord] = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row['Timestamp'].strip()
            # Probar múltiples formatos comunes
            fmts = [
                "%d/%m/%Y %I:%M:%S %p",  # 20/02/2018 08:31:01 AM (12h con segundos)
                "%d/%m/%Y %H:%M:%S",     # 20/02/2018 08:31:01 (24h con segundos)
                "%d/%m/%Y %H:%M",        # 20/02/2018 08:31 (24h sin segundos)
            ]
            ts: Optional[datetime] = None
            for fmt in fmts:
                try:
                    ts = datetime.strptime(ts_str, fmt)
                    break
                except Exception:
                    continue
            if ts is None:
                raise ValueError(f"Timestamp no reconocido: '{ts_str}'")
            size = int(row['Packet_Size'])
            proto = int(row['Protocol'])
            records.append(TrafficRecord(ts, size, proto))
    return records


def estimate_rates_from_records(records: List[TrafficRecord], interval_seconds: int = 60,
                                mean_service_time_ms: Optional[float] = None) -> Tuple[float, float]:
    """
    Estimate Poisson arrival rate lambda and service rate mu from traffic records.

    - lambda: estimated as average arrivals per second, grouping by fixed intervals (default 60s).
    - mu: if mean_service_time_ms provided, mu = 1000 / mean_service_time_ms (per second).
        Otherwise, a simple heuristic uses packet size to guess service time at a given link rate.
    Returns (lambda, mu)
    """
    if not records:
        raise ValueError("No records provided")

    # Group by minute (or provided interval)
    if interval_seconds <= 0:
        interval_seconds = 60

    # Sort records
    records_sorted = sorted(records, key=lambda r: r.timestamp)

    # Count per interval
    start = records_sorted[0].timestamp
    end = records_sorted[-1].timestamp
    total_seconds = max(1, int((end - start).total_seconds()) + 1)

    # Build buckets
    buckets = {}
    for rec in records_sorted:
        delta = int((rec.timestamp - start).total_seconds())
        bucket = delta // interval_seconds
        buckets[bucket] = buckets.get(bucket, 0) + 1

    total_arrivals = sum(buckets.values())
    total_time = (max(buckets.keys()) + 1) * interval_seconds if buckets else total_seconds
    lambda_est = total_arrivals / max(1, total_time)

    # Service rate estimation
    if mean_service_time_ms is not None and mean_service_time_ms > 0:
        mu_est = 1000.0 / mean_service_time_ms
    else:
        # Heuristic: assume link speed 100 Mbps, service time ~ packet_size_bytes * 8 / link_bps
        # Then convert to per-second rate mu = 1 / mean_service_time
        LINK_MBPS = 100
        link_bps = LINK_MBPS * 1_000_000
        avg_bits = sum(r.packet_size for r in records_sorted) * 8 / len(records_sorted)
        mean_service_time = avg_bits / link_bps  # seconds
        mu_est = 1.0 / mean_service_time if mean_service_time > 0 else 1.0

    return lambda_est, mu_est
