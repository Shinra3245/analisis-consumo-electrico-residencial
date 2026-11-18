#!/usr/bin/env python3
"""Detección de anomalías en perfiles ResStock (piloto de 10 perfiles) con evaluación sintética.

Uso (desde la raíz del repositorio):
    python analitica/anomalias_resstock.py

Entrada : datos/resstock_perfiles_piloto.parquet   (bldg_id, timestamp_fin_local[EST, fin de intervalo], electricidad_kwh)
          datos/resstock_seleccion_propuesta.csv   (estado, tipo_vivienda, peso_viviendas por bldg_id)
Salidas : analitica/salidas/gold_resstock_profile_summary.csv
          analitica/salidas/gold_resstock_monthly.csv
          analitica/salidas/gold_resstock_pattern.csv
          analitica/salidas/gold_anomaly_metrics.csv
          analitica/salidas/gold_anomaly_sensitivity.csv
          analitica/salidas/gold_anomaly_cases.csv
          analitica/salidas/gold_anomaly_case_series.csv

QUÉ ES "ATÍPICO" (definición escrita antes de elegir parámetros)
  Una hora de un perfil es atípica si su consumo se aleja de lo normal para ese MISMO perfil en horas
  comparables (mismo mes, mismo tipo de día [laboral/fin de semana] y misma hora). La línea base es la
  mediana de esa celda. Tres categorías, con reglas distintas porque sus distribuciones lo son:
    aumento  : score robusto (desviación respecto a la mediana, en unidades de MAD) >= z_up
    caida    : consumo <= ratio_down x línea base, solo donde la línea base >= mediana horaria del perfil
               (una caída está acotada por 0: un score simétrico en MAD casi nunca la alcanzaría)
    faltante : valor ausente (regla determinista, no estadística)
  Aumento y caída exigen al menos MIN_RUN horas consecutivas para generar una alerta.

PROTOCOLO DE EVALUACIÓN
  1. Se hace una COPIA de los datos; los originales no se modifican.
  2. En la copia se inyectan eventos sintéticos etiquetados (aumentos, caídas y faltantes).
  3. Los perfiles se dividen en calibración (NY: se eligen z_up y ratio_down) y evaluación (CO: se mide).
  4. Precision/recall/F1 se calculan a nivel de EVENTO, solo contra las etiquetas sintéticas.
Los eventos son sintéticos: demuestran la lógica del método, no son hechos reales del sistema eléctrico.
Las horas están en EST fijo (como publica ResStock); NO se convirtieron a hora local.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261117
N_SPIKES, N_DROPS, N_MISSING = 8, 8, 4            # por perfil
SPIKE_LEN, DROP_LEN, MISSING_LEN = (3, 6), (6, 12), (6, 24)  # horas, rango inclusivo
SPIKE_LEVELS = {"low": 0.5, "mid": 1.0, "high": 2.0}   # múltiplo del percentil 95 horario del perfil
DROP_LEVELS = {"low": 0.50, "mid": 0.75, "high": 0.95}  # fracción del consumo que se elimina
SCALE_FLOOR_FRAC = 0.10   # piso de escala = 10 % de la mediana horaria del perfil
SCALE_FLOOR_ABS = 0.01    # kWh
Z_GRID = np.arange(3.0, 20.01, 1.0)
RATIO_GRID = np.arange(0.10, 0.5001, 0.05)
MIN_RUN = 2  # horas consecutivas para alertar aumento/caída (explorado 1-3 sobre calibración; ver sensibilidad)
CALIBRATION_STATE, EVALUATION_STATE = "NY", "CO"
CONTEXT_HOURS = 48

CATEGORIES = ("aumento", "caida", "faltante")


# ----------------------------------------------------------------------------
# Carga y preparación
# ----------------------------------------------------------------------------
def load_hourly(parquet: Path, selection: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_parquet(parquet)
    need = {"bldg_id", "timestamp_fin_local", "electricidad_kwh"}
    if not need.issubset(raw.columns):
        raise SystemExit(f"Columnas inesperadas en {parquet}: {list(raw.columns)}")
    if raw["electricidad_kwh"].isna().any() or (raw["electricidad_kwh"] < 0).any():
        raise SystemExit("El parquet contiene nulos o consumos negativos; revisar antes de continuar.")
    # La marca es el FIN del intervalo (EST). Se asigna cada intervalo a su hora de inicio.
    start = raw["timestamp_fin_local"] - pd.Timedelta(minutes=15)
    raw = raw.assign(hour_start=start.dt.floor("h"))
    hourly = (raw.groupby(["bldg_id", "hour_start"])
                 .agg(kwh=("electricidad_kwh", "sum"), n=("electricidad_kwh", "size"))
                 .reset_index())
    if (hourly["n"] != 4).any():
        raise SystemExit("Hay horas con menos de 4 intervalos de 15 min.")
    hourly["kwh"] = hourly["kwh"].astype(float)
    hourly = hourly.drop(columns="n")
    hourly["month"] = hourly["hour_start"].dt.month
    hourly["hour"] = hourly["hour_start"].dt.hour
    hourly["day_type"] = np.where(hourly["hour_start"].dt.day_of_week >= 5, "weekend", "weekday")

    sel = pd.read_csv(selection)
    meta = (sel[sel["bldg_id"].isin(hourly["bldg_id"].unique())]
            .rename(columns={"estado": "state_code", "tipo_vivienda": "housing_type",
                             "peso_viviendas": "profile_weight"})
            [["bldg_id", "state_code", "housing_type", "profile_weight"]]
            .drop_duplicates("bldg_id"))
    if len(meta) != hourly["bldg_id"].nunique():
        raise SystemExit("Faltan metadatos (estado/tipo de vivienda) para algún perfil.")
    return hourly, meta


# ----------------------------------------------------------------------------
# Línea base robusta por perfil: mediana/MAD por (mes, tipo de día, hora)
# ----------------------------------------------------------------------------
def fit_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """df: filas de UN perfil con columna kwh (puede tener NaN). Devuelve tabla de celdas."""
    med_profile = float(np.nanmedian(df["kwh"]))
    floor = max(SCALE_FLOOR_FRAC * med_profile, SCALE_FLOOR_ABS)

    def cell(s: pd.Series) -> pd.Series:
        v = s.dropna().values
        m = np.median(v)
        mad = np.median(np.abs(v - m))
        return pd.Series({"baseline_kwh": m, "scale_kwh": max(1.4826 * mad, floor), "n_obs": len(v)})

    return df.groupby(["month", "day_type", "hour"]).kwh.apply(cell).unstack().reset_index()


def score_profile(df: pd.DataFrame) -> pd.DataFrame:
    base = fit_baseline(df)
    out = df.merge(base, on=["month", "day_type", "hour"], how="left")
    out["score"] = (out["kwh"] - out["baseline_kwh"]) / out["scale_kwh"]
    out["ratio"] = out["kwh"] / out["baseline_kwh"]
    out["profile_median"] = float(np.nanmedian(df["kwh"]))
    return out


def raw_flags(scored: pd.DataFrame, z_up: float, ratio_down: float) -> pd.Series:
    cat = pd.Series("", index=scored.index, dtype=object)
    cat[(scored["score"] >= z_up).fillna(False)] = "aumento"
    down = (scored["ratio"] <= ratio_down) & (scored["baseline_kwh"] >= scored["profile_median"])
    cat[down.fillna(False)] = "caida"
    cat[scored["kwh"].isna()] = "faltante"
    return cat


# ----------------------------------------------------------------------------
# Inyección de eventos sintéticos sobre una COPIA
# ----------------------------------------------------------------------------
def inject(df: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (copia con eventos, tabla de eventos). No modifica df."""
    d = df.copy().reset_index(drop=True)
    d["kwh_original"] = d["kwh"]
    n = len(d)
    p95 = float(np.quantile(d["kwh"], 0.95))
    med = float(np.median(d["kwh"]))
    base0 = fit_baseline(df)  # solo para decidir DÓNDE tiene sentido una caída (no para detectar)
    d = d.merge(base0[["month", "day_type", "hour", "baseline_kwh"]],
                on=["month", "day_type", "hour"], how="left").rename(columns={"baseline_kwh": "_b0"})
    kcol = d.columns.get_loc("kwh")
    taken = np.zeros(n, dtype=bool)
    events = []

    def free(i0: int, ln: int) -> bool:
        lo, hi = max(0, i0 - 24), min(n, i0 + ln + 24)  # margen de 24 h entre eventos
        return not taken[lo:hi].any()

    def place(kind: str, count: int, length: tuple[int, int], levels: dict | None):
        placed, tries = 0, 0
        while placed < count and tries < 5000:
            tries += 1
            ln = int(rng.integers(length[0], length[1] + 1))
            i0 = int(rng.integers(0, n - ln))
            if not free(i0, ln):
                continue
            seg = slice(i0, i0 + ln)
            if kind == "caida" and d["_b0"].iloc[seg].mean() < med:
                continue  # no se inyectan caídas donde lo normal ya es casi nulo
            level = ""
            if kind == "aumento":
                level = rng.choice(list(levels))
                d.iloc[seg, kcol] = d["kwh"].iloc[seg].values + levels[level] * p95
            elif kind == "caida":
                level = rng.choice(list(levels))
                d.iloc[seg, kcol] = d["kwh"].iloc[seg].values * (1.0 - levels[level])
            else:
                d.iloc[seg, kcol] = np.nan
            taken[i0:i0 + ln] = True
            events.append({"category": kind, "magnitude": level, "i0": i0, "i1": i0 + ln - 1})
            placed += 1

    place("aumento", N_SPIKES, SPIKE_LEN, SPIKE_LEVELS)
    place("caida", N_DROPS, DROP_LEN, DROP_LEVELS)
    place("faltante", N_MISSING, MISSING_LEN, None)
    d = d.drop(columns="_b0")
    ev = pd.DataFrame(events).sort_values("i0").reset_index(drop=True)
    ev["event_id"] = [f"e{i:02d}" for i in range(len(ev))]
    return d, ev


