# Contributing

DRACula is an early public preview. Keep desktop and web behavior in the shared
core where practical, and hide capabilities a controller does not support.

## Getting started

Use Python 3.12+, JDK 17+, and Node.js 22.8+ for development checks:

```sh
python3 -m venv .venv
.venv/bin/pip install -r apps/web/requirements-test.txt
PYTHON_BIN=.venv/bin/python ./scripts/check.sh
```

See [release validation](docs/release-validation.md) for Docker checks and
[architecture](docs/architecture.md) for the device/worker boundaries. Node is
used only for frontend tests. Do not add live hardware to automated tests.

## Hardware and credentials

Read [AGENTS.md](AGENTS.md) before working on the repository. Authorization is
specific to a device and action. A status read or console test does not authorize
power operations, configuration changes, firmware updates, virtual media, log
clears, controller resets or remote input.

Use documentation IP addresses and synthetic credentials in fixtures. Never
commit passwords, keys, cookies, JNLP tickets, vaults, raw hardware responses,
downloaded runtimes or proprietary device binaries. Keep legacy TLS confined to
device-facing workers; do not relax the browser-facing connection or system Java.

## Pull requests

Explain the concrete behavior changed, validation performed and material limits.
Add meaningful regression coverage for behavior fixes. Include UI screenshots
where appearance changed, without identifying hardware or exposing credentials.
Keep a human review of generated code and the rights to submit all contributed
material. Do not claim tests passed if they were skipped or not run.

Contributions intentionally submitted for inclusion are under Apache License 2.0,
unless explicitly stated otherwise and agreed with the maintainer. Preserve
existing copyright and third-party notices; do not apply DRACula's license to
vendor binaries or downloaded runtimes.

## Required AI disclosure

AI assistance is allowed and must be disclosed for code, tests, documentation and
other contributed material. For each AI-assisted commit, include these exact
trailers; include the same block in its pull-request description:

```text
AI-Agent: {agent name}
AI-Model-Version: {model name and complexity, request from author if necessary}
AI-Inference-Date: {timestamp}
```

Use an ISO 8601 inference timestamp with a timezone, such as
`2026-10-31T05:15:46-05:00`. Name the actual agent/tool, exact model and reasoning
or complexity setting. Ask the author when a model or setting is not available;
do not guess or silently omit it. Use a separate block for each agent/model
involved. Do not attribute past contributions without evidence.

For changes that have not been committed, record the current block in
[AI_DISCLOSURE.md](AI_DISCLOSURE.md), then carry it into the commit and PR. The
repository's current disclosure does not replace disclosure of later work.
Human-only contributions can state that no AI assistance was used in the PR.
The optional `.gitmessage` template is available with:

```sh
git config --local commit.template .gitmessage
```
