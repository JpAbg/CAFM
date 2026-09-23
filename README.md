# CAFM — Computer-Aided Facility Management

A facility-management application built on Frappe, ERPNext, and HRMS for managing facilities, assets, maintenance operations, employees, vendors, utilities, and operational workflows.

CAFM also includes a mobile-ready Client Portal and an Android application built with Capacitor.

For everyday operational use, see the [CAFM User Guide](USER_GUIDE.md).

## Requirements

- **Frappe Framework:** version 15
- **ERPNext:** version 15
- **HRMS:** version 15
- **Database:** MariaDB 10.11 is the tested configuration
- A working Frappe Bench with Redis, Node.js, Yarn, and Bench installed

For Android development or APK builds, you also need:

- npm
- Android Studio and the Android SDK
- Java/JDK compatible with the Android build environment

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

For a local development machine, a `.localhost` site name opens without editing the hosts file.

Bench will ask for the MariaDB root password and a new Frappe Administrator password. Do not place either password in the repository.

For a deployed environment, replace `cafm-test.localhost` with your real site domain in every command below.

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

Use `bench start` instead of `bench restart` in a development bench.

Then open the local address shown by Bench, normally:

```text
http://cafm-test.localhost:8000
```

## Verify the installation

Confirm that all four apps are listed:

```bash
bench --site cafm-test.localhost list-apps
```

The output must include:

- `frappe`
- `erpnext`
- `hrms`
- `cafm`

Then sign in as Administrator and confirm that the CAFM Operations interface and Facility Management dashboard open.

For a development or test site, run the automated business-rule and installation checks:

```bash
bench --site cafm-test.localhost set-config allow_tests true
bench --site cafm-test.localhost run-tests --app cafm
```

Run the test suite only in a development environment with Frappe test dependencies installed. Do not enable tests on a production site.

## Client Portal

CAFM provides a Client Portal for employees and requesters at:

```text
/client-portal
```

The portal allows signed-in users to create and follow their facility requests from a browser or the CAFM Android app.

Normal Frappe authentication and CAFM permissions continue to apply. The Android application does not use a separate CAFM account or database.

## Android app

The CAFM dashboard project includes a Capacitor Android application under:

```text
apps/cafm/dashboard/android
```

The Android app provides a mobile application interface for the CAFM Client Portal while connecting to the same Frappe backend.

### Install dashboard dependencies

From the CAFM dashboard directory:

```bash
cd apps/cafm/dashboard
npm install
```

The project uses Capacitor, including the Capacitor App plugin for native Android application behaviour.

### Build the web application

Build the dashboard before synchronising Android when frontend files have changed:

```bash
npm run build
```

### Synchronise Capacitor

After changing the frontend or Capacitor configuration, run:

```bash
npx cap sync android
```

This copies the current web build and synchronises the installed Capacitor plugins with the Android project.

### Open the Android project

```bash
npx cap open android
```

Android Studio can then be used to run the application on a connected device or emulator and to produce Android builds.

Alternatively, a debug APK can be built from the command line:

```bash
cd android
./gradlew assembleDebug
```

The generated debug APK is placed under the Android project's build output directory.

### Network access

The Android device must be able to reach the CAFM server.

A development address such as:

```text
http://cafm.localhost:8000
```

that works on the development computer does not automatically resolve from a physical Android phone.

For development on a physical device, configure the app to use a CAFM address reachable from that device, such as the development machine's address on the same local network.

For production, use the deployed CAFM server address.

### Android Back button

Inside the Android app, the device Back button follows the Client Portal's navigation state.

For example, it can return from:

- a technician view to its request;
- a request to the previous request view;
- a create or edit view to the previous portal state.

When there is no previous portal state to restore, Back leaves the application.

This behaviour is specific to the Android application. Opening `/client-portal` directly in a normal browser continues to use normal browser navigation.

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

If the Android application's frontend or dependencies changed, also rebuild and synchronise the Android project:

```bash
cd apps/cafm/dashboard
npm install
npm run build
npx cap sync android
```

Rebuild the APK or Android application after synchronisation.

## Troubleshooting

- **`App erpnext is not installed` or `App hrms is not installed`:** install ERPNext and HRMS on the same site before CAFM.
- **ModuleNotFoundError for another local app:** remove the stale app from the bench configuration or install that app into the same bench. A clean CAFM bench only needs Frappe, ERPNext, HRMS, and CAFM.
- **Login page appears unstyled:** rebuild assets after confirming that the bench environment imports Frappe from that bench's own `apps/frappe` directory, then hard-refresh the browser.
- **Database connection refused:** start MariaDB and verify the site's `db_host` and `db_port` values.
- **Access denied for the database administrator:** rerun `bench new-site` and enter the MariaDB root password when prompted. Do not confuse it with the Frappe Administrator password.
- **Workspace or dashboard changes are missing:** run `bench --site cafm-test.localhost migrate`, rebuild CAFM assets, and clear the browser cache.
- **Client Portal works on the computer but not on the phone:** confirm that the Android device can reach the CAFM server address. A localhost address on the development computer is not the phone's localhost.
- **Android changes are missing:** rebuild the frontend if necessary and run `npx cap sync android` before rebuilding or running the Android application.
- **Android build fails:** confirm that Android Studio, the Android SDK, Java/JDK, npm dependencies, and the Capacitor Android project are correctly installed.
- **Production install fails:** restore the pre-install backup, keep the full command output, and compare the installed Frappe, ERPNext, and HRMS branches with the supported version 15 line.

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/cafm
pre-commit install
```

The configured checks include Ruff, ESLint, Prettier, and pyupgrade.

When changing the mobile frontend, rebuild and synchronise the Android project before testing the change on a device.

## License

MIT