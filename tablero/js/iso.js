// Ilustración isométrica CONCEPTUAL de un tipo de vivienda.
// Exterior ilustrativo: no es un plano ni un modelo de habitaciones; no contiene cuartos,
// termostatos, interruptores ni luces interiores.
// Coordenadas: x hacia abajo-derecha (+X), y hacia abajo-izquierda (+Y), z hacia arriba (+Z).

const S = 38, OX = 190, OY = 120, C = Math.cos(Math.PI / 6), SN = 0.5;
const P = (x, y, z) => [OX + (x - y) * C * S, OY + (x + y) * SN * S - z * S];
const ptStr = (pts) => pts.map((p) => P(...p).map((n) => n.toFixed(1)).join(',')).join(' ');
const poly = (pts, cls) => `<polygon class="${cls}" points="${ptStr(pts)}"/>`;
const line = (p1, p2, cls) => {
  const [x1, y1] = P(...p1), [x2, y2] = P(...p2);
  return `<line class="${cls}" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>`;
};

// Prisma rectangular ortogonal
function box(x, y, z, w, d, h, clsL = 'f-left', clsR = 'f-right', clsT = 'f-top') {
  return poly([[x, y + d, z], [x + w, y + d, z], [x + w, y + d, z + h], [x, y + d, z + h]], clsL)
    + poly([[x + w, y, z], [x + w, y + d, z], [x + w, y + d, z + h], [x + w, y, z + h]], clsR)
    + poly([[x, y, z + h], [x + w, y, z + h], [x + w, y + d, z + h], [x, y + d, z + h]], clsT);
}

// Zócalo de cimentación ligeramente saliente
function plinth(x, y, z, w, d, h) {
  const m = 0.04;
  return box(x - m, y - m, z, w + 2 * m, d + 2 * m, h, 'plinth-l', 'plinth-r', 'plinth-t');
}

// Techo a dos aguas con cumbrera paralela al eje X y aleros salientes
function gableRoof(x, y, z, w, d, r, overX = 0.12, overY = 0.14) {
  const x0 = x - overX, x1 = x + w + overX;
  const y0 = y - overY, y1 = y + d + overY;
  const ym = y + d / 2;
  // Faldón frontal (f-left / roof-a)
  const fFront = poly([[x0, y1, z], [x1, y1, z], [x1, ym, z + r], [x0, ym, z + r]], 'roof-a');
  // Testero o tímpano derecho (gablete en x1)
  const gRight = poly([[x1, y0, z], [x1, y1, z], [x1, ym, z + r]], 'roof-g');
  // Faldón posterior (f-right / roof-b)
  const fBack = poly([[x0, y0, z], [x1, y0, z], [x1, ym, z + r], [x0, ym, z + r]], 'roof-b');
  // Cumbrera
  const ridge = line([x0, ym, z + r], [x1, ym, z + r], 'iso-ridge');
  // Borde de alero
  const eave = line([x0, y1, z], [x1, y1, z], 'iso-eave');
  return fFront + gRight + fBack + ridge + eave;
}

// Chimenea en el tejado con remate
function chimney(x, y, z, w = 0.22, d = 0.22, h = 0.55) {
  const cap = box(x - 0.03, y - 0.03, z + h, w + 0.06, d + 0.06, 0.06, 'chim-cap-l', 'chim-cap-r', 'chim-cap-t');
  return box(x, y, z, w, d, h, 'chim-l', 'chim-r', 'chim-t') + cap;
}

// Ventana detallada en fachada frontal (f-left, plano Y = y_front)
function winFront(x, y, z, w, h) {
  const eps = 0.01;
  const frame = poly([[x - 0.03, y + eps, z - 0.03], [x + w + 0.03, y + eps, z - 0.03], [x + w + 0.03, y + eps, z + h + 0.03], [x - 0.03, y + eps, z + h + 0.03]], 'win-frame');
  const glass = poly([[x, y + eps * 2, z], [x + w, y + eps * 2, z], [x + w, y + eps * 2, z + h], [x, y + eps * 2, z + h]], 'win-glass');
  // Repisa / vierteaguas
  const sill = poly([[x - 0.05, y + 0.08, z - 0.02], [x + w + 0.05, y + 0.08, z - 0.02], [x + w + 0.05, y, z - 0.02], [x - 0.05, y, z - 0.02]], 'win-sill');
  // Cruceta / parteluz
  const midX = x + w / 2, midZ = z + h / 2;
  const divV = line([midX, y + eps * 3, z], [midX, y + eps * 3, z + h], 'win-mullion');
  const divH = line([x, y + eps * 3, midZ], [x + w, y + eps * 3, midZ], 'win-mullion');
  return frame + glass + sill + divV + divH;
}

