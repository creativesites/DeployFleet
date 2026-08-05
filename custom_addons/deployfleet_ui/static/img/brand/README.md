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

Two raster lockups supplied by the user (Aug 2026) — no vector source
exists yet, so these are the only real assets, not a placeholder list:

| Filename | Size | Use |
|---|---|---|
| `logo-full-light-bg.png` | 1584×672, source-quality | Full wordmark + icon + tagline, navy text, for light backgrounds. Large — use `-web` variant in actual UI. |
| `logo-full-light-bg-web.png` | 760×322 | Same, downscaled for real on-screen use (login page, Help Center header). |
| `logo-full-dark-bg.jpg` | 597×244, source-quality | Same lockup, white text, for dark backgrounds. Low source resolution — visibly soft above ~300px display width. |
| `logo-mark.png` | 270×230 | Icon-only crop (the "D" mark), cropped from the light lockup. **Not a transparent cutout** — carries the light lockup's own subtle paper-texture background baked in, so it only reads cleanly on near-white/`--df-color-neutral-100`-ish surfaces, not on the brand gradient, dark Command Layer glass, or any other colored chrome. |
| `logo-mark-web.png` | 97×82 | Downscaled icon crop, for small chrome (login page badge, favicon source at current fidelity). |

## Still genuinely missing — get from the designer when possible

- A true vector (`logo-full.svg`, `logo-mark.svg`) — everything above is
  raster, so it will soften at large display sizes or high-DPI zoom.
- A transparent-background icon mark, for compositing onto the brand
  gradient, dark Command Layer glass, or any surface that isn't
  near-white — the current `logo-mark*.png` files cannot be used there
  without visible edge artifacts.
- `favicon.ico` / `favicon-192.png` / `favicon-512.png` — not generated
  yet; `logo-mark-web.png` is the best current source if one needs to be
  produced from what exists today, but a purpose-cut icon would look
  sharper at favicon sizes.

## Also worth updating separately, not part of this directory

`custom_addons/deployfleet_core/static/description/icon.png` is a
different Odoo convention entirely — the module icon shown in Odoo's own
Apps list — and should be swapped for the new logo mark once a proper
square asset (ideally vector or the transparent cutout above) exists. It
isn't touched by this directory or by anything that reads from it.
