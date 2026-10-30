# Web application boundary

Planned modern UI talks only to the DRACula backend. Backend workers own device
sessions, old TLS, runtime downloads and console execution. A browser-side Java
plugin or direct browser connection to the DRAC is not part of the design.
No running web server or browser console bridge exists yet.
