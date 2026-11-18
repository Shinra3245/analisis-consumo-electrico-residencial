#!/usr/bin/env python3
"""Exporta agregados descriptivos del Parquet piloto para el dashboard.

No aplica ponderación poblacional ni produce estimaciones representativas.
Requiere pyarrow: python -m pip install pyarrow
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pyarrow.parquet as pq

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="datos/resstock_perfiles_piloto.parquet")
    parser.add_argument("--output",default="analitica/salidas/tablero/resstock.json")
    args=parser.parse_args()
    table=pq.read_table(args.input,columns=["bldg_id","timestamp_fin_local","electricidad_kwh"])
    rows=table.to_pylist()
    profiles={}
    monthly={}
    for r in rows:
        bid=str(r["bldg_id"])
        ts=r["timestamp_fin_local"]
        kwh=float(r["electricidad_kwh"])
        profiles.setdefault(bid,{"bldg_id":bid,"total_kwh":0.0,"intervals":0})
        profiles[bid]["total_kwh"]+=kwh
        profiles[bid]["intervals"]+=1
        # Timestamp marks interval end; subtract 15 minutes before month attribution.
        month=(ts.replace(tzinfo=None)-__import__("datetime").timedelta(minutes=15)).strftime("%Y-%m")
        monthly.setdefault(bid,{})
        monthly[bid][month]=monthly[bid].get(month,0.0)+kwh
    output={"source":"resstock_perfiles_piloto.parquet","unit":"kWh","weighted":False,
            "profiles":list(profiles.values()),
            "monthly":[{"bldg_id":bid,"period":period,"kwh":value}
                      for bid,months in monthly.items() for period,value in sorted(months.items())]}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Exportado: {path} · {len(profiles)} perfiles · {len(output['monthly'])} agregados mensuales")
if __name__=="__main__":main()