# ----------------------------------------------------------------------------
# Evaluación a nivel de evento
# ----------------------------------------------------------------------------
def alerts_from_flags(cat: pd.Series, min_run: int) -> pd.DataFrame:
    """Agrupa horas consecutivas de la misma categoría en alertas; aumento/caída exigen min_run horas."""
    rows, i, n = [], 0, len(cat)
    vals = cat.values
    while i < n:
        if vals[i] == "":
            i += 1
            continue
        j = i
        while j + 1 < n and vals[j + 1] == vals[i]:
            j += 1
        need = 1 if vals[i] == "faltante" else min_run
        if (j - i + 1) >= need:
            rows.append({"category": vals[i], "i0": i, "i1": j})
        i = j + 1
    return pd.DataFrame(rows, columns=["category", "i0", "i1"])


def evaluate_profile(scored: pd.DataFrame, events: pd.DataFrame, z_up: float, ratio_down: float, min_run: int):
    alerts = alerts_from_flags(raw_flags(scored, z_up, ratio_down), min_run)
    ev = events.copy()

    def hit(row_i0, row_i1, category):
        m = alerts[(alerts["category"] == category) & (alerts["i0"] <= row_i1) & (alerts["i1"] >= row_i0)]
        return len(m) > 0

    ev["detected"] = [hit(r.i0, r.i1, r.category) for r in ev.itertuples()]
    alerts["true_alert"] = [
        len(ev[(ev["category"] == a.category) & (ev["i0"] <= a.i1) & (ev["i1"] >= a.i0)]) > 0
        for a in alerts.itertuples()
    ]
    return ev, alerts


