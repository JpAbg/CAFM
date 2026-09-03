# CAFM Dashboard Frontend

This directory contains the Vue and Vite frontend assets used by CAFM dashboards.

## Development

From this directory:

    yarn install
    yarn dev

## Production build

Build CAFM assets from the Bench root so Frappe publishes them correctly:

    bench build --app cafm

Do not treat this frontend as a separate deployable application. It is packaged and served by the CAFM Frappe app.

## Required backend apps

The CAFM app requires Frappe version 15, ERPNext version 15, and HRMS version 15.
