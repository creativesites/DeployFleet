# Brand assets

Drop the new DeployFleet logo/icon files here. This directory lives inside
`deployfleet_ui` (not at the repo root) because Odoo only serves files from
a module's own `static/` tree — anything placed outside a module's
`static/` folder is unreachable by the web client, so this is the one
place in the repo a logo file can actually be referenced from CSS/XML.

Once a file is added here, it's reachable at:

```
/deployfleet_ui/static/img/brand/<filename>
```

e.g. `background: url(/deployfleet_ui/static/img/brand/logo-mark.svg);` in
any component SCSS, or `<img src="/deployfleet_ui/static/img/brand/logo-full.svg"/>`
in any OWL template.

## Expected files (add as available — none of this is wired up yet)

| Filename | Use |
|---|---|
| `logo-full.svg` | Full wordmark + icon, light backgrounds (Launcher header, Help Center, login screen) |
| `logo-mark.svg` | Icon-only square mark, for small chrome (Launcher trigger button, favicon source, Command Palette) |
| `logo-white.svg` | White/light variant of the mark, for use on the brand gradient or dark Command Layer surfaces |
| `favicon.ico` | Browser tab icon |
| `favicon-192.png`, `favicon-512.png` | PWA/mobile home-screen icons, if/when the driver/dispatcher/customer apps in `MOBILE_ARCHITECTURE.md` need them |

## Also worth updating separately, not part of this directory

`custom_addons/deployfleet_core/static/description/icon.png` is a
different Odoo convention entirely — the module icon shown in Odoo's own
Apps list — and should be swapped for the new logo mark once available.
It isn't touched by this directory or by anything that reads from it.
