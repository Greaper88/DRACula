# Runtime and third-party packaging

DRACula's browser frontend has no third-party JavaScript or remotely loaded fonts.
The backend dependencies are listed in `requirements.txt`; their installed license
metadata remains in the image. Debian package notices remain under `/usr/share/doc`.

## Java runtime

The verified legacy runtime is the public Azul Zulu CA build:

- Package: `zulu8.98.0.107-ca-jdk8.0.512-linux_i686.tar.gz`
- Vendor URL: https://cdn.azul.com/zulu/bin/zulu8.98.0.107-ca-jdk8.0.512-linux_i686.tar.gz
- SHA-256: `791ddba1fd02ce0cf84301c57ce3315839a0966afb960174f4354016a579148c`

The full extracted distribution is retained, including its LICENSE,
ASSEMBLY_EXCEPTION, DISCLAIMER, THIRD_PARTY_README and source archive. The worker
uses an external Java security-properties file; it does not rewrite the runtime.

OpenJDK licensing includes GPLv2 with the Classpath Exception and additional
component notices. Azul also distinguishes its public CA and subscriber offerings.
Preserving license texts alone does not discharge all binary-redistribution
requirements; corresponding-source obligations and the precise bundled components
must be addressed for a public runtime-included release. The shipped `src.zip`
should not be assumed to contain the complete corresponding native/JVM source.

By default, images build with `BUNDLE_JAVA=false`. That image does
not redistribute the Java binary; the deploying user's container downloads it
directly from the vendor on first launch. This separates runtime distribution from
the application image, rather than claiming it removes every license obligation.

References:

- Azul licensing information: https://docs.azul.com/core/tpls/july-2026/zulu8_jdk_tpl.html
- Azul CA/SA build guidance: https://support.azul.com/hc/en-us/articles/360051512551-What-s-the-difference-between-CA-and-SA-bundles-of-Azul-Zulu-Builds-of-OpenJDK
- Azul repository/redistribution guidance: https://support.azul.com/hc/en-us/articles/360058780152-How-is-the-repository-for-Zulu-different-since-Jul-2020

## Dell viewer

The proprietary `avctDRAC5Viewer.jar` is downloaded from the user's own authorized
DRAC, never committed or copied into the image build context. Its SHA-256 must
match the reviewed version before the read-only adapter runs. Only DRACula's
adapter source is included in the repository and image.