// Ventana detallada en fachada lateral derecha (f-right, plano X = x_right)
function winSide(x, y, z, d, h) {
  const eps = 0.01;
  const frame = poly([[x + eps, y - 0.03, z - 0.03], [x + eps, y + d + 0.03, z - 0.03], [x + eps, y + d + 0.03, z + h + 0.03], [x + eps, y - 0.03, z + h + 0.03]], 'win-frame');
  const glass = poly([[x + eps * 2, y, z], [x + eps * 2, y + d, z], [x + eps * 2, y + d, z + h], [x + eps * 2, y, z + h]], 'win-glass');
  const sill = poly([[x + 0.08, y - 0.05, z - 0.02], [x + 0.08, y + d + 0.05, z - 0.02], [x, y + d + 0.05, z - 0.02], [x, y - 0.05, z - 0.02]], 'win-sill');
  const midY = y + d / 2, midZ = z + h / 2;
  const divV = line([x + eps * 3, midY, z], [x + eps * 3, midY, z + h], 'win-mullion');
  const divH = line([x + eps * 3, y, midZ], [x + eps * 3, y + d, midZ], 'win-mullion');
  return frame + glass + sill + divV + divH;
}

// Puerta de entrada con marco, panel y manija en fachada frontal (f-left)
function doorFront(x, y, z, w = 0.38, h = 0.75) {
  const eps = 0.01;
  const frame = poly([[x - 0.03, y + eps, z], [x + w + 0.03, y + eps, z], [x + w + 0.03, y + eps, z + h + 0.03], [x - 0.03, y + eps, z + h + 0.03]], 'door-frame');
  const panel = poly([[x, y + eps * 2, z], [x + w, y + eps * 2, z], [x + w, y + eps * 2, z + h], [x, y + eps * 2, z + h]], 'door-panel');
  // Pequeño ventanuco superior de la puerta
  const glass = poly([[x + 0.06, y + eps * 3, z + h - 0.24], [x + w - 0.06, y + eps * 3, z + h - 0.24], [x + w - 0.06, y + eps * 3, z + h - 0.06], [x + 0.06, y + eps * 3, z + h - 0.06]], 'door-glass');
  // Manija
  const knob = poly([[x + w - 0.07, y + eps * 4, z + 0.34], [x + w - 0.04, y + eps * 4, z + 0.34], [x + w - 0.04, y + eps * 4, z + 0.37], [x + w - 0.07, y + eps * 4, z + 0.37]], 'door-knob');
  return frame + panel + glass + knob;
}

// Escalones de acceso (porch steps)
function stepsFront(x, y, zBase, w = 0.5, d = 0.22, h = 0.1) {
  return box(x, y, zBase - h, w, d, h, 'step-l', 'step-r', 'step-t')
    + box(x - 0.04, y + d, zBase - 2 * h, w + 0.08, d, h, 'step-l', 'step-r', 'step-t');
}

// Porche o marquesina voladiza
function porchCanopy(x, y, z, w, d, h = 0.06) {
  return box(x, y, z, w, d, h, 'canopy-l', 'canopy-r', 'canopy-t');
}

// Líneas de revestimiento / siding horizontal en fachada frontal
function sidingFront(x, y, z0, z1, w, step = 0.14) {
  let out = '';
  for (let z = z0 + step; z < z1; z += step) {
    out += line([x, y + 0.005, z], [x + w, y + 0.005, z], 'iso-siding');
  }
  return out;
}