def alert_hours(alerts: pd.DataFrame, n: int) -> pd.Series:
    out = pd.Series("", index=range(n), dtype=object)
    for a in alerts.itertuples():
        out.iloc[a.i0:a.i1 + 1] = a.category
    return out


def prf(n_events: int, n_detected: int, n_alerts: int, n_true_alerts: int) -> dict:
    recall = n_detected / n_events if n_events else np.nan
    precision = n_true_alerts / n_alerts if n_alerts else np.nan
    f1 = (2 * precision * recall / (precision + recall)
          if n_alerts and n_events and (precision + recall) > 0 else np.nan)
    return {"n_events": n_events, "n_detected": n_detected, "recall": recall,
            "n_alerts": n_alerts, "n_true_alerts": n_true_alerts, "precision": precision, "f1": f1}


def aggregate(ev_all: pd.DataFrame, al_all: pd.DataFrame, categories=CATEGORIES) -> dict:
    e = ev_all[ev_all["category"].isin(categories)]
    a = al_all[al_all["category"].isin(categories)]
    return prf(len(e), int(e["detected"].sum()), len(a), int(a["true_alert"].sum()))


# ----------------------------------------------------------------------------
def run(root: Path) -> None:
    out = root / "analitica" / "salidas"
    out.mkdir(parents=True, exist_ok=True)
    hourly, meta = load_hourly(root / "datos" / "resstock_perfiles_piloto.parquet",
                               root / "datos" / "resstock_seleccion_propuesta.csv")
    meta = meta.sort_values(["state_code", "housing_type"]).reset_index(drop=True)
    profiles = {b: g.sort_values("hour_start").reset_index(drop=True) for b, g in hourly.groupby("bldg_id")}

    # --- Tablas descriptivas (sobre datos ORIGINALES) ---------------------------
    summ = (hourly.groupby("bldg_id").agg(
                annual_kwh=("kwh", "sum"), mean_hour_kwh=("kwh", "mean"),
                peak_hour_kwh=("kwh", "max"), n_hours=("kwh", "size"))
            .reset_index().merge(meta, on="bldg_id"))
    summ.to_csv(out / "gold_resstock_profile_summary.csv", index=False, lineterminator="\n", float_format="%.4f")

    monthly = hourly.groupby(["bldg_id", "month"]).agg(kwh_month=("kwh", "sum")).reset_index()
    monthly = monthly.merge(meta[["bldg_id", "state_code", "housing_type"]], on="bldg_id")
    monthly.to_csv(out / "gold_resstock_monthly.csv", index=False, lineterminator="\n", float_format="%.4f")

    pat = (hourly.groupby(["bldg_id", "month", "day_type", "hour"]).kwh
                 .agg(median_kwh="median", mean_kwh="mean", p10_kwh=lambda s: s.quantile(.10),
                      p90_kwh=lambda s: s.quantile(.90), n_obs="size").reset_index()
                 .merge(meta[["bldg_id", "state_code", "housing_type"]], on="bldg_id"))
    pat.to_csv(out / "gold_resstock_pattern.csv", index=False, lineterminator="\n", float_format="%.4f")

    # --- Copia de prueba con eventos sintéticos ----------------------------------
    injected, events = {}, {}
    for b, g in profiles.items():
        rng = np.random.default_rng([SEED, int(b)])
        injected[b], events[b] = inject(g, rng)
    scored = {b: score_profile(d) for b, d in injected.items()}

    cal_ids = meta.loc[meta["state_code"] == CALIBRATION_STATE, "bldg_id"].tolist()
    ev_ids = meta.loc[meta["state_code"] == EVALUATION_STATE, "bldg_id"].tolist()

    def collect(ids, z_up, ratio_down, min_run=MIN_RUN):
        evs, als = [], []
        for b in ids:
            e, a = evaluate_profile(scored[b], events[b], z_up, ratio_down, min_run)
            e["bldg_id"], a["bldg_id"] = b, b
            evs.append(e)
            als.append(a)
        return pd.concat(evs, ignore_index=True), pd.concat(als, ignore_index=True)

    # --- Calibración (solo con el conjunto de calibración; cada categoría por separado) ----
    def best_param(grid, cat, make_args, conservative_is_high):
        res = []
        for v in grid:
            e, a = collect(cal_ids, *make_args(v))
            f1 = aggregate(e, a, (cat,))["f1"]
            res.append((v, 0.0 if pd.isna(f1) else f1))
        top = max(f for _, f in res)
        tied = [v for v, f in res if f >= top - 1e-12]
        return (max(tied) if conservative_is_high else min(tied)), top

    z_up, f1_up = best_param(Z_GRID, "aumento", lambda v: (v, 0.0), True)
    ratio_down, f1_dn = best_param(RATIO_GRID, "caida", lambda v: (1e9, v), False)
    print(f"Calibrado en {CALIBRATION_STATE}: z_up = {z_up:g} (F1 aumento {f1_up:.3f}); "
          f"ratio_down = {ratio_down:.2f} (F1 caída {f1_dn:.3f}); min_run = {MIN_RUN} h")

    # --- Métricas ------------------------------------------------------------------
    mrows = []
    for set_name, ids in (("calibration", cal_ids), ("evaluation", ev_ids)):
        e, a = collect(ids, z_up, ratio_down)
        for cat in CATEGORIES + ("aumento+caida",):
            cats = ("aumento", "caida") if cat == "aumento+caida" else (cat,)
            mrows.append({"eval_set": set_name, "category": cat, "magnitude": "all", **aggregate(e, a, cats)})
        for cat in ("aumento", "caida"):  # sensibilidad por magnitud: solo recall
            for lvl in ("low", "mid", "high"):
                sub = e[(e["category"] == cat) & (e["magnitude"] == lvl)]
                mrows.append({"eval_set": set_name, "category": cat, "magnitude": lvl,
                              "n_events": len(sub), "n_detected": int(sub["detected"].sum()),
                              "recall": sub["detected"].mean() if len(sub) else np.nan,
                              "n_alerts": np.nan, "n_true_alerts": np.nan, "precision": np.nan, "f1": np.nan})
    metrics = pd.DataFrame(mrows)
    metrics["z_up"], metrics["ratio_down"], metrics["min_run_hours"] = z_up, ratio_down, MIN_RUN
    metrics["method"] = "median_by_month_daytype_hour"
    metrics["is_synthetic_labels"] = True
    metrics.to_csv(out / "gold_anomaly_metrics.csv", index=False, lineterminator="\n", float_format="%.4f")

    # --- Sensibilidad a la duración mínima de alerta (evaluación, umbrales ya calibrados) ----
    srows = []
    for mr in (1, 2, 3):
        e, a = collect(ev_ids, z_up, ratio_down, min_run=mr)
        for cat in ("aumento", "caida"):
            srows.append({"min_run_hours": mr, "category": cat, **aggregate(e, a, (cat,))})
    pd.DataFrame(srows).to_csv(out / "gold_anomaly_sensitivity.csv", index=False, lineterminator="\n", float_format="%.4f")

    # --- Casos para el tablero (conjunto de evaluación) --------------------------
    e_eval, a_eval = collect(ev_ids, z_up, ratio_down)
    chosen = []

    def first(df):
        return df.sort_values(["bldg_id", "i0"]).iloc[0] if len(df) else None

    det = e_eval[e_eval["detected"]]
    for cat, magn in (("aumento", "mid"), ("caida", "mid"), ("faltante", "")):
        cand = det[(det["category"] == cat) & (det["magnitude"] == magn)]
        r = first(cand if len(cand) else det[det["category"] == cat])
        if r is not None:
            chosen.append(("synthetic_detected", r.bldg_id, r.category, int(r.i0), int(r.i1), r.magnitude))
    r = first(e_eval[(~e_eval["detected"]) & (e_eval["category"] != "faltante")])
    if r is not None:
        chosen.append(("synthetic_missed", r.bldg_id, r.category, int(r.i0), int(r.i1), r.magnitude))
    r = first(a_eval[(~a_eval["true_alert"]) & (a_eval["category"] != "faltante")])
    if r is not None:
        chosen.append(("unlabeled_alert", r.bldg_id, r.category, int(r.i0), int(r.i1), ""))

    cases, series = [], []
    for k, (kind, b, cat, i0, i1, magn) in enumerate(chosen, start=1):
        b = int(b)
        sc = scored[b]
        m = meta[meta["bldg_id"] == b].iloc[0]
        win = sc.iloc[i0:i1 + 1]
        if cat == "aumento":
            metric, value = "score_robusto_max", float(win["score"].max())
            rule = f"score robusto >= {z_up:g} durante >= {MIN_RUN} h seguidas"
        elif cat == "caida":
            metric, value = "razon_vs_linea_base_min", float(win["ratio"].min())
            rule = f"consumo <= {ratio_down:.0%} de la línea base durante >= {MIN_RUN} h seguidas"
        else:
            metric, value = "valor_ausente", np.nan
            rule = "valor ausente (regla determinista, no estadística)"
        has_obs = win["kwh"].notna().all()
        # Un caso sin etiqueta o no detectado se rotula por separado; solo los sintéticos detectados "aciertan".
        if kind == "synthetic_detected":
            outcome = "detectado"
        elif kind == "synthetic_missed":
            outcome = "no_detectado"
        else:
            outcome = "alerta_sin_etiqueta"
        cid = f"caso_{k}"
        cases.append({
            "case_id": cid, "kind": kind, "outcome": outcome, "bldg_id": b, "state_code": m["state_code"],
            "housing_type": m["housing_type"], "category": cat, "magnitude": magn,
            "start_est": win["hour_start"].iloc[0], "end_est": win["hour_start"].iloc[-1], "n_hours": len(win),
            "observed_kwh": float(win["kwh"].sum()) if win["kwh"].notna().any() else np.nan,
            "baseline_kwh": float(win["baseline_kwh"].sum()),
            "diff_kwh": float(win["kwh"].sum() - win["baseline_kwh"].sum()) if has_obs else np.nan,
            "trigger_metric": metric, "trigger_value": value, "rule": rule,
            "is_synthetic": kind != "unlabeled_alert",
        })
        lo, hi = max(0, i0 - CONTEXT_HOURS), min(len(sc), i1 + CONTEXT_HOURS + 1)
        ctx = sc.iloc[lo:hi]
        _, al_b = evaluate_profile(sc, events[b], z_up, ratio_down, MIN_RUN)
        hours_flag = alert_hours(al_b, len(sc)).iloc[lo:hi]
        series.append(pd.DataFrame({
            "case_id": cid, "timestamp_start_est": ctx["hour_start"].values,
            "observed_kwh": ctx["kwh"].values, "original_kwh": ctx["kwh_original"].values,
            "baseline_kwh": ctx["baseline_kwh"].values, "score": ctx["score"].values,
            "ratio_to_baseline": ctx["ratio"].values, "alert": hours_flag.values,
        }))
    pd.DataFrame(cases).to_csv(out / "gold_anomaly_cases.csv", index=False, lineterminator="\n", float_format="%.4f")
    pd.concat(series, ignore_index=True).to_csv(out / "gold_anomaly_case_series.csv", index=False, lineterminator="\n", float_format="%.4f")

    # --- Resumen en consola ----------------------------------------------------------
    show = metrics[metrics["magnitude"] == "all"][
        ["eval_set", "category", "n_events", "n_detected", "recall", "n_alerts", "precision", "f1"]]
    print("\nMétricas (etiquetas SINTÉTICAS, nivel de evento):")
    print(show.round(3).to_string(index=False))
    print("\nRecall por magnitud (evaluación):")
    print(metrics[(metrics["eval_set"] == "evaluation") & (metrics["magnitude"] != "all")]
          [["category", "magnitude", "n_events", "recall"]].round(3).to_string(index=False))
    print("\nSensibilidad a MIN_RUN (evaluación):")
    print(pd.DataFrame(srows)[["min_run_hours", "category", "recall", "n_alerts", "precision", "f1"]].round(3).to_string(index=False))
    print("\nCasos:", [(c["case_id"], c["kind"], c["category"]) for c in cases])
    print("Salidas escritas en", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    run(ap.parse_args().root)
