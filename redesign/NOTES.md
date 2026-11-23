# Redesign: now applied to the live templates

The block-logo redesign is applied in `templates/` and `static/styles.css`.
The files in this folder (`index.html`, `competition-2026.html`, `redesign.css`) are the earlier standalone mockups.

## Reverting
`backup-before-redesign/` holds the pink design exactly as it was before the redesign
(all of `templates/`, plus `static/styles.css` and `static/site.js`). To revert:

    cp -R redesign/backup-before-redesign/templates/. templates/
    cp redesign/backup-before-redesign/static/styles.css redesign/backup-before-redesign/static/site.js static/
    rm static/gic-logo-white.svg

`DESIGN.md` was also updated to describe the new look.
