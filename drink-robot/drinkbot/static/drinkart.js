/* DrinkArt — draws a picture of a drink from its recipe.
 *
 *   DrinkArt.svg({ glass: "highball", garnish: "lime",
 *                  layers: [{ color: "#ff9d1c", tint: 1, ml: 135, last: false }, ...] })
 *
 * The liquid color is a mix of the ingredient colors weighted by ml × tint
 * (clear spirits have a low tint, juices a high one). Ingredients marked
 * `last` (e.g. grenadine in a Sunrise) sink to the bottom as a separate band.
 * Used by the real app's menu and by the static demo site.
 */
(function (root) {
  let uid = 0;

  function hex(c) {
    c = c.replace("#", "");
    return [0, 2, 4].map(i => parseInt(c.substr(i, 2), 16));
  }
  function toHex(rgb) {
    return "#" + rgb.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
  }
  function mix(layers) {
    let w = 0, ml = 0, acc = [0, 0, 0];
    layers.forEach(l => {
      const k = l.ml * l.tint, c = hex(l.color);
      acc = acc.map((v, i) => v + c[i] * k);
      w += k; ml += l.ml;
    });
    if (!w) return { color: "#e8eef2", opacity: 0.22 };
    const density = w / Math.max(ml, 1);
    return { color: toHex(acc.map(v => v / w)), opacity: Math.max(0.24, Math.min(0.92, 0.2 + density * 0.85)) };
  }
  function shade(color, f) { return toHex(hex(color).map(v => f < 0 ? v * (1 + f) : v + (255 - v) * f)); }

  // Glass interiors (where liquid can be) and outlines, in a 200×200 box.
  const GLASSES = {
    highball: { inside: "M67 42 L133 42 L129 172 L71 172 Z", top: 42, bottom: 172, fill: 0.78, ice: 3, straw: true,
      outline: "M64 38 L136 38 L131 176 L69 176 Z", base: "M69 176 L131 176 L131 184 L69 184 Z", rimL: 64, rimR: 136 },
    rocks: { inside: "M58 92 L142 92 L138 168 L62 168 Z", top: 92, bottom: 168, fill: 0.72, ice: 2,
      outline: "M54 88 L146 88 L141 172 L59 172 Z", base: "M59 172 L141 172 L141 182 L59 182 Z", rimL: 54, rimR: 146 },
    martini: { inside: "M42 58 L158 58 L100 124 Z", top: 58, bottom: 124, fill: 0.86, ice: 0,
      outline: "M36 52 L164 52 L100 128 Z", stem: true, rimL: 36, rimR: 164 },
    mug: { inside: "M64 66 L136 66 L136 166 L64 166 Z", top: 66, bottom: 166, fill: 0.9, ice: 0, opaque: "#b8733a",
      outline: "M60 60 L140 60 L140 170 Q140 178 132 178 L68 178 Q60 178 60 170 Z", handle: true, rimL: 60, rimR: 140 },
    solo_16: { inside: "M60 50 L140 50 L129 172 L71 172 Z", top: 50, bottom: 172, fill: 0.8, ice: 0, opaque: "#c8282e",
      outline: "M56 46 L144 46 L132 176 L68 176 Z", rimL: 56, rimR: 144 },
  };

  function garnishSvg(kind, g) {
    const x = g.rimR - 6, y = g.top - (g.stem ? 8 : 6);
    switch (kind) {
      case "lime":
      case "lemon": {
        const rind = kind === "lime" ? "#5f9e2f" : "#e9c626", flesh = kind === "lime" ? "#cfe79a" : "#fbef9e";
        const segs = [0, 60, 120, 180, 240, 300].map(a => {
          const r = a * Math.PI / 180;
          return `<line x1="${x}" y1="${y}" x2="${x + Math.cos(r) * 15}" y2="${y + Math.sin(r) * 15}" stroke="${rind}" stroke-width="1.2" opacity=".6"/>`;
        }).join("");
        return `<g><circle cx="${x}" cy="${y}" r="19" fill="${rind}"/><circle cx="${x}" cy="${y}" r="16" fill="${flesh}"/>${segs}<circle cx="${x}" cy="${y}" r="2.2" fill="${rind}" opacity=".7"/></g>`;
      }
      case "orange":
        return `<g transform="translate(${x} ${y + 4})"><path d="M-22 0 A22 22 0 0 1 22 0 Z" fill="#f08a10"/><path d="M-18 0 A18 18 0 0 1 18 0 Z" fill="#ffc14d"/>` +
          [30, 60, 90, 120, 150].map(a => { const r = a * Math.PI / 180; return `<line x1="0" y1="0" x2="${-Math.cos(r) * 17}" y2="${-Math.sin(r) * 17}" stroke="#f08a10" stroke-width="1.2" opacity=".7"/>`; }).join("") + `</g>`;
      case "cherry":
        return `<g><path d="M${x - 4} ${y - 2} Q${x + 2} ${y - 26} ${x + 16} ${y - 30}" fill="none" stroke="#4a6b2a" stroke-width="2.4" stroke-linecap="round"/><circle cx="${x - 4}" cy="${y + 4}" r="10" fill="#b5122b"/><circle cx="${x - 7}" cy="${y + 1}" r="3" fill="#ff8a9a" opacity=".7"/></g>`;
      case "pineapple":
        return `<g transform="translate(${x} ${y})"><path d="M-16 8 L16 8 L0 -18 Z" fill="#f5cf3b" stroke="#d8a91c" stroke-width="1.5"/><path d="M-3 -16 Q-10 -34 -2 -40 Q0 -28 2 -16 Z M3 -16 Q12 -32 8 -38 Q4 -26 0 -16 Z" fill="#3f8a3a"/></g>`;
      default:
        return "";
    }
  }

  function svg(spec, opts) {
    opts = opts || {};
    const g = GLASSES[spec.glass] || GLASSES.highball;
    const id = "da" + (++uid);
    const main = spec.layers.filter(l => !l.last), sink = spec.layers.filter(l => l.last);
    const m = mix(main.length ? main : spec.layers);
    const total = spec.layers.reduce((a, l) => a + l.ml, 0) || 1;
    const sinkFrac = sink.reduce((a, l) => a + l.ml, 0) / total;
    const h = g.bottom - g.top, surface = g.bottom - h * g.fill;
    const parts = [];

    parts.push(`<defs>
      <clipPath id="${id}c"><path d="${g.inside}"/></clipPath>
      <linearGradient id="${id}l" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="${shade(m.color, -0.18)}"/><stop offset=".45" stop-color="${shade(m.color, 0.12)}"/><stop offset="1" stop-color="${shade(m.color, -0.25)}"/>
      </linearGradient>
      <radialGradient id="${id}g" cx=".5" cy=".62" r=".55"><stop offset="0" stop-color="${m.color}" stop-opacity="${0.28 * m.opacity + 0.06}"/><stop offset="1" stop-color="${m.color}" stop-opacity="0"/></radialGradient>
      ${sink.length ? `<linearGradient id="${id}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mix(sink).color}" stop-opacity="0"/><stop offset=".55" stop-color="${mix(sink).color}" stop-opacity=".95"/><stop offset="1" stop-color="${shade(mix(sink).color, -0.2)}"/></linearGradient>` : ""}
    </defs>`);
    if (!opts.noGlow) parts.push(`<rect x="0" y="0" width="200" height="200" fill="url(#${id}g)"/>`);
    // table shadow
    parts.push(`<ellipse cx="100" cy="${g.stem ? 186 : (g.base ? 185 : 181)}" rx="${(g.rimR - g.rimL) / 2 + 6}" ry="5" fill="#000" opacity=".35"/>`);

    if (g.stem) {
      parts.push(`<rect x="97.5" y="126" width="5" height="52" fill="#fff" opacity=".28"/><ellipse cx="100" cy="180" rx="30" ry="5" fill="#fff" opacity=".22"/>`);
    }
    if (g.handle) {
      parts.push(`<path d="M140 82 Q166 84 166 112 Q166 140 140 142" fill="none" stroke="${shade(g.opaque, -0.2)}" stroke-width="9" stroke-linecap="round"/>`);
    }
    if (g.opaque) {
      // opaque cup/mug: body color, liquid only visible at the rim
      parts.push(`<path d="${g.outline}" fill="${g.opaque}"/>`);
      parts.push(`<path d="M${g.rimL + 10} ${g.top + 12} L${g.rimL + 16} ${g.bottom - 10}" stroke="#fff" stroke-opacity=".22" stroke-width="7" stroke-linecap="round"/>`);
      parts.push(`<ellipse cx="100" cy="${g.top + 2}" rx="${(g.rimR - g.rimL) / 2 - 3}" ry="7" fill="${m.color}" opacity="${Math.max(0.75, m.opacity)}"/>`);
      parts.push(`<ellipse cx="100" cy="${g.top - 1}" rx="${(g.rimR - g.rimL) / 2}" ry="8" fill="none" stroke="${shade(g.opaque, 0.35)}" stroke-width="3"/>`);
    } else {
      parts.push(`<path d="${g.outline}" fill="#fff" opacity=".05"/>`);
      if (g.base) parts.push(`<path d="${g.base}" fill="#fff" opacity=".2"/>`);
      const liq = [];
      liq.push(`<rect x="0" y="${surface}" width="200" height="${200 - surface}" fill="url(#${id}l)" opacity="${m.opacity}"/>`);
      if (sink.length) {
        const sh = Math.max(14, (g.bottom - surface) * Math.min(0.55, sinkFrac * 2.4));
        liq.push(`<rect x="0" y="${g.bottom - sh * 1.6}" width="200" height="${sh * 1.6}" fill="url(#${id}s)"/>`);
      }
      // ice
      for (let i = 0; i < g.ice; i++) {
        const cx = 76 + (i * 23) % 50 + (g.ice === 2 ? 10 : 0), cy = surface + 4 + (i % 2) * 16, s = g.ice === 2 ? 30 : 24, rot = [-12, 9, -4][i % 3];
        liq.push(`<rect x="${cx}" y="${cy}" width="${s}" height="${s}" rx="5" transform="rotate(${rot} ${cx + s / 2} ${cy + s / 2})" fill="#fff" fill-opacity=".14" stroke="#fff" stroke-opacity=".45" stroke-width="1.2"/>`);
      }
      liq.push(`<rect x="0" y="${surface - 1}" width="200" height="3" fill="#fff" opacity=".35"/>`);
      parts.push(`<g clip-path="url(#${id}c)">${liq.join("")}</g>`);
      if (g.straw) parts.push(`<path d="M${g.rimL + 24} ${g.bottom - 18} L${g.rimL + 8} ${g.top - 30}" stroke="#ff9f1c" stroke-width="6" stroke-linecap="round"/><path d="M${g.rimL + 24} ${g.bottom - 18} L${g.rimL + 8} ${g.top - 30}" stroke="#fff" stroke-width="6" stroke-dasharray="6 6" stroke-linecap="round" opacity=".6"/>`);
      parts.push(`<path d="${g.outline}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2.2" stroke-linejoin="round"/>`);
      parts.push(`<path d="M${g.rimL + 9} ${g.top + 6} L${g.rimL + 13} ${g.bottom - 12}" stroke="#fff" stroke-opacity=".28" stroke-width="4" stroke-linecap="round"/>`);
    }
    if (spec.garnish && spec.garnish !== "none") parts.push(garnishSvg(spec.garnish, g));
    const label = opts.label ? ` role="img" aria-label="${String(opts.label).replace(/"/g, "&quot;")}"` : ` aria-hidden="true"`;
    return `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"${label}>${parts.join("")}</svg>`;
  }

  root.DrinkArt = { svg, mix };
})(typeof window !== "undefined" ? window : globalThis);