// Elementos de entorno: árbol frondoso
function leafyTree(x, y, scale = 1) {
  const r = 0.12 * scale;
  const trunk = box(x, y, 0, r * 2, r * 2, 0.45 * scale, 'trunk-l', 'trunk-r', 'trunk-t');
  const b1 = box(x - 0.25 * scale, y - 0.25 * scale, 0.35 * scale, 0.7 * scale, 0.7 * scale, 0.4 * scale, 'leaf-l', 'leaf-r', 'leaf-t');
  const b2 = box(x - 0.18 * scale, y - 0.18 * scale, 0.65 * scale, 0.56 * scale, 0.56 * scale, 0.38 * scale, 'leaf-l', 'leaf-r', 'leaf-t');
  const b3 = box(x - 0.1 * scale, y - 0.1 * scale, 0.95 * scale, 0.4 * scale, 0.4 * scale, 0.3 * scale, 'leaf-l', 'leaf-r', 'leaf-t');
  return trunk + b1 + b2 + b3;
}

// Arbusto de jardín
function gardenBush(x, y, s = 0.25) {
  return box(x - s / 2, y - s / 2, 0, s, s, s * 0.85, 'bush-l', 'bush-r', 'bush-t');
}

// Sendero pavimentado desde la entrada hacia el frente
function gardenPath(x, y0, y1, w = 0.42) {
  return poly([[x, y0, 0.002], [x + w, y0, 0.002], [x + w, y1, 0.002], [x, y1, 0.002]], 'iso-path');
}

// Sombra arrojada sobre el suelo
function dropShadow(x, y, w, d) {
  return poly([[x + 0.15, y - 0.15, 0.001], [x + w + 0.35, y - 0.15, 0.001], [x + w + 0.35, y + d + 0.15, 0.001], [x + 0.15, y + d + 0.15, 0.001]], 'iso-shadow');
}

/* -------------------------------------------------------------
 * ARQUETIPOS DE VIVIENDA (5 tipos normalizados)
 * ------------------------------------------------------------- */
