// Ilustración isométrica CONCEPTUAL de un tipo de vivienda. No es un plano ni un modelo
// de habitaciones: no contiene cuartos, termostatos, interruptores ni luces.
const S = 40, OX = 190, OY = 118, C = Math.cos(Math.PI / 6), SN = 0.5;
const P = (x, y, z) => [OX + (x - y) * C * S, OY + (x + y) * SN * S - z * S];
const poly = (pts, cls) => `<polygon class="${cls}" points="${pts.map((p) => P(...p).map((n) => n.toFixed(1)).join(',')).join(' ')}"/>`;

function box(x, y, z, w, d, h) {
  return poly([[x, y + d, z], [x + w, y + d, z], [x + w, y + d, z + h], [x, y + d, z + h]], 'f-left')
    + poly([[x + w, y, z], [x + w, y + d, z], [x + w, y + d, z + h], [x + w, y, z + h]], 'f-right')
    + poly([[x, y, z + h], [x + w, y, z + h], [x + w, y + d, z + h], [x, y + d, z + h]], 'f-top');
}
// Techo a dos aguas con cumbrera paralela a x
function gable(x, y, z, w, d, r) {
  const m = y + d / 2;
  return poly([[x, y + d, z], [x + w, y + d, z], [x + w, m, z + r], [x, m, z + r]], 'roof-a')
    + poly([[x + w, y, z], [x + w, y + d, z], [x + w, m, z + r]], 'roof-g')
    + poly([[x, y, z], [x + w, y, z], [x + w, m, z + r], [x, m, z + r]], 'roof-b');
}
const tree = (x, y) => poly([[x, y, 0], [x + .35, y, 0], [x + .35, y + .35, 0], [x, y + .35, 0]], 'trunk')
  + poly([[x - .15, y - .15, .25], [x + .5, y - .15, .25], [x + .5, y + .5, .25], [x - .15, y + .5, .25]], 'leaf-a')
  + poly([[x - .05, y - .05, .75], [x + .4, y - .05, .75], [x + .4, y + .4, .75], [x - .05, y + .4, .75]], 'leaf-b');

const SHAPES = {
  'Mobile Home': () => box(-1.6, -.7, 0, 3.2, 1.4, .85) + box(1.6, -.4, 0, .5, .8, .12),
  'Single-Family Detached': () => box(-1.5, -1, 0, 2.4, 2, 1.2) + gable(-1.5, -1, 1.2, 2.4, 2, .9) + box(.9, -.6, 0, 1, 1.4, .7),
  'Single-Family Attached': () => box(-1.8, -1, 0, 1.8, 2, 1.2) + gable(-1.8, -1, 1.2, 1.8, 2, .8) + box(0, -1, 0, 1.8, 2, 1.2) + gable(0, -1, 1.2, 1.8, 2, .8),
  'Multi-Family with 2 - 4 Units': () => box(-1.5, -1, 0, 3, 2, 1.9) + box(-1.5, -1, 1.9, 3, 2, .12),
  'Multi-Family with 5+ Units': () => box(-1.1, -1, 0, 2.2, 2, 3.4) + box(-1.1, -1, 3.4, 2.2, 2, .12),
};

export function isoHouse(housingType) {
  const shape = SHAPES[housingType] || SHAPES['Single-Family Detached'];
  const ground = poly([[-3, -2.4, 0], [3, -2.4, 0], [3, 2.4, 0], [-3, 2.4, 0]], 'ground')
    + poly([[-3, 2.4, -.18], [3, 2.4, -.18], [3, 2.4, 0], [-3, 2.4, 0]], 'ground-l')
    + poly([[3, -2.4, -.18], [3, 2.4, -.18], [3, 2.4, 0], [3, -2.4, 0]], 'ground-r');
  const t = (housingType === 'Multi-Family with 5+ Units') ? '' : tree(-2.5, 1.6);
  return `<svg class="iso" viewBox="0 0 380 270" aria-hidden="true" focusable="false"><g class="iso-g">${ground}${t}${shape()}${housingType === 'Multi-Family with 5+ Units' ? '' : tree(2.2, -1.9)}</g></svg>`;
}
