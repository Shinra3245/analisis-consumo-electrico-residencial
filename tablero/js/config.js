// Ruta base de las exportaciones JSON de Gold. Cambiar aquí (o con ?data=<url/>)
// no requiere tocar el esquema: el tablero solo lee <base>/manifest.json y las tablas que liste.
export const SCHEMA_VERSION = '1.0';

const param = new URLSearchParams(location.search).get('data');
export const DATA_BASE = (param || 'data/v1/').replace(/\/?$/, '/');

// Tablas que el tablero sabe leer. `columns` son obligatorias: si faltan, la tabla se rechaza
// (no hay alias silenciosos entre nombres distintos, ver docs/especificacion-tablero.md §9).
export const TABLES = {
  gold_eia_monthly: {
    columns: ['period', 'state_code', 'data_status', 'sales_mwh'],
    source: 'eia',
  },
  gold_resstock_monthly: {
    columns: ['bldg_id', 'source_period', 'kwh_month', 'state_code', 'housing_type'],
    source: 'resstock',
  },
  gold_resstock_pattern: {
    columns: ['bldg_id', 'period_local', 'day_type', 'hour_local', 'utc_offset_minutes',
      'is_partial_period', 'median_kwh', 'state_code', 'housing_type', 'time_zone'],
    source: 'resstock',
    lazy: true,
  },
  gold_resstock_pattern_aggregate: {
    columns: ['state_code', 'housing_type', 'time_zone', 'period_local', 'day_type', 'hour_local', 'utc_offset_minutes',
      'is_partial_period', 'median_kwh', 'mean_kwh', 'p10_kwh', 'p90_kwh', 'min_kwh', 'max_kwh',
      'n_obs', 'n_profiles'],
    source: 'resstock',
    lazy: true,
  },
  gold_resstock_profile_summary: {
    columns: ['bldg_id', 'source_year', 'annual_kwh', 'mean_hour_kwh', 'peak_hour_kwh',
      'n_hours', 'state_code', 'housing_type'],
    source: 'resstock',
  },
  gold_climate: {
    columns: ['point_id', 'state_code', 'timestamp_utc', 'temperature_c', 'model'],
    source: 'climate',
  },
  gold_anomaly_candidates: {
    columns: ['period', 'state_code', 'yoy_change_pct', 'season', 'robust_z', 'partition', 'classification'],
    source: 'eia',
  },
  gold_anomaly_synthetic_eval: {
    columns: ['injection_pct', 'k_mad', 'tp', 'fn', 'fp', 'tn', 'recall', 'precision', 'false_positive_rate', 'evaluation_scope'],
    source: 'eia',
  },
  gold_forecast_metrics: {
    columns: ['state_code', 'naive_mae_mwh', 'naive_rmse_mwh', 'naive_smape_pct', 'model_mae_mwh', 'model_rmse_mwh', 'model_smape_pct', 'model_smape_improvement_pct'],
    source: 'eia',
  },
  gold_forecast_series: {
    columns: ['state_code', 'period', 'actual_mwh', 'naive_mwh', 'model_mwh', 'partition'],
    source: 'eia',
  },
};