const SHAPES = {
  // 1. Mobile Home: alargada, zócalo perimetral, techo metálico bajo, puerta lateral con gradas
  'Mobile Home': () => {
    const x = -1.7, y = -0.7, zPlinth = 0.18, w = 3.3, d = 1.35, h = 0.85;
    return dropShadow(x, y, w, d)
      + plinth(x, y, 0, w, d, zPlinth)
      + box(x, y, zPlinth, w, d, h)
      + gableRoof(x, y, zPlinth + h, w, d, 0.26, 0.08, 0.1)
      + sidingFront(x, y + d, zPlinth, zPlinth + h, w, 0.12)
      // Puerta lateral y porche de acceso
      + doorFront(x + 0.45, y + d, zPlinth, 0.34, 0.72)
      + stepsFront(x + 0.4, y + d, zPlinth, 0.44, 0.24, 0.09)
      + porchCanopy(x + 0.35, y + d, zPlinth + 0.76, 0.54, 0.3, 0.04)
      // Secuencia de ventanas en fachada frontal
      + winFront(x + 1.2, y + d, zPlinth + 0.22, 0.45, 0.42)
      + winFront(x + 1.9, y + d, zPlinth + 0.22, 0.45, 0.42)
      + winFront(x + 2.55, y + d, zPlinth + 0.22, 0.45, 0.42)
      // Ventana en testero lateral
      + winSide(x + w, y + 0.35, zPlinth + 0.22, 0.45, 0.42)
      // Chimenea / tiro de ventilación de techo
      + chimney(x + 2.4, y + 0.3, zPlinth + h + 0.18, 0.14, 0.14, 0.3)
      // Unidad de servicio exterior (bomba de calor / gas)
      + box(x - 0.45, y + 0.4, 0, 0.32, 0.4, 0.38, 'util-l', 'util-r', 'util-t')
      + gardenPath(x + 0.42, y + d + 0.48, 2.3, 0.4)
      + gardenBush(-2.2, 1.2, 0.3)
      + gardenBush(1.9, -1.6, 0.28);
  },

  // 2. Single-Family Detached: vivienda unifamiliar completa con aleros, chimenea, porche y jardín
  'Single-Family Detached': () => {
    const x = -1.35, y = -1.0, zPlinth = 0.16, w = 2.4, d = 2.0, h = 1.25, r = 0.95;
    // Ala lateral secundaria
    const wx = 0.9, dx = 1.3, hx = 0.85;
    return dropShadow(x, y, w + wx, d)
      + plinth(x, y, 0, w, d, zPlinth)
      + box(x, y, zPlinth, w, d, h)
      + gableRoof(x, y, zPlinth + h, w, d, r, 0.16, 0.18)
      + sidingFront(x, y + d, zPlinth, zPlinth + h, w, 0.15)
      // Ala lateral adyacente (cochera / porche cubierto)
      + plinth(x + w, y + 0.3, 0, wx, dx, zPlinth)
      + box(x + w, y + 0.3, zPlinth, wx, dx, hx)
      + gableRoof(x + w, y + 0.3, zPlinth + hx, wx, dx, 0.45, 0.1, 0.12)
      // Chimenea de mampostería sobre faldón
      + chimney(x + 0.4, y + 0.35, zPlinth + h + 0.55, 0.26, 0.26, 0.7)
      // Porche y puerta principal
      + doorFront(x + 0.35, y + d, zPlinth, 0.42, 0.82)
      + stepsFront(x + 0.3, y + d, zPlinth, 0.52, 0.26, 0.08)
      + porchCanopy(x + 0.22, y + d, zPlinth + 0.88, 0.68, 0.35, 0.06)
      // Ventanas de fachada frontal
      + winFront(x + 1.2, y + d, zPlinth + 0.25, 0.55, 0.6)
      + winFront(x + 1.9, y + d, zPlinth + 0.25, 0.42, 0.6)
      // Ventanas en ala lateral
      + winSide(x + w + wx, y + 0.65, zPlinth + 0.2, 0.45, 0.45)
      // Sendero y entorno
      + gardenPath(x + 0.35, y + d + 0.52, 2.35, 0.44)
      + gardenBush(x + 1.1, y + d + 0.2, 0.28)
      + gardenBush(x + 1.85, y + d + 0.2, 0.28)
      + leafyTree(-2.4, 1.4, 1.1)
      + leafyTree(2.2, -1.8, 0.95);
  },

  // 3. Single-Family Attached (Townhouse): dos unidades adosadas con muro medianero y accesos dobles
  'Single-Family Attached': () => {
    const zPlinth = 0.16, h = 1.4, d = 1.9, r = 0.85;
    const w1 = 1.6, w2 = 1.6;
    const x1 = -1.65, x2 = x1 + w1;
    return dropShadow(x1, -0.95, w1 + w2, d)
      + plinth(x1, -0.95, 0, w1 + w2, d, zPlinth)
      // Unidad 1 (izquierda)
      + box(x1, -0.95, zPlinth, w1, d, h)
      + gableRoof(x1, -0.95, zPlinth + h, w1, d, r, 0.08, 0.14)
      + sidingFront(x1, -0.95 + d, zPlinth, zPlinth + h, w1, 0.16)
      + doorFront(x1 + 0.22, -0.95 + d, zPlinth, 0.38, 0.78)
      + stepsFront(x1 + 0.18, -0.95 + d, zPlinth, 0.46, 0.24, 0.08)
      + porchCanopy(x1 + 0.14, -0.95 + d, zPlinth + 0.84, 0.54, 0.28, 0.05)
      + winFront(x1 + 0.8, -0.95 + d, zPlinth + 0.22, 0.52, 0.55)
      + winFront(x1 + 0.25, -0.95 + d, zPlinth + 0.88, 0.42, 0.45)
      + winFront(x1 + 0.85, -0.95 + d, zPlinth + 0.88, 0.45, 0.45)
      // Muro medianero divisorio
      + line([x2, -0.95 + d + 0.01, zPlinth], [x2, -0.95 + d + 0.01, zPlinth + h + r], 'iso-seam')
      // Unidad 2 (derecha, simétrica)
      + box(x2, -0.95, zPlinth, w2, d, h)
      + gableRoof(x2, -0.95, zPlinth + h, w2, d, r, 0.08, 0.14)
      + sidingFront(x2, -0.95 + d, zPlinth, zPlinth + h, w2, 0.16)
      + doorFront(x2 + 0.22, -0.95 + d, zPlinth, 0.38, 0.78)
      + stepsFront(x2 + 0.18, -0.95 + d, zPlinth, 0.46, 0.24, 0.08)
      + porchCanopy(x2 + 0.14, -0.95 + d, zPlinth + 0.84, 0.54, 0.28, 0.05)
      + winFront(x2 + 0.8, -0.95 + d, zPlinth + 0.22, 0.52, 0.55)
      + winFront(x2 + 0.25, -0.95 + d, zPlinth + 0.88, 0.42, 0.45)
      + winFront(x2 + 0.85, -0.95 + d, zPlinth + 0.88, 0.45, 0.45)
      // Ventanas laterales
      + winSide(x2 + w2, -0.95 + 0.4, zPlinth + 0.25, 0.45, 0.5)
      + winSide(x2 + w2, -0.95 + 0.4, zPlinth + 0.88, 0.45, 0.45)
      // Sendero compartido y vegetación frontal
      + gardenPath(x1 + 0.25, -0.95 + d + 0.48, 2.3, 0.4)
      + gardenPath(x2 + 0.25, -0.95 + d + 0.48, 2.3, 0.4)
      + gardenBush(-2.1, 1.2, 0.26)
      + gardenBush(1.9, 1.2, 0.26)
      + leafyTree(2.2, -1.8, 0.9);
  },

  // 4. Multi-Family with 2 - 4 Units: edificio de 2 plantas con accesos múltiples y ritmo de vanos
  'Multi-Family with 2 - 4 Units': () => {
    const x = -1.45, y = -1.0, zPlinth = 0.18, w = 2.8, d = 2.05, h = 1.95, r = 0.55;
    return dropShadow(x, y, w, d)
      + plinth(x, y, 0, w, d, zPlinth)
      + box(x, y, zPlinth, w, d, h)
      // Cornisa / moldura intermedia entre piso 1 y piso 2
      + box(x - 0.03, y - 0.03, zPlinth + 0.95, w + 0.06, d + 0.06, 0.07, 'cornice-l', 'cornice-r', 'cornice-t')
      // Techo a cuatro aguas / faldones
      + gableRoof(x, y, zPlinth + h, w, d, r, 0.14, 0.16)
      // Accesos dobles en planta baja
      + doorFront(x + 0.4, y + d, zPlinth, 0.38, 0.78)
      + doorFront(x + 1.25, y + d, zPlinth, 0.38, 0.78)
      + stepsFront(x + 0.32, y + d, zPlinth, 1.4, 0.26, 0.09)
      + porchCanopy(x + 0.28, y + d, zPlinth + 0.85, 1.48, 0.32, 0.06)
      // Ventanas piso 1 (PB)
      + winFront(x + 1.95, y + d, zPlinth + 0.2, 0.55, 0.55)
      // Ventanas piso 2 (PA, simétricas)
      + winFront(x + 0.35, y + d, zPlinth + 1.15, 0.5, 0.55)
      + winFront(x + 1.15, y + d, zPlinth + 1.15, 0.5, 0.55)
      + winFront(x + 1.95, y + d, zPlinth + 1.15, 0.5, 0.55)
      // Ventanas fachada lateral
      + winSide(x + w, y + 0.45, zPlinth + 0.22, 0.5, 0.5)
      + winSide(x + w, y + 1.25, zPlinth + 0.22, 0.45, 0.5)
      + winSide(x + w, y + 0.45, zPlinth + 1.15, 0.5, 0.5)
      + winSide(x + w, y + 1.25, zPlinth + 1.15, 0.45, 0.5)
      // Acceso y sendero
      + gardenPath(x + 0.65, y + d + 0.52, 2.35, 0.75)
      + gardenBush(x - 0.5, y + d + 0.2, 0.3)
      + gardenBush(x + w + 0.15, y + d + 0.2, 0.3)
      + leafyTree(-2.3, 1.3, 0.95);
  },

  // 5. Multi-Family with 5+ Units: bloque urbano multifamiliar de 3.5 plantas, azotea con casetón y portal vidriado
  'Multi-Family with 5+ Units': () => {
    const x = -1.25, y = -1.05, zPlinth = 0.2, w = 2.45, d = 2.1, h = 3.1;
    return dropShadow(x, y, w, d)
      + plinth(x, y, 0, w, d, zPlinth)
      + box(x, y, zPlinth, w, d, h)
      // Cornisas horizontales de entrepiso (división visual de niveles)
      + box(x - 0.02, y - 0.02, zPlinth + 0.9, w + 0.04, d + 0.04, 0.05, 'cornice-l', 'cornice-r', 'cornice-t')
      + box(x - 0.02, y - 0.02, zPlinth + 1.85, w + 0.04, d + 0.04, 0.05, 'cornice-l', 'cornice-r', 'cornice-t')
      + box(x - 0.02, y - 0.02, zPlinth + 2.8, w + 0.04, d + 0.04, 0.05, 'cornice-l', 'cornice-r', 'cornice-t')
      // Parapeto / antepecho de remate en azotea
      + box(x - 0.04, y - 0.04, zPlinth + h, w + 0.08, d + 0.08, 0.16, 'parapet-l', 'parapet-r', 'parapet-t')
      // Casetón de ascensor y cuarto de máquinas en azotea
      + box(x + 0.55, y + 0.45, zPlinth + h + 0.16, 0.85, 0.75, 0.5, 'mach-l', 'mach-r', 'mach-t')
      + chimney(x + 1.6, y + 0.8, zPlinth + h + 0.16, 0.18, 0.18, 0.35)
      // Portal principal vidriado en planta baja con marquesina urbana
      + doorFront(x + 0.85, y + d, zPlinth, 0.75, 0.78)
      + porchCanopy(x + 0.75, y + d, zPlinth + 0.84, 0.95, 0.38, 0.06)
      + stepsFront(x + 0.8, y + d, zPlinth, 0.85, 0.22, 0.08)
      // Cuadrícula regular de ventanas de apartamentos en fachada frontal
      // Nivel 1 (planta baja)
      + winFront(x + 0.2, y + d, zPlinth + 0.22, 0.45, 0.5)
      + winFront(x + 1.8, y + d, zPlinth + 0.22, 0.45, 0.5)
      // Nivel 2
      + winFront(x + 0.2, y + d, zPlinth + 1.1, 0.45, 0.5)
      + winFront(x + 1.0, y + d, zPlinth + 1.1, 0.45, 0.5)
      + winFront(x + 1.8, y + d, zPlinth + 1.1, 0.45, 0.5)
      // Nivel 3
      + winFront(x + 0.2, y + d, zPlinth + 2.05, 0.45, 0.5)
      + winFront(x + 1.0, y + d, zPlinth + 2.05, 0.45, 0.5)
      + winFront(x + 1.8, y + d, zPlinth + 2.05, 0.45, 0.5)
      // Ventanas en fachada lateral derecha
      + winSide(x + w, y + 0.35, zPlinth + 0.22, 0.42, 0.5)
      + winSide(x + w, y + 1.15, zPlinth + 0.22, 0.42, 0.5)
      + winSide(x + w, y + 0.35, zPlinth + 1.1, 0.42, 0.5)
      + winSide(x + w, y + 1.15, zPlinth + 1.1, 0.42, 0.5)
      + winSide(x + w, y + 0.35, zPlinth + 2.05, 0.42, 0.5)
      + winSide(x + w, y + 1.15, zPlinth + 2.05, 0.42, 0.5)
      // Pavimento urbano frontal y alcorque
      + gardenPath(x + 0.78, y + d + 0.44, 2.38, 0.9)
      + box(x - 0.7, y + d + 0.2, 0, 0.45, 0.45, 0.12, 'plinth-l', 'plinth-r', 'plinth-t')
      + leafyTree(x - 0.6, y + d + 0.3, 0.75);
  },
};

