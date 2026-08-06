# Brand assets

DeployFleet logo files. This directory lives inside `deployfleet_ui` (not
at the repo root) because Odoo only serves files from a module's own
`static/` tree — anything placed outside a module's `static/` folder is
unreachable by the web client, so this is the one place in the repo a
logo file can actually be referenced from CSS/XML.

Reachable at:

```
/deployfleet_ui/static/img/brand/<filename>
```

e.g. `background: url(/deployfleet_ui/static/img/brand/logo-mark.png);` in
any component SCSS, or `<img src="/deployfleet_ui/static/img/brand/logo-mark-web.png"/>`
in any OWL template.

## What's actually here today

The first batch (Aug 2026) was two raster lockups with baked-in
backgrounds. A second batch, supplied the same month, added real
transparent-background assets — those are now the preferred source for
anything that needs to sit on a colored or dark surface; the originals
are kept for their specific light/dark-background use cases.

| Filename | Size | Use |
|---|---|---|
| `logo-mark-transparent.png` | 169×171, real alpha transparency | **Preferred icon mark.** The "D" mark with a genuinely transparent background — safe to composite onto the brand gradient, dark Command Layer glass, or any colored chrome, unlike the earlier crop below. Used for the Odoo Apps-list module icon (`deployfleet_core/static/description/icon.png`, a direct copy of this file) and the Launcher header's brand mark. |
| `logo-mark-transparent-web.png` | 97×97 | Downscaled version of the above, for small chrome — this is what the Launcher header actually loads. |
| `logo-full-transparent.png` | 1146×292, real alpha transparency | **Preferred full lockup.** Icon + "DeployFleet" wordmark + tagline, navy text, transparent background, source quality. |
| `logo-full-transparent-web.png` | 760×194 | Downscaled version for real on-screen use. |
| `logo-full-light-bg.png` / `-web.png` | 1584×672 / 760×322 | First-batch lockup with an opaque light paper-texture background baked in — still fine on near-white surfaces (e.g. the login page, which already uses this one), but superseded by the transparent version above for anything else. |
| `logo-full-dark-bg.jpg` | 597×244, source-quality | White-text lockup for dark backgrounds. Low source resolution — visibly soft above ~300px display width. No transparent dark-text-on-light equivalent needed now that the transparent lockup composites cleanly on any surface. |
| `logo-mark.png` / `-web.png` | 270×230 / 97×82 | First-batch icon crop, **not transparent** (carries the light lockup's paper texture) — superseded by `logo-mark-transparent*.png` for new work; kept since nothing currently depends on removing it. |

## Still genuinely missing — get from the designer when possible

- A true vector (`logo-full.svg`, `logo-mark.svg`) — everything above is
  raster, so it will soften at large display sizes or high-DPI zoom.
- `favicon.ico` / `favicon-192.png` / `favicon-512.png` — not generated
  yet; `logo-mark-transparent-web.png` is a good source to produce one
  from, but a purpose-cut icon would look sharper at favicon sizes.

## Also worth knowing

`custom_addons/deployfleet_core/static/description/icon.png` (the Odoo
Apps-list module icon) is a direct copy of `logo-mark-transparent.png`,
not a reference to it — Odoo's module-icon convention doesn't support
loading from another module's `static/` tree, so the file is duplicated
there. If the mark is ever revised, that copy needs updating too.
