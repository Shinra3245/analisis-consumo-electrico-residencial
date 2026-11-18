import { DATA_BASE, SCHEMA_VERSION, TABLES } from './config.js';

// Estados de una tabla: pending (no listada/no existe) · ok · error
export const store = {
  manifest: null,
  manifestStatus: 'loading', // loading | ok | missing | error
  manifestMessage: '',
  tables: {}, // nombre -> {status, rows, message, entry, validated}
};

const stripName = (s) => String(s).split('/').pop().replace(/\.json$/, '').replace(/\.[0-9a-f]{64}$/, '');

function manifestEntries(m) {
  const raw = m.tables || m.artifacts || m.outputs || m.files || [];
  const list = Array.isArray(raw)
    ? raw
    : Object.entries(raw).map(([k, v]) => ({ table: k, ...(typeof v === 'object' ? v : { file: v }) }));
  const map = {};
  for (const e of list) {
    const file = e.file || e.path || e.url;
    const name = stripName(e.table || e.name || file || '');
    if (name) map[name] = { ...e, file: file || `${name}.json` };
  }
  return map;
}

async function sha256Hex(buf) {
  if (!globalThis.crypto?.subtle) return null;
  const d = await crypto.subtle.digest('SHA-256', buf);
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function loadTable(name, spec, entry, manifestOk) {
  if (manifestOk && !entry) return { status: 'pending', message: 'No listada en el manifiesto: todavía no entregada por el bloque de datos.' };
  const url = DATA_BASE + (entry ? entry.file : `${name}.json`);
  let res;
  try {
    res = await fetch(url, { cache: 'no-cache' });
  } catch (e) {
    return { status: 'error', message: `No se pudo cargar ${url}: ${e.message}` };
  }
  if (res.status === 404) {
    return entry
      ? { status: 'error', message: `El manifiesto lista ${entry.file} pero no se encontró (${url}).` }
      : { status: 'pending', message: 'Todavía no entregada por el bloque de datos.' };
  }
  if (!res.ok) return { status: 'error', message: `No se pudo cargar ${url} (HTTP ${res.status}).` };
  const buf = await res.arrayBuffer();
  const notes = [];
  let validated = 'sin validar';
  if (entry?.sha256) {
    const hex = await sha256Hex(buf);
    if (hex === null) notes.push('SHA-256 no verificable (contexto no seguro; usar localhost/HTTPS)');
    else if (hex !== entry.sha256) {
      return { status: 'error', message: `SHA-256 de ${entry.file} no coincide con el manifiesto; la tabla no se usa.`, entry };
    } else validated = 'SHA-256 verificado';
  } else if (manifestOk) notes.push('el manifiesto no declara SHA-256 para esta tabla');
  if (entry?.bytes != null && entry.bytes !== buf.byteLength) {
    return { status: 'error', message: `Tamaño de ${entry.file} (${buf.byteLength} B) distinto del manifiesto (${entry.bytes} B).`, entry };
  }
  let json;
  try {
    json = JSON.parse(new TextDecoder().decode(buf));
  } catch (e) {
    return { status: 'error', message: `JSON inválido en ${url}: ${e.message}`, entry };
  }
  const rows = Array.isArray(json) ? json : json.rows || json.data;
  if (!Array.isArray(rows)) {
    return { status: 'error', message: `${url} debe ser un arreglo de filas (o {rows:[…]}).`, entry };
  }
  const declared = entry?.rows ?? entry?.row_count;
  if (declared != null && declared !== rows.length) {
    return { status: 'error', message: `${name}: ${rows.length} filas leídas, el manifiesto declara ${declared}.`, entry };
  }
  if (rows.length) {
    const missing = spec.columns.filter((c) => !(c in rows[0]));
    if (missing.length) {
      return { status: 'error', message: `${name}: faltan columnas del contrato (${missing.join(', ')}). Se esperaba esquema ${SCHEMA_VERSION}.`, entry };
    }
  }
  return { status: 'ok', rows, entry, validated, notes, bytes: buf.byteLength };
}

export async function loadAll() {
  try {
    const res = await fetch(DATA_BASE + 'manifest.json', { cache: 'no-cache' });
    if (res.status === 404) {
      store.manifestStatus = 'missing';
      store.manifestMessage = 'manifest.json todavía no está disponible: las tablas se leen sin validar hashes ni conteos.';
    } else if (!res.ok) {
      store.manifestStatus = 'error';
      store.manifestMessage = `No se pudo cargar manifest.json (HTTP ${res.status}).`;
    } else {
      store.manifest = await res.json();
      const v = String(store.manifest.schema_version ?? store.manifest.manifest_version ?? '');
      if (v !== SCHEMA_VERSION) {
        store.manifestStatus = 'error';
        store.manifestMessage = `Versión de esquema ${v || 'ausente'}; se esperaba ${SCHEMA_VERSION}. No se cargan tablas.`;
        store.manifest = null;
      } else store.manifestStatus = 'ok';
    }
  } catch (e) {
    store.manifestStatus = 'error';
    store.manifestMessage = `No se pudo leer manifest.json: ${e.message}`;
  }
  if (store.manifestStatus === 'error') {
    for (const n of Object.keys(TABLES)) store.tables[n] = { status: 'error', message: store.manifestMessage };
    return;
  }
  const entries = store.manifest ? manifestEntries(store.manifest) : {};
  store.entries = entries;
  await Promise.all(Object.entries(TABLES).map(async ([n, spec]) => {
    store.tables[n] = await loadTable(n, spec, entries[n], store.manifestStatus === 'ok');
  }));
}

export const rowsOf = (n) => (store.tables[n]?.status === 'ok' ? store.tables[n].rows : null);
export const statusOf = (n) => store.tables[n]?.status || 'pending';
