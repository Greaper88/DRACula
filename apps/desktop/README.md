# Desktop application boundary

Planned portable app using the shared core. Device communication and managed Java
processes remain behind a local service boundary. Runtime selection must include
OS, CPU architecture, Java version and any viewer native-library architecture.
Downloaded runtimes need pinned sources, hashes and license review. Legacy Java
settings belong to a dedicated runtime profile, not the user's system Java.
No desktop framework or release packaging has been selected yet.
