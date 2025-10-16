from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class SimulationResult:
    duration: float
    arrivals: int
    departures: int
    rho: Optional[float]
    lambda_eff: float
    mu_eff: Optional[float]
    avg_wait_in_queue: float
    avg_time_in_system: float
    L_time_avg: float
    Lq_time_avg: float
    busy_fraction: float
    timeline: List[Tuple[float, int]] = field(default_factory=list)  # (time, N(t))


class MM1Simulator:
    """
    Discrete-event simulator for an M/M/1 queue.

    - Arrivals: Poisson process with rate lambda (exponential inter-arrival times).
    - Service times: Exponential with rate mu.
    - Single server, FIFO discipline.

    Notes on metrics:
    - L_time_avg: time-average number in the system N(t).
    - Lq_time_avg: time-average number in queue (excluding service).
    - avg_wait_in_queue (Wq) and avg_time_in_system (W) are empirical means
      over served customers.
    - busy_fraction ~= empirical utilization (rho) over the simulated horizon.
    """

    def __init__(self, arrival_rate: float, service_rate: float, seed: Optional[int] = None):
        if arrival_rate <= 0:
            raise ValueError("arrival_rate (lambda) must be > 0")
        if service_rate <= 0:
            raise ValueError("service_rate (mu) must be > 0")
        self.lambda_ = float(arrival_rate)
        self.mu = float(service_rate)
        self.rng = random.Random(seed)

    def _exp(self, rate: float) -> float:
        return self.rng.expovariate(rate)

    def run(self, duration: Optional[float] = None, max_arrivals: Optional[int] = None,
            record_timeline: bool = True, warmup_time: float = 0.0) -> SimulationResult:
        if duration is None and max_arrivals is None:
            raise ValueError("Provide duration (seconds) or max_arrivals")
        if warmup_time < 0:
            warmup_time = 0.0

        t = 0.0
        next_arrival = self._exp(self.lambda_)
        next_departure = math.inf  # no job in service initially

        # State
        queue: List[float] = []  # arrival times waiting
        server_busy = False
        current_job_arrival: Optional[float] = None
        current_job_start: Optional[float] = None

        # Metrics accumulators
        last_event_time = 0.0
        area_N = 0.0  # integral of N(t) after warm-up
        area_Q = 0.0  # integral of Q(t) after warm-up
        busy_time = 0.0  # after warm-up

        total_wait = 0.0  # measured after warm-up
        total_system = 0.0  # measured after warm-up
        served = 0  # total served (for info)
        served_measured = 0  # served after warm-up (for averages)
        arrivals = 0  # total arrivals
        arrivals_measured = 0  # arrivals after warm-up (for lambda_eff)

        timeline: List[Tuple[float, int]] = []

        def N_now() -> int:
            # number in system = queue length + (1 if busy else 0)
            return len(queue) + (1 if server_busy else 0)

        # Main loop
        while True:
            if duration is not None and t >= duration:
                break
            if max_arrivals is not None and arrivals >= max_arrivals and not server_busy and len(queue) == 0:
                # stop once all arrived are served
                break

            # Determine next event time
            t_next = min(next_arrival, next_departure)

            # Cap by duration if provided
            if duration is not None and t_next > duration:
                t_next = duration

            # Update time-average integrals up to t_next, but only part after warm-up
            dt_total = t_next - last_event_time
            if dt_total < 0:
                dt_total = 0.0

            # Portion that counts toward metrics
            start_eff = max(last_event_time, warmup_time)
            end_eff = t_next
            dt_eff = max(0.0, end_eff - start_eff)

            if dt_eff > 0:
                area_N += N_now() * dt_eff
                area_Q += len(queue) * dt_eff
                if server_busy:
                    busy_time += dt_eff
            last_event_time = t_next
            t = t_next

            # Record timeline
            if record_timeline:
                timeline.append((t, N_now()))

            # Decide which event fires (if at duration boundary, there may be none)
            if duration is not None and t >= duration:
                # At the horizon; don't process further events
                continue

            if next_arrival <= next_departure:
                # Arrival event
                arrivals += 1
                if t >= warmup_time:
                    arrivals_measured += 1
                if not server_busy:
                    # Start service immediately
                    server_busy = True
                    current_job_arrival = t
                    current_job_start = t
                    service_time = self._exp(self.mu)
                    next_departure = t + service_time
                else:
                    # join queue
                    queue.append(t)
                # Schedule next arrival
                next_arrival = t + self._exp(self.lambda_)

                # If a max_arrivals cap is set and reached, we won't schedule more arrivals beyond cap
                if max_arrivals is not None and arrivals >= max_arrivals:
                    next_arrival = math.inf
            else:
                # Departure event
                served += 1
                # Compute metrics for the departing job (the one in service)
                if current_job_arrival is not None and current_job_start is not None:
                    wait = current_job_start - current_job_arrival
                    system_time = t - current_job_arrival
                    if t >= warmup_time:
                        total_wait += wait
                        total_system += system_time
                        served_measured += 1

                # Start next job if any
                if len(queue) > 0:
                    arrival_time = queue.pop(0)
                    current_job_arrival = arrival_time
                    current_job_start = t
                    service_time = self._exp(self.mu)
                    next_departure = t + service_time
                    # server stays busy
                else:
                    # Queue empty: server becomes idle
                    server_busy = False
                    current_job_arrival = None
                    current_job_start = None
                    next_departure = math.inf

        sim_duration = last_event_time if duration is not None else t
        # Measured duration excludes warm-up
        measured_duration = max(0.0, sim_duration - warmup_time)

        # Empirical rates
        lambda_eff = arrivals_measured / measured_duration if measured_duration > 0 else float('nan')
        mu_eff = (served_measured / busy_time) if busy_time > 0 else None
        rho_emp = busy_time / measured_duration if measured_duration > 0 else None

        avg_wait = (total_wait / served_measured) if served_measured > 0 else 0.0
        avg_system = (total_system / served_measured) if served_measured > 0 else 0.0
        L_avg = area_N / measured_duration if measured_duration > 0 else 0.0
        Lq_avg = area_Q / measured_duration if measured_duration > 0 else 0.0

        # Theoretical rho may be lambda/mu if stable
        rho_theo = None
        if self.mu > 0:
            rho_theo = self.lambda_ / self.mu

        return SimulationResult(
            duration=sim_duration,
            arrivals=arrivals,
            departures=served,
            rho=rho_theo,
            lambda_eff=lambda_eff,
            mu_eff=mu_eff,
            avg_wait_in_queue=avg_wait,
            avg_time_in_system=avg_system,
            L_time_avg=L_avg,
            Lq_time_avg=Lq_avg,
            busy_fraction=rho_emp if rho_emp is not None else 0.0,
            timeline=timeline,
        )
