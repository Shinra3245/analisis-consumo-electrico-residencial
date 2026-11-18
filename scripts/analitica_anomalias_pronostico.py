#!/usr/bin/env python3
"""Anomalias interpretables y pronostico con holdout temporal sobre EIA mensual.

Lee datos/ existentes (solo lectura) y escribe artefactos bajo --salida
(por defecto /tmp/analitica_anomalias_pronostico). No accede a AWS.
Las anomalias reales NO se afirman: se reportan "candidatos estadisticos".
La evaluacion de deteccion usa solo inyecciones sinteticas etiquetadas.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ESTACION = {12: "DEF", 1: "DEF", 2: "DEF", 3: "MAM", 4: "MAM", 5: "MAM",
            6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
K_MAD = 1.4826


def cargar_eia(ruta):
    d = pd.read_csv(ruta)
    req = {"periodo", "estado", "estado_dato", "ventas_mwh"}
    if not req <= set(d.columns):
        raise SystemExit(f"Esquema inesperado en {ruta}: faltan {req - set(d.columns)}")
    if d.duplicated(["periodo", "estado"]).any() or d.ventas_mwh.isna().any():
        raise SystemExit("EIA con duplicados o nulos")
    d["fecha"] = pd.PeriodIndex(d.periodo, freq="M")
    return d.sort_values(["estado", "fecha"])


def serie_final(d):
    """Solo meses Final: los preliminares no entran a ajuste ni evaluacion."""
    f = d[d.estado_dato == "Final"]
    return f.pivot(index="fecha", columns="estado", values="ventas_mwh")


def yoy_log(p):
    return np.log(p).diff(12).dropna(how="all")


def ajustar_limites(yoy_ent, k):
    """Mediana y MAD robustos del cambio log interanual por estado x estacion."""
    filas = []
    for est in yoy_ent.columns:
        s = yoy_ent[est].dropna()
        est_season = s.index.month.map(ESTACION)
        for sea, g in s.groupby(est_season):
            med = g.median()
            mad = max(K_MAD * (g - med).abs().median(), 0.01)  # piso: 1% log
            filas.append((est, sea, len(g), med, mad, med - k * mad, med + k * mad))
    return pd.DataFrame(filas, columns=["estado", "estacion", "n", "mediana", "mad_esc", "lim_inf", "lim_sup"])


def puntuar(yoy, lim):
    s = yoy.stack().rename("yoy").reset_index()
    s.columns = ["fecha", "estado", "yoy"]
    s["estacion"] = s.fecha.dt.month.map(ESTACION)
    s = s.merge(lim, on=["estado", "estacion"])
    s["z_robusto"] = (s.yoy - s.mediana) / s.mad_esc
    s["candidato"] = (s.yoy < s.lim_inf) | (s.yoy > s.lim_sup)
    return s


def metricas(y, f):
    y, f = np.asarray(y, float), np.asarray(f, float)
    e = y - f
    return {"MAE": float(np.abs(e).mean()), "RMSE": float(np.sqrt((e ** 2).mean())),
            "sMAPE": float(100 * np.mean(2 * np.abs(e) / (np.abs(y) + np.abs(f))))}


def pronosticar(p, n_test, min_train):
    """Holdout temporal: ultimos n_test meses. Ajuste solo con entrenamiento."""
    ent, prue = p.iloc[:-n_test], p.iloc[-n_test:]
    res = {}
    if len(ent) < min_train:
        return None, ent, prue
    h = np.arange(1, n_test + 1)
    t_ent = np.arange(len(ent))
    for est in p.columns:
        y = np.log(ent[est].values)
        # baseline ingenua estacional: repite el ultimo ciclo anual de entrenamiento
        ult = ent[est].values[-12:]
        naive = np.array([ult[(i) % 12] for i in range(n_test)])
        # modelo: log-lineal con tendencia + dummies de mes (sin fuga: solo entrenamiento)
        def X(t, meses):
            D = np.eye(12)[np.asarray(meses) - 1]
            return np.column_stack([D, np.asarray(t, float)])
        beta, *_ = np.linalg.lstsq(X(t_ent, ent.index.month), y, rcond=None)
        resid = y - X(t_ent, ent.index.month) @ beta
        smear = np.mean(np.exp(resid))  # correccion de retransformacion
        mod = np.exp(X(len(ent) + h - 1, prue.index.month) @ beta) * smear
        res[est] = (prue[est].values, naive, mod)
    return res, ent, prue


def serie_forecast(p, n_test, min_train):
    """Backtest (no proyeccion futura): real vs naive vs modelo en el holdout."""
    res, ent, prue = pronosticar(p, n_test, min_train)
    if res is None:
        return None
    filas = []
    for est, (y, nv, md) in res.items():
        for i, per in enumerate(prue.index):
            filas.append({"estado": est, "period": str(per), "real_mwh": y[i],
                          "naive_mwh": nv[i], "modelo_mwh": md[i], "particion": "holdout"})
    return pd.DataFrame(filas)


def evaluar_forecast(p, n_test, min_train):
    res, ent, prue = pronosticar(p, n_test, min_train)
    if res is None:
        return None, {"suficiente": False, "motivo": f"entrenamiento {len(ent)} < {min_train} meses"}
    filas = []
    for est, (y, nv, md) in res.items():
        a, b = metricas(y, nv), metricas(y, md)
        filas.append({"estado": est, **{f"naive_{k}": v for k, v in a.items()},
                      **{f"modelo_{k}": v for k, v in b.items()}})
    t = pd.DataFrame(filas)
    t["mejora_rmse_pct"] = 100 * (1 - t.modelo_RMSE / t.naive_RMSE)
    t["mejora_smape_pct"] = 100 * (1 - t.modelo_sMAPE / t.naive_sMAPE)
    gana = int((t.modelo_sMAPE < t.naive_sMAPE).sum())
    resumen = {
        "suficiente": True, "meses_entrenamiento": len(ent), "meses_prueba": len(prue),
        "periodo_entrenamiento": [str(ent.index[0]), str(ent.index[-1])],
        "periodo_prueba": [str(prue.index[0]), str(prue.index[-1])],
        "n_estados": len(t),
        "sMAPE_mediana_naive": float(t.naive_sMAPE.median()),
        "sMAPE_mediana_modelo": float(t.modelo_sMAPE.median()),
        "RMSE_mediana_naive_mwh": float(t.naive_RMSE.median()),
        "RMSE_mediana_modelo_mwh": float(t.modelo_RMSE.median()),
        "estados_donde_modelo_supera_naive_sMAPE": gana,
    }
    return t, resumen


def prueba_sintetica(p, lim, n_ent, k, semilla, magnitudes=(0.10, 0.20, 0.30, 0.50)):
    """Inyecta picos/caidas multiplicativos en el periodo de prueba. SINTETICO."""
    rng = np.random.default_rng(semilla)
    prueba = p.iloc[n_ent:]
    base = yoy_log(p)
    filas = []
    for mag in magnitudes:
        y = p.copy()
        marca = pd.DataFrame(False, index=y.index, columns=y.columns)
        for est in y.columns:
            # todo el holdout; los 12 meses previos (entrenamiento) quedan como referencia del YoY
            idx = rng.choice(np.arange(max(n_ent, 12), len(y)), size=3, replace=False)
            for i in idx:
                signo = rng.choice([-1, 1])
                y.iloc[i, y.columns.get_loc(est)] *= (1 + signo * mag)
                marca.iloc[i, marca.columns.get_loc(est)] = True
        sc = puntuar(yoy_log(y), lim)
        sc = sc[sc.fecha >= prueba.index[0]]
        etiq = marca.stack().rename("inyectado").reset_index()
        etiq.columns = ["fecha", "estado", "inyectado"]
        sc = sc.merge(etiq, on=["fecha", "estado"])
        # una inyeccion en t tambien altera yoy en t+12; se etiqueta como inyectado el mes t
        # y se excluyen los meses t+12 (efecto de arrastre) del conteo de falsos positivos
        arrastre = marca.shift(12, fill_value=False).stack().rename("arr").reset_index()
        arrastre.columns = ["fecha", "estado", "arr"]
        sc = sc.merge(arrastre, on=["fecha", "estado"])
        sc = sc[~(sc.arr & ~sc.inyectado)]
        tp = int((sc.candidato & sc.inyectado).sum()); fn = int((~sc.candidato & sc.inyectado).sum())
        fp = int((sc.candidato & ~sc.inyectado).sum()); tn = int((~sc.candidato & ~sc.inyectado).sum())
        filas.append({"magnitud_inyectada": mag, "k_mad": k, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
                      "recall": tp / max(tp + fn, 1), "precision": tp / max(tp + fp, 1),
                      "tasa_falsos_positivos": fp / max(fp + tn, 1), "ETIQUETA": "SINTETICO"})
    return pd.DataFrame(filas)


def descripcion_resstock(ruta):
    if not ruta.exists():
        return {"disponible": False}
    r = pd.read_csv(ruta, usecols=["timestamp", "out.electricity.total.energy_consumption..kwh"])
    r["timestamp"] = pd.to_datetime(r.timestamp)
    c = r["out.electricity.total.energy_consumption..kwh"]
    m = c.groupby(r.timestamp.dt.to_period("M")).sum() / 1000
    return {"disponible": True, "filas": len(r), "inicio": str(r.timestamp.min()), "fin": str(r.timestamp.max()),
            "intervalo": "15 min", "total_mwh": float(m.sum()), "mes_pico": str(m.idxmax()),
            "mwh_mes_pico": float(m.max()), "nota": "Solo descriptivo: un anio, un estrato (CO unifamiliar aislada); no se usa para anomalias ni forecast."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eia", default=str(RAIZ / "datos/eia_residencial_mensual.csv"))
    ap.add_argument("--resstock", default=str(RAIZ / "data/raw/up00-co-single-family_detached.csv"))
    ap.add_argument("--salida", default="/tmp/analitica_anomalias_pronostico")
    ap.add_argument("--meses-prueba", type=int, default=24)
    ap.add_argument("--meses-min-entrenamiento", type=int, default=48)
    ap.add_argument("--k-mad", type=float, default=3.5)
    ap.add_argument("--semilla", type=int, default=42)
    a = ap.parse_args(argv)
    sal = Path(a.salida).resolve()
    for ent in (RAIZ / "datos", RAIZ / "data", RAIZ / "docs"):
        if sal == ent or ent in sal.parents:
            raise SystemExit("La salida no puede estar dentro de datos/, data/ ni docs/")
    sal.mkdir(parents=True, exist_ok=True)

    d = cargar_eia(a.eia)
    p = serie_final(d)
    prelim = d[d.estado_dato != "Final"]
    n_ent = len(p) - a.meses_prueba
    # Anomalias: limites ajustados SOLO con el entrenamiento; se puntua entrenamiento y prueba
    lim = ajustar_limites(yoy_log(p.iloc[:n_ent]), a.k_mad)
    sc = puntuar(yoy_log(p), lim)
    sc["particion"] = np.where(sc.fecha >= p.index[n_ent], "prueba", "entrenamiento")
    cand = sc[sc.candidato].sort_values("z_robusto", key=abs, ascending=False)
    # preliminares: puntuados aparte, solo informativo
    pp = d.pivot(index="fecha", columns="estado", values="ventas_mwh")
    scp = puntuar(yoy_log(pp), lim)
    scp = scp[scp.fecha.isin(prelim.fecha.unique())]
    fc, res_fc = evaluar_forecast(p, a.meses_prueba, a.meses_min_entrenamiento)
    sint = prueba_sintetica(p, lim, n_ent, a.k_mad, a.semilla)

    sc.to_csv(sal / "puntuaciones_yoy.csv", index=False)
    cand.to_csv(sal / "candidatos_estadisticos.csv", index=False)
    lim.to_csv(sal / "limites_robustos.csv", index=False)
    sint.to_csv(sal / "evaluacion_sintetica.csv", index=False)
    serie = serie_forecast(p, a.meses_prueba, a.meses_min_entrenamiento)
    if serie is not None:
        serie.round(4).to_csv(sal / "forecast_serie.csv", index=False)
        res_fc["forecast_serie"] = {"archivo": "forecast_serie.csv", "filas": len(serie),
                                    "estados": int(serie.estado.nunique()),
                                    "periodos": int(serie.period.nunique()),
                                    "tipo": "backtest sobre holdout; no es proyeccion futura"}
    if fc is not None:
        fc.to_csv(sal / "forecast_metricas_por_estado.csv", index=False)
    resumen = {
        "entrada_eia": a.eia, "filas_eia": len(d), "estados": int(p.shape[1]),
        "meses_final": int(p.shape[0]), "rango_final": [str(p.index[0]), str(p.index[-1])],
        "meses_preliminares_excluidos": sorted(prelim.fecha.astype(str).unique().tolist()),
        "parametros": {"k_mad": a.k_mad, "meses_prueba": a.meses_prueba, "semilla": a.semilla},
        "anomalias_reales": {"scores_totales": int(len(sc)),
                             "candidatos_entrenamiento": int(cand.particion.eq("entrenamiento").sum()),
                             "candidatos_prueba": int(cand.particion.eq("prueba").sum()),
                             "candidatos_preliminares_2026": int(scp.candidato.sum()),
                             "scores_preliminares_2026": int(len(scp)),
                             "advertencia": "Candidatos estadisticos para revision; no se afirman anomalias reales."},
        "evaluacion_sintetica": sint.to_dict("records"),
        "forecast": res_fc,
        "resstock_descripcion": descripcion_resstock(Path(a.resstock)),
    }
    (sal / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"\nArtefactos en {sal}", file=sys.stderr)


if __name__ == "__main__":
    main()
