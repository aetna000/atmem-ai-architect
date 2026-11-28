# AtMem branding in the handoff website

Local Architect candidate `0.2.8-handoff.2` regenerated the existing NextDNS-style reference project at revision 1. Its saved design, project ID, requirements and decisions match the prior delivery.

[Open the handoff](http://127.0.0.1:5286/) · [Open Architect](http://127.0.0.1:5185/)

## Shared reader

Project overviews, work orders, module handoffs and authored guides use AtMem’s official horizontal wordmark, favicon, DM Sans and Manrope. The website includes the light and dark artwork, licensed fonts, and a single local stylesheet. The preview and downloaded pages use the same generator. The reader links the wordmark to AtMem and credits the logo artist. [AtMem website](https://atmem.ai/) · [Artwork and font digests](../../../../docs/brand-source.json)

The connection overview uses AtMem pink on ink. Generated sequence and fallback drawings use rose arrows and pale pink participant cards. Native drawings retain their project colors.

## Verification

| Check | Result |
| --- | --- |
| Installed app | Opened the previous project from its exported snapshot, previewed the website, opened a work order and downloaded the ZIP. A separate local test directory held the project. |
| Offline Chrome on macOS | All 12 pages decoded the official wordmark and loaded both font families from the ZIP. All 95 local links and nine drawings resolved. The browser issued zero network requests. |
| Reader layout | All seven sections worked at 320, 390, 768 and 1440 pixels. Dark mode selected the light-ink wordmark. Print selected the dark-ink wordmark and included all seven sections. |
| Transfer and missing assets | A freight project exercised a module and a nested guide. Removed alternative artwork, stylesheet and favicon each failed the link check. |
| Distributed copy | All 30 files in the ZIP matched both the extracted folder and the live reader over HTTP. The production app served the same entry point and handoff bundle as the tested installation. |
| Regression | 789 JavaScript tests passed and the production build completed. The engineering archive verified 180 payload digests. Its independent project check confirmed 11 interfaces, 10 case definitions and eight typed views. |

The delivered ZIP SHA-256 is `6c3d0bd37907367e412eca96398d3b420ca64a4ffb43a164675df736247cce35`. [Browser receipt](browser-review.json) · [Desktop](overview-light.png) · [Dark](overview-dark.png) · [Mobile](overview-mobile.png)

## Manual check

1. Open the handoff and follow **Build plan → Policy publisher**. The work order carries the same wordmark and typefaces.
2. Extract the ZIP and open **index.html** with networking disabled. Switch the system appearance and open print preview to inspect the wordmark.

## Rollback

The previous site and ZIP are in `.local/team-handoff-delivered`. The previous app executable is `.local/team-handoff-candidate/release-install/node_modules/.bin/atmemai`. To restore that version, run its `restart --port 5185 --data-dir .local/team-handoff-candidate/home --no-open` command from the repository.
