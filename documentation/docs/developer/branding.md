---
title: Logos and Branding
reviewers: Dr Simon Chapman, Marcus Baw
---

## Logos and Branding

The RCPCH Design Team have given us help and advice in ensuring the RCPCH Incubator builds products which adhere to RCPCH Brand Guidance.

In addition they have created custom logos for our projects and even our teams. These logo files are present in the `docs/_assets/_images` folder of [this repository](https://github.com/rcpch/national-paediatric-diabetes-audit/tree/live/documentation/docs/_assets/_images).

## RCPCH Brand Guidance

The RCPCH full brand guidance can be found [here](https://github.com/rcpch/rcpch-private/tree/main/branding-colours) (private repository, access for RCPCH team only)

## Use of TailwindCSS

Note that the NPDA audit uses [TailwindCSS](https://tailwindcss.com/) with custom variables to conform to RCPCH branding.

!!! info "Tailwind CSS CLI - Using watch to speed up development"
    Tailwind is a large package, so "tree-shakes" unused CSS classes on build. Because of this, it is necessary to rebuild the styles.css file (i.e., "rerun treeshaking") when adding Tailwind classes to templates that haven't been used elsewhere. By rebuilding, Tailwind will automatically find and add classes to styles.css. 
    
    For one-off rebuilds:
    ```console
    docker compose exec -it django npm run build:css
    ```
    
    To avoid multiple rebuilds, you can leverage Tailwind's CLI `watch` command using: 
    ```console
    docker compose exec -it django npm run watch:css
    ```
