# CAFM

Computer-Aided Facility Management application built on Frappe, ERPNext, and HRMS.

For everyday operational use, see the [CAFM User Guide](USER_GUIDE.md).

## Requirements

- **Frappe Framework:** version 15
- **ERPNext:** version 15
- **HRMS:** version 15
- **Database:** MariaDB 10.11 is the tested configuration
- A working Frappe Bench with Redis, Node.js, Yarn, and Bench installed

## Compatibility

CAFM currently targets the version 15 release line. The clean-site installation was verified with:

- Frappe 15.118.0
- ERPNext 15.119.1
- HRMS 15.63.2
- MariaDB 10.11

ERPNext and HRMS are required apps and must be installed on the site before CAFM.

## Clean-site installation

Start from a working Frappe Bench with MariaDB, Redis, Node.js, Yarn, and Bench installed.

### 1. Download the required apps

Skip an app that is already present in your bench's `apps` directory.

```bash
cd /path/to/frappe-bench
bench get-app --branch version-15 erpnext
bench get-app --branch version-15 hrms
bench get-app --branch main https://github.com/JpAbg/CAFM.git
```

### 2. Create a site

```bash
bench new-site cafm-test.localhost
```

For a local development machine, a .localhost site name opens without editing the hosts file.

Bench will ask for the MariaDB root password and a new Frappe Administrator password. Do not place either password in the repository.

For a deployed environment, replace cafm-test.localhost with your real site domain in every command below.

### 3. Install the apps in dependency order

```bash
bench --site cafm-test.localhost install-app erpnext
bench --site cafm-test.localhost install-app hrms
bench --site cafm-test.localhost install-app cafm
```

The CAFM installer creates its roles and permission rules and applies the required custom fields and configuration. It does not require modifying ERPNext core files.

### 4. Migrate and build assets

```bash
bench --site cafm-test.localhost migrate
bench build --app cafm
bench restart
```

Use bench start instead of bench restart in a development bench. Then open the local address shown by Bench, normally http://cafm-test.localhost:8000.

## Verify the installation

Confirm that all four apps are listed:

```bash
bench --site cafm-test.localhost list-apps
```

The output must include `frappe`, `erpnext`, `hrms`, and `cafm`. Then sign in as Administrator and confirm that the CAFM workspace and Facility Management dashboard open.

For a development or test site, run the automated business-rule and installation checks:

```bash
bench --site cafm-test.localhost set-config allow_tests true
bench --site cafm-test.localhost run-tests --app cafm
```

Run the test suite only in a development environment with Frappe test dependencies installed. Do not enable tests on a production site.

## Updating CAFM

Back up the site before updating:

```bash
bench --site cafm-test.localhost backup --with-files
cd apps/cafm
git pull origin main
cd ../..
bench --site cafm-test.localhost migrate
bench build --app cafm
bench restart
```

## Troubleshooting

- **`App erpnext is not installed` or `App hrms is not installed`:** install ERPNext and HRMS on the same site before CAFM.
- **ModuleNotFoundError for another local app:** remove the stale app from the bench configuration or install that app into the same bench. A clean CAFM bench only needs Frappe, ERPNext, HRMS, and CAFM.
- **Login page appears unstyled:** rebuild assets after confirming that the bench environment imports Frappe from that bench's own apps/frappe directory, then hard-refresh the browser.
- **Database connection refused:** start MariaDB and verify the site's `db_host` and `db_port` values.
- **Access denied for the database administrator:** rerun `bench new-site` and enter the MariaDB root password when prompted; do not confuse it with the Frappe Administrator password.
- **Workspace or dashboard changes are missing:** run `bench --site cafm-test.localhost migrate`, rebuild CAFM assets, and clear the browser cache.
- **Production install fails:** restore the pre-install backup, keep the full command output, and compare the installed Frappe, ERPNext, and HRMS branches with the supported version 15 line.

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/cafm
pre-commit install
```

The configured checks include Ruff, ESLint, Prettier, and pyupgrade.

## License

MIT
