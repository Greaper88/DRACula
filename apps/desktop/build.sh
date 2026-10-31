#!/bin/sh
# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
set -eu
DRACULA_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec python3 "$DRACULA_ROOT/scripts/build-desktop.py"
