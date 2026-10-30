#!/bin/sh
set -eu
DRACULA_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
rm -rf "$DRACULA_ROOT/.local/desktop/classes"
mkdir -p "$DRACULA_ROOT/.local/desktop/classes"
javac --release 17 -d "$DRACULA_ROOT/.local/desktop/classes" "$DRACULA_ROOT"/apps/desktop/java/dracula/*.java
jar --create --file "$DRACULA_ROOT/.local/desktop/dracula-manager.jar" --main-class dracula.Manager -C "$DRACULA_ROOT/.local/desktop/classes" .