const NAMES_ES = {
  'Mobile Home': 'casa móvil',
  'Single-Family Detached': 'vivienda unifamiliar aislada',
  'Single-Family Attached': 'vivienda unifamiliar adosada',
  'Multi-Family with 2 - 4 Units': 'edificio de 2 a 4 viviendas',
  'Multi-Family with 5+ Units': 'edificio de 5 o más viviendas',
};

export function isoHouse(housingType) {
  const key = SHAPES[housingType] ? housingType : 'Single-Family Detached';
  const shape = SHAPES[key];
  const ground = poly([[-3, -2.4, 0], [3, -2.4, 0], [3, 2.4, 0], [-3, 2.4, 0]], 'ground')
    + poly([[-3, 2.4, -0.18], [3, 2.4, -0.18], [3, 2.4, 0], [-3, 2.4, 0]], 'ground-l')
    + poly([[3, -2.4, -0.18], [3, 2.4, -0.18], [3, 2.4, 0], [3, -2.4, 0]], 'ground-r');
  const label = `Ilustración exterior de ${housingType ? NAMES_ES[key] : 'una vivienda genérica'} (conceptual; sin interiores ni cifras)`;
  return `<svg class="iso" viewBox="0 0 380 270" role="img" aria-label="${label}"><title>${label}</title><g class="iso-g">${ground}${shape()}</g></svg>`;
}
