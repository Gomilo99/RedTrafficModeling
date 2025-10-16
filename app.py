from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from src.data.loaders import read_network_csv, estimate_rates_from_records
from src.sim.queue_mm1 import MM1Simulator


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RedTrafficModeling - M/M/1 Demo")
        self.geometry("720x520")

        self.csv_path: Optional[str] = None
        self.lambda_var = tk.StringVar(value="")
        self.mu_var = tk.StringVar(value="")
        self.duration_var = tk.StringVar(value="300")
        self.arrivals_cap_var = tk.StringVar(value="")
        self.mean_service_ms_var = tk.StringVar(value="")
        self.warmup_var = tk.StringVar(value="0")

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # File selection
        file_row = ttk.Frame(frm)
        file_row.pack(fill=tk.X, pady=5)
        ttk.Label(file_row, text="CSV de tráfico:").pack(side=tk.LEFT)
        self.file_entry = ttk.Entry(file_row)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(file_row, text="Abrir...", command=self.on_open_file).pack(side=tk.LEFT)

        # Params
        params = ttk.LabelFrame(frm, text="Parámetros")
        params.pack(fill=tk.X, pady=10)

        def add_param(row, label, var):
            r = ttk.Frame(params)
            r.pack(fill=tk.X, pady=2)
            ttk.Label(r, text=label, width=24).pack(side=tk.LEFT)
            e = ttk.Entry(r, textvariable=var)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            return e

        self.lambda_entry = add_param(0, "Lambda (llegadas/seg):", self.lambda_var)
        self.mu_entry = add_param(1, "Mu (servicios/seg):", self.mu_var)
        self.duration_entry = add_param(2, "Duración sim (seg):", self.duration_var)
        self.arrivals_cap_entry = add_param(3, "Máx. llegadas (opcional):", self.arrivals_cap_var)
        self.mean_service_entry = add_param(4, "Media servicio ms (opcional):", self.mean_service_ms_var)
        self.warmup_entry = add_param(5, "Warm-up (seg, opcional):", self.warmup_var)

        # Buttons
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=10)
        ttk.Button(btns, text="Estim. parámetros desde CSV", command=self.on_estimate).pack(side=tk.LEFT)
        ttk.Button(btns, text="Simular", command=self.on_simulate).pack(side=tk.LEFT, padx=10)

        # Results
        res_frame = ttk.LabelFrame(frm, text="Resultados")
        res_frame.pack(fill=tk.BOTH, expand=True)
        self.text = tk.Text(res_frame, height=16)
        self.text.pack(fill=tk.BOTH, expand=True)

        # Footer
        ttk.Label(frm, text="M/M/1: llegadas Poisson, servicio exponencial, 1 servidor.").pack(anchor=tk.W, pady=6)

    def on_open_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if path:
            self.csv_path = path
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, path)

    def on_estimate(self):
        try:
            if not self.csv_path:
                self.csv_path = self.file_entry.get().strip() or None
            if not self.csv_path:
                messagebox.showwarning("Falta CSV", "Selecciona un archivo CSV primero.")
                return
            records = read_network_csv(self.csv_path)
            ms = self._parse_float(self.mean_service_ms_var.get())
            lam, mu = estimate_rates_from_records(records, mean_service_time_ms=ms)
            self.lambda_var.set(f"{lam:.6f}")
            self.mu_var.set(f"{mu:.6f}")
            messagebox.showinfo("Estimación lista", f"Lambda ≈ {lam:.6f}, Mu ≈ {mu:.6f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_simulate(self):
        try:
            lam = self._require_float(self.lambda_var.get(), "Lambda")
            mu = self._require_float(self.mu_var.get(), "Mu")
            duration = self._parse_float(self.duration_var.get())
            arrivals_cap = self._parse_int(self.arrivals_cap_var.get())
            warmup = self._parse_float(self.warmup_var.get()) or 0.0

            sim = MM1Simulator(lam, mu)
            res = sim.run(duration=duration if duration and duration > 0 else None,
                          max_arrivals=arrivals_cap if arrivals_cap and arrivals_cap > 0 else None,
                          record_timeline=True,
                          warmup_time=warmup)
            self._show_results(res)
        except Exception as e:
            messagebox.showerror("Error en simulación", str(e))

    def _show_results(self, res):
        self.text.delete("1.0", tk.END)
        lines = [
            f"Duración sim: {res.duration:.3f} s",
            f"Llegadas: {res.arrivals}",
            f"Salidas (atendidos): {res.departures}",
            f"Utilización teórica (rho=λ/μ): {res.rho:.3f}" if res.rho is not None else "rho teórico: N/A",
            f"Lambda empírico: {res.lambda_eff:.6f} 1/s",
            f"Mu empírico: {res.mu_eff:.6f} 1/s" if res.mu_eff is not None else "Mu empírico: N/A",
            f"Fracción ocupado (rho empírico): {res.busy_fraction:.3f}",
            f"Wq promedio: {res.avg_wait_in_queue:.6f} s",
            f"W promedio: {res.avg_time_in_system:.6f} s",
            f"L promedio (tiempo): {res.L_time_avg:.6f}",
            f"Lq promedio (tiempo): {res.Lq_time_avg:.6f}",
        ]
        self.text.insert(tk.END, "\n".join(lines))

    @staticmethod
    def _parse_float(s: str) -> Optional[float]:
        try:
            s = s.strip()
            if not s:
                return None
            return float(s)
        except Exception:
            return None

    @staticmethod
    def _parse_int(s: str) -> Optional[int]:
        try:
            s = s.strip()
            if not s:
                return None
            return int(s)
        except Exception:
            return None

    @staticmethod
    def _require_float(s: str, name: str) -> float:
        try:
            return float(s)
        except Exception:
            raise ValueError(f"{name} debe ser numérico")


if __name__ == "__main__":
    App().mainloop()
