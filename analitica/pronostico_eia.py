#!/usr/bin/env python3
"""Pronóstico mensual de ventas residenciales EIA-861M (MWh) con evaluación temporal.

Uso (desde la raíz del repositorio):
    python analitica/pronostico_eia.py

Entrada : datos/eia_residencial_mensual.csv  (periodo, estado, sector, estado_dato, ventas_mwh)
Salidas : analitica/salidas/gold_eia_monthly.csv
          analitica/salidas/gold_forecast_monthly.csv
          analitica/salidas/gold_forecast_annual.csv
          analitica/salidas/gold_forecast_metrics.csv

Protocolo (ver docs/metodo-pronostico.md):
  * backtest            : se ajusta con 2018-2023 (Final) y se evalúa en 2024-2025 (Final).
                          Es la ÚNICA ventana que alimenta las métricas titulares.
  * preliminary_check   : mismo ajuste, horizonte ene-ago 2026 contra datos Preliminary.
                          Se muestra aparte; no entra en las métricas titulares.
  * forward             : se ajusta con 2018-2025 (Final) y se proyecta sep 2026-dic 2027.
                          No tiene dato real contra el cual comparar: es un escenario.
Nunca se mezclan meses al azar: la partición es siempre temporal.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

TRAIN_END_BACKTEST = "2023-12"
BACKTEST_START, BACKTEST_END = "2024-01", "2025-12"
PRELIM_START, PRELIM_END = "2026-01", "2026-08"
FORWARD_START, FORWARD_END = "2026-09", "2027-12"
MIN_DENOMINATOR_MWH = 1.0  # por debajo de esto, sMAPE no se interpreta

MODELS = ["seasonal_naive", "seasonal_mean", "log_linear_trend"]


def period_index(start: str, end: str) -> pd.PeriodIndex:
    return pd.period_range(start, end, freq="M")


# ----------------------------------------------------------------------------
# Modelos. Cada uno recibe la serie de entrenamiento (índice PeriodIndex mensual
# sin huecos) y el índice de periodos a pronosticar; devuelve un ndarray.
# ----------------------------------------------------------------------------
def seasonal_naive(train: pd.Series, horizon: pd.PeriodIndex) -> np.ndarray:
    """Repite el valor del mismo mes del último año disponible."""
    last_year = train.iloc[-12:]
    by_month = {p.month: v for p, v in last_year.items()}
    return np.array([by_month[p.month] for p in horizon], dtype=float)


def seasonal_mean(train: pd.Series, horizon: pd.PeriodIndex) -> np.ndarray:
    """Promedio histórico del mismo mes (sin tendencia)."""
    months = np.array([p.month for p in train.index])
    mean_by_month = {m: train.values[months == m].mean() for m in range(1, 13)}
    return np.array([mean_by_month[p.month] for p in horizon], dtype=float)


def log_linear_trend(train: pd.Series, horizon: pd.PeriodIndex) -> np.ndarray:
    """log(y) = a + b*t + efecto mensual. Mínimos cuadrados ordinarios."""
    t0 = train.index[0]

    def design(idx: pd.PeriodIndex) -> np.ndarray:
        t = np.array([(p - t0).n for p in idx], dtype=float)
        m = np.array([p.month for p in idx])
        dummies = np.zeros((len(idx), 11))
        for k in range(2, 13):  # enero es la categoría base
            dummies[:, k - 2] = (m == k).astype(float)
        return np.column_stack([np.ones(len(idx)), t, dummies])

    x_train = design(train.index)
    y_train = np.log(train.values)
    beta, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
    # Corrección de sesgo por retransformación (Duan smearing).
    resid = y_train - x_train @ beta
    smear = float(np.mean(np.exp(resid)))
    return np.exp(design(horizon) @ beta) * smear


MODEL_FUNCS = {
    "seasonal_naive": seasonal_naive,
    "seasonal_mean": seasonal_mean,
    "log_linear_trend": log_linear_trend,
}


# ----------------------------------------------------------------------------
# Métricas
# ----------------------------------------------------------------------------
def smape_terms(actual: np.ndarray, fc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    denom = np.abs(actual) + np.abs(fc)
    ok = denom >= MIN_DENOMINATOR_MWH
    term = np.full(actual.shape, np.nan)
    term[ok] = 200.0 * np.abs(fc[ok] - actual[ok]) / denom[ok]
    return term, ok


def compute_metrics(actual: np.ndarray, fc: np.ndarray) -> dict:
    err = fc - actual
    terms, ok = smape_terms(actual, fc)
    return {
        "n_months": int(len(actual)),
        "mae_mwh": float(np.mean(np.abs(err))),
        "rmse_mwh": float(np.sqrt(np.mean(err**2))),
        "smape_pct": float(np.nanmean(terms)) if ok.any() else np.nan,
        "n_not_interpretable": int((~ok).sum()),
    }


# ----------------------------------------------------------------------------
def load_eia(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected = {"periodo", "estado", "sector", "estado_dato", "ventas_mwh"}
    if not expected.issubset(df.columns):
        raise SystemExit(f"Columnas inesperadas en {path}: {list(df.columns)}")
    df = df[df["sector"] == "RES"].copy()
    df["period"] = pd.PeriodIndex(df["periodo"], freq="M")
    df = df.rename(columns={"estado": "state_code", "estado_dato": "data_status", "ventas_mwh": "sales_mwh"})
    if df.duplicated(["period", "state_code"]).any():
        raise SystemExit("Claves (period, state_code) duplicadas en EIA.")
    if not np.isfinite(df["sales_mwh"]).all() or (df["sales_mwh"] < 0).any():
        raise SystemExit("Hay ventas no finitas o negativas.")
    return df[["period", "state_code", "data_status", "sales_mwh"]].sort_values(["state_code", "period"])


def run(root: Path) -> None:
    src = root / "datos" / "eia_residencial_mensual.csv"
    out = root / "analitica" / "salidas"
    out.mkdir(parents=True, exist_ok=True)

    eia = load_eia(src)

    # --- Serie limpia para tablero (conserva Final / Preliminary) --------------
    eia_out = eia.copy()
    eia_out["period"] = eia_out["period"].astype(str)
    eia_out.to_csv(out / "gold_eia_monthly.csv", index=False, lineterminator="\n", float_format="%.2f")

    final = eia[eia["data_status"] == "Final"]
    prelim = eia[eia["data_status"] == "Preliminary"]

    train_idx_bt = period_index("2018-01", TRAIN_END_BACKTEST)
    train_idx_fw = period_index("2018-01", "2025-12")
    splits = [
        ("backtest", train_idx_bt, period_index(BACKTEST_START, BACKTEST_END), final, True),
        ("preliminary_check", train_idx_bt, period_index(PRELIM_START, PRELIM_END), prelim, False),
        ("forward", train_idx_fw, period_index(FORWARD_START, FORWARD_END), None, False),
    ]

    rows = []
    states = sorted(final["state_code"].unique())
    for st in states:
        s_final = final[final["state_code"] == st].set_index("period")["sales_mwh"]
        for split, train_idx, horizon, actual_df, headline in splits:
            if not train_idx.isin(s_final.index).all():
                raise SystemExit(f"{st}: faltan meses finales de entrenamiento para {split}.")
            train = s_final.loc[train_idx]
            actual_s = None
            status_s = None
            if actual_df is not None:
                a = actual_df[actual_df["state_code"] == st].set_index("period")
                actual_s, status_s = a["sales_mwh"], a["data_status"]
            for model in MODELS:
                fc = MODEL_FUNCS[model](train, horizon)
                for p, f in zip(horizon, fc):
                    act = np.nan
                    stt = ""
                    if actual_s is not None and p in actual_s.index:
                        act, stt = float(actual_s.loc[p]), status_s.loc[p]
                    rows.append((st, str(p), model, split, stt, act, float(f), headline))

    monthly = pd.DataFrame(
        rows,
        columns=["state_code", "period", "model_id", "split", "actual_status",
                 "actual_mwh", "forecast_mwh", "in_headline_metrics"],
    )
    monthly.to_csv(out / "gold_forecast_monthly.csv", index=False, lineterminator="\n", float_format="%.2f")

    # --- Métricas por estado y para la suma de 51 jurisdicciones ---------------
    metric_rows = []
    for split_name in ("backtest", "preliminary_check"):
        sub = monthly[(monthly["split"] == split_name) & monthly["actual_mwh"].notna()]
        window = f"{sub['period'].min()}..{sub['period'].max()}"
        for model in MODELS:
            m = sub[sub["model_id"] == model]
            for st, g in m.groupby("state_code"):
                metric_rows.append(("state", st, model, split_name, window,
                                    compute_metrics(g["actual_mwh"].values, g["forecast_mwh"].values)))
            tot = m.groupby("period")[["actual_mwh", "forecast_mwh"]].sum()
            metric_rows.append(("all_51", "ALL", model, split_name, window,
                                compute_metrics(tot["actual_mwh"].values, tot["forecast_mwh"].values)))
    metrics = pd.DataFrame(
        [dict(scope=sc, state_code=st, model_id=mo, split=sp, eval_window=w, **mt)
         for sc, st, mo, sp, w, mt in metric_rows]
    )
    metrics["in_headline_metrics"] = metrics["split"] == "backtest"
    metrics.to_csv(out / "gold_forecast_metrics.csv", index=False, lineterminator="\n", float_format="%.4f")

    # --- Anual (solo años completos del backtest + forward completo 2027) -------
    monthly["year"] = monthly["period"].str[:4].astype(int)
    ann = []
    for (st, model, split, yr), g in monthly.groupby(["state_code", "model_id", "split", "year"]):
        if len(g) != 12:
            continue  # no se reporta un "año" parcial
        act = g["actual_mwh"].sum() if g["actual_mwh"].notna().all() else np.nan
        ann.append((st, yr, model, split, act, g["forecast_mwh"].sum()))
    annual = pd.DataFrame(ann, columns=["state_code", "year", "model_id", "split", "actual_mwh", "forecast_mwh"])
    annual["pct_error"] = 100.0 * (annual["forecast_mwh"] - annual["actual_mwh"]) / annual["actual_mwh"]
    annual.to_csv(out / "gold_forecast_annual.csv", index=False, lineterminator="\n", float_format="%.4f")

    # --- Resumen en consola ------------------------------------------------------
    print(f"Estados/DC procesados: {len(states)}")
    head = metrics[(metrics["split"] == "backtest") & (metrics["scope"] == "all_51")]
    print("\nBacktest 2024-2025, suma de 51 jurisdicciones:")
    print(head[["model_id", "mae_mwh", "rmse_mwh", "smape_pct"]].round(2).to_string(index=False))
    by_state = metrics[(metrics["split"] == "backtest") & (metrics["scope"] == "state")]
    print("\nsMAPE medio por estado (backtest):")
    print(by_state.groupby("model_id")["smape_pct"].agg(["mean", "median", "max"]).round(2).to_string())
    best = by_state.loc[by_state.groupby("state_code")["smape_pct"].idxmin(), "model_id"].value_counts()
    print("\nModelo con menor sMAPE por estado:", best.to_dict())
    print("Salidas escritas en", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                    help="Raíz del repositorio (por defecto, la del script).")
    run(ap.parse_args().root)
