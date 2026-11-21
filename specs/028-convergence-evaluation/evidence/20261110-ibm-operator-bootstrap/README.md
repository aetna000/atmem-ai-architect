# IBM operator CLI password binding repair

The native bootstrap calls its password reader with purpose and principal. The
operator CLI supplied a one-argument callback, so IBM initialization failed before
creating its first SQL login. The retained regression reproduces the TypeError.
The corrected callback accepts and verifies both fields against the owned binding.

The CLI now creates both restricted logins with private SCRAM credentials, passes
schema/grant admission, permits their required reads and denies audit deletion.
All four CLI tests pass on local PostgreSQL 17 and 18; the aggregate API suite passes
62 checks. No secret values are included. The private loopback transport substitute
is explicit; this does not validate an IBM endpoint or complete native deployment.
