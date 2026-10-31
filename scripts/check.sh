#!/usr/bin/env bash
# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
DRACULA_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DRACULA_ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NODE_BIN="${NODE_BIN:-node}"
for command in "$PYTHON_BIN" "$NODE_BIN" java javac jar; do
  command -v "$command" >/dev/null || { printf 'Missing development tool: %s\n' "$command" >&2; exit 1; }
done
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"; import cryptography, fastapi, httpx, PIL, Xlib'
"$NODE_BIN" -e 'if((v=>v[0]<22||(v[0]===22&&v[1]<8))(process.versions.node.split(".").map(Number)))throw Error("Node.js 22.8+ required for the checks")'
export PYTHONPATH="$DRACULA_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON_BIN" -m unittest discover -s tests -v
"$NODE_BIN" --test --test-isolation=none tests/web_*.test.cjs
./apps/desktop/build.sh
mkdir -p .local/desktop/test-classes
javac --release 17 -cp .local/desktop/dracula-manager.jar -d .local/desktop/test-classes apps/desktop/tests/dracula/*.java
for source in apps/desktop/tests/dracula/*Test.java; do
  test_name="$(basename "$source" .java)"
  java -Djava.awt.headless=true -cp .local/desktop/dracula-manager.jar:.local/desktop/test-classes "dracula.$test_name"
done
