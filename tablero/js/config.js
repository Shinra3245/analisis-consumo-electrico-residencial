export const CONFIG = {
  dataBase: "../analitica/salidas/",
  manifestCandidates: ["../analitica/salidas/manifest.json", "../analitica/salidas/gold/manifest.json", "../analitica/salidas/tablero/manifest.json", "../data/manifest.json", "../datos/manifest.json"],
  candidates: {
    eia: ["../analitica/salidas/gold/gold_eia_monthly.json", "../analitica/salidas/gold/gold_eia_monthly.csv", "../analitica/salidas/gold/eia_mensual.json", "../analitica/salidas/gold/eia_mensual.csv", "../analitica/salidas/eia_mensual.csv", "../datos/eia_residencial_mensual.csv", "../data/eia_residencial_mensual.csv", "../datos/eia_residencial.csv"],
    coverage: ["../analitica/salidas/gold/cobertura_eia.json", "../analitica/salidas/gold/cobertura_eia.csv", "../analitica/salidas/cobertura_eia.csv", "../datos/cobertura_eia.csv", "../data/cobertura_eia.csv"],
    climate: ["../analitica/salidas/gold/clima_open_meteo_muestra.json", "../analitica/salidas/gold/clima_open_meteo_muestra.csv", "../analitica/salidas/clima_open_meteo_muestra.csv", "../datos/clima_open_meteo_muestra.csv", "../data/clima_open_meteo_muestra.csv", "../datos/clima.csv"],
    comparison: ["../analitica/salidas/gold/comparacion_mensual.json", "../analitica/salidas/tablero/comparacion_mensual.json", "../analitica/salidas/comparacion_mensual.json", "../analitica/salidas/gold/demo_colorado_2018_verificacion.csv", "../datos/demo_colorado_2018_verificacion.csv", "../data/demo_colorado_2018_verificacion.csv"],
    resstock: ["../analitica/salidas/gold/gold_resstock_profile_summary.json", "../analitica/salidas/gold/resstock_profile_summary.json", "../analitica/salidas/tablero/resstock.json", "../analitica/salidas/resstock.json"],
    forecast: ["../analitica/salidas/gold/gold_forecast_monthly.json", "../analitica/salidas/gold/estimaciones.json", "../analitica/salidas/tablero/estimaciones.json", "../analitica/salidas/estimaciones.json"],
    forecastMetrics: ["../analitica/salidas/gold/gold_forecast_metrics.json", "../analitica/salidas/gold/forecast_metrics.json"],
    forecastAnnual: ["../analitica/salidas/gold/gold_forecast_annual.json", "../analitica/salidas/gold/forecast_annual.json"],
    anomalies: ["../analitica/salidas/gold/gold_anomaly_cases.json", "../analitica/salidas/gold/anomalias.json", "../analitica/salidas/tablero/anomalias.json", "../analitica/salidas/anomalias.json"],
    anomalyMetrics: ["../analitica/salidas/gold/gold_anomaly_metrics.json", "../analitica/salidas/gold/anomaly_metrics.json"],
    anomalySensitivity: ["../analitica/salidas/gold/gold_anomaly_sensitivity.json", "../analitica/salidas/gold/anomaly_sensitivity.json"],
    anomalySeries: ["../analitica/salidas/gold/gold_anomaly_case_series.json", "../analitica/salidas/gold/anomaly_case_series.json"],
    patterns: ["../analitica/salidas/gold/gold_resstock_pattern.json", "../analitica/salidas/gold/patrones_horarios.json", "../analitica/salidas/tablero/patrones_horarios.json", "../analitica/salidas/patrones_horarios.json"],
    resstockMonthly: ["../analitica/salidas/gold/gold_resstock_monthly.json"],
    resstockSummary: ["../analitica/salidas/gold/gold_resstock_profile_summary.json"]
  },
  aliases: {
    eia: {period:["period","periodo","year_month","fecha","anio_mes"],year:["year","anio","año"],month:["month","mes"],state:["state_code","estado","state"],status:["data_status","estado_dato","status"],sales:["sales_mwh","ventas_mwh","eia_mwh","consumo_mwh"],sector:["sector","sector_name"]},
    comparison: {period:["period","periodo","year_month","fecha","anio_mes","source_period"],year:["year","anio","año"],month:["month","mes"],state:["state_code","estado","state"],resstock:["resstock_mwh","resstock_co_unifamiliar_aislada_mwh","consumo_resstock_mwh"],eia:["eia_mwh","eia_co_res_ventas_mwh","ventas_eia_mwh"],difference:["difference_mwh","diferencia_mwh"],ratio:["ratio_pct","relacion_porcentaje","razon_descriptiva_pct"]},
    climate:{point:["point_id","punto_id","location","location_name","point_name"],timestamp:["timestamp_utc","time","timestamp","fecha_hora"],temperature:["temperature_c","temperature_2m","temperature","temperatura_c","temp_c"],model:["model","modelo"]},
    resstock:{buildingId:["bldg_id","building_id","profile_id","id_perfil"],state:["state_code","estado","state"],housingType:["housing_type","tipo_vivienda"],period:["period","periodo","year_month","source_period"],kwh:["electricity_kwh","consumption_kwh","consumo_kwh","kwh","annual_kwh","median_kwh"]},
    forecast:{period:["period","periodo","year_month"],year:["year","anio"],month:["month","mes"],state:["state_code","estado","state"],model:["model_id","modelo","model"],split:["split","set","dataset"],forecast:["forecast_mwh","estimacion_mwh","predicted_mwh"],actual:["actual_mwh","real_mwh","sales_mwh"],status:["actual_status","data_status","status"]},
    anomalies:{period:["period","timestamp_start_local","timestamp_start_est","timestamp","start_est","start"],year:["year"],state:["state_code","estado","state"],buildingId:["bldg_id","profile_id"],observed:["observed_kwh","observed_value","observado"],baseline:["baseline_kwh","expected_value","baseline","referencia"],score:["score","trigger_value"],method:["method","rule","metodo"],category:["category","categoria"],synthetic:["is_synthetic","is_synthetic_labels"]},
    patterns:{period:["period_local","period","month","mes"],hour:["hour_local","hour","hora"],state:["state_code","estado"],housingType:["housing_type","tipo_vivienda"],buildingId:["bldg_id","profile_id"],dayType:["day_type","tipo_dia"],value:["median_kwh","mean_kwh","kwh","value"]}
  }
};
