# CAFM

Computer-Aided Facility Management application built on Frappe, ERPNext, and HRMS.

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
bench new-site cafm.example.com
```

Bench will ask for the MariaDB root password and a new Frappe Administrator password. Do not place either password in the repository.

### 3. Install the apps in dependency order

```bash
bench --site cafm.example.com install-app erpnext
bench --site cafm.example.com install-app hrms
bench --site cafm.example.com install-app cafm
```

The CAFM installer creates its roles and permission rules and applies the required custom fields and configuration. It does not require modifying ERPNext core files.

### 4. Migrate and build assets

```bash
bench --site cafm.example.com migrate
bench build --app cafm
bench restart
```

Use `bench start` instead of `bench restart` in a development bench.

## Verify the installation

Confirm that all four apps are listed:

```bash
bench --site cafm.example.com list-apps
```

The output must include `frappe`, `erpnext`, `hrms`, and `cafm`. Then sign in as Administrator and confirm that the CAFM workspace and Facility Management dashboard open.

For a development or test site, run the automated business-rule and installation checks:

```bash
bench --site cafm.example.com set-config allow_tests true
bench --site cafm.example.com run-tests --app cafm
```

Do not enable tests on a production site.

## Updating CAFM

Back up the site before updating:

```bash
bench --site cafm.example.com backup --with-files
cd apps/cafm
git pull origin main
cd ../..
bench --site cafm.example.com migrate
bench build --app cafm
bench restart
```

## Troubleshooting

- **`App erpnext is not installed` or `App hrms is not installed`:** install ERPNext and HRMS on the same site before CAFM.
- **Database connection refused:** start MariaDB and verify the site's `db_host` and `db_port` values.
- **Access denied for the database administrator:** rerun `bench new-site` and enter the MariaDB root password when prompted; do not confuse it with the Frappe Administrator password.
- **Workspace or dashboard changes are missing:** run `bench --site cafm.example.com migrate`, rebuild CAFM assets, and clear the browser cache.
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
