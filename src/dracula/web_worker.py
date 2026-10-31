# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Web compatibility entry point for the shared console supervisor."""
from .console_session import ConsoleSession,RETRY_DELAYS

class ConsoleWorker(ConsoleSession):
    """A private Xvfb display with the shared saved-credential reconnect loop."""
