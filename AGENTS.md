# DRACula working rules

## Required AI disclosure — all agents and AI tools

These rules apply to every AI tool contributing code, tests, documentation or
other material in this repository, regardless of vendor or agent name.
AI-assisted work must be disclosed. Include the following exact fields as
commit-message trailers and in the corresponding pull-request description:

```text
AI-Agent: {agent name}
AI-Model-Version: {model name and complexity, request from author if necessary}
AI-Inference-Date: {timestamp}
```

Use the actual agent/tool name, exact model and reasoning/complexity setting, and
an ISO 8601 inference timestamp with a timezone. If the model or complexity is
not exposed, request it from the author before finalizing the disclosure; never
invent it. Use separate blocks for different agents/models. Do not falsely
attribute historical contributions or claim AI work was human-only.
When no commit is being made, record the block in AI_DISCLOSURE.md for the current
pending change and carry it into the eventual commit and PR. Follow
CONTRIBUTING.md and preserve LICENSE, NOTICE and third-party notices.

## Hardware and shared-core boundaries

Use one repository and shared core for desktop and web applications.
No hardware addresses or live targets are preapproved by this file. Obtain the
current user's authorization for each target and respect every exclusion. A
previous session's access or a device appearing in a profile is not authorization
for a new action. Use synthetic devices and documentation IP ranges for tests.

Never change settings, update firmware, reset a controller, clear logs, mount
virtual media, send remote keyboard/mouse input, or perform power operations
without explicit approval for that particular action. Read-only authorization
covers status and console metadata only. Do not launch an interactive viewer
until input suppression is verified or interactive access is explicitly approved.

Supported app settings stage local drafts and require an exact-target review and
confirmation before submission. Power has its own confirmed workflow. These app
features do not authorize agents to submit arbitrary live test writes. There
must be no lab-specific address allowlist or hardcoded runtime write blocks.

Interactive KVM starts with input disabled and offers an explicit switch. Keep
the vendor's original context/power menus and confirmations. Agent input tests
need separate target-specific authorization; enabling the feature in code does
not authorize a live key, click, power operation or configuration change.

Do not commit passwords, cookies, session identifiers, JNLP tickets, device
binaries, downloaded runtimes, or raw hardware responses. Store transient
material outside tracked files with restrictive permissions. Fresh installs must
start without server entries or embedded credentials. Removing all profiles must
leave an empty list across restarts.

Legacy TLS/Java compatibility must be confined to device-facing workers, never
applied globally or to browser-facing connections. The browser must never receive
DRAC credentials or direct device URLs. Preserve Apache and third-party notices
in source and binary distributions. Run the applicable offline checks documented
in CONTRIBUTING.md and docs/release-validation.md before handing off changes.
