# Security Policy

Please report vulnerabilities privately through GitHub's security advisory
feature for this repository. Do not include proprietary GDS files in reports.

Project config loading executes Python and is intended only for trusted files.
Native cache entries are executable libraries; keep the default private user
cache, and treat a custom `EBEAMTIME_NATIVE_CACHE_DIR` as a trusted boundary.
