# DRAC 5 field semantics

Both applications use `dracula.field_schema` to distinguish configurable fields,
reported status and unverified fields. The **Access** column shows
**Configurable**, **Configurable · locked**, **Read only**, or **Unverified**. The
form registry describes inferred capability; only fields with a complete,
reviewed submission mapping and controller permission receive an editor. The
shared configuration core independently enforces a single-use exact-change review
and confirmation tied to the selected controller. There are no address-specific
write blocks. Live checks require authorization for the selected device.

The registry was reviewed against read-only GETs of the test controller's static DRAC 5 forms:
`nic`, `services`, `serial`, `sol`, `ad`, `user`, `adrgconfig`, `vkvmconfig`,
`vmconfig`, `listpef`, `pef`, `pefdest` and `pefemail`. Localized wrappers identify
the original forms. Named inputs, checkbox conditions, select options and mapped
XML variables supply the evidence. The application does not download or execute
these forms at runtime. Raw XML, XSL and credentials are not part of the registry.

| Page | Configurable candidates identified in the original forms |
| --- | --- |
| Network | NIC mode and enable, DHCP, addresses, DNS, VLAN, link settings, IPMI over LAN and privilege limit |
| Services | Service enable flags, web/SSH/Telnet ports and timeouts, local configuration restrictions |
| Serial / SOL | Enable, redirection, baud rate, connection/flow-control modes, privilege limit, timeout and escape/history settings |
| Users / Directory | User enable/name, SOL and privilege settings; directory enable, SSO, schema, domains, servers and role groups |
| Alerts | Event alert/action flags, trap destination enable/address, SMTP server, email destination enable/address/description |
| KVM | Console enable, ports, encryption, local display, viewer type and sharing-access policy |
| Virtual media | Attachment mode, ports, key enable, viewer type and boot-device selector |

Secrets such as passwords, community strings and encryption keys are deliberately
excluded from status rows, even when the vendor form can change them. They will
need dedicated approved flows; these secrets remain excluded from the editor.

True binary fields use switches (passive on read-only devices) with **Enabled/Disabled** or **True/False**
for factual/negative flags. Two-choice settings retain their actual labels, such
as Java/Native or Full/Half duplex. Numeric counters, IDs and ports remain numbers.
Unknown values never silently become false. Unreviewed fields remain unverified.

Some names are misleading: `BootOnceEnabled` is a multi-value boot-device selector,
`AuthorizeMultipleSessions` has No access / Read-only access / Full access, and
virtual-media `Attached` supports Detached / Attached / Auto attach. These retain
select semantics rather than becoming boolean switches. Boot choice 1 is labeled
Virtual media or vFlash according to the controller capability when editing.

Configurable candidates still depend on hardware support, firmware, user
privileges and other settings. `dracula.configuration` now defines reviewed form
routes, record selectors, checkbox omission, validation, preserved fields and
confirmation/readback handling. Its submission paths are tested with synthetic
controllers. No live configuration write has been performed during implementation.

Validation covered all eleven configuration tabs on the test controller through the web API,
with no page-read errors. The actual desktop bridge returned typed service rows,
and both rendered layouts were inspected. Offline checks cover negative flags,
unknown codes, multi-value selectors, repeated records, secret redaction and
non-interactive controls. other controllers were not accessed; no configuration change,
remote input, power operation or KVM session was needed.

The editor leaves fields locked when their original whole form cannot be
preserved safely. Reviews bind to an opaque loaded snapshot and compare the full
stable configuration of every affected record. Only the changed values appear in
the review; untouched secrets remain server-side and are never included in UI
metadata. Repeated user/role/filter/destination identifiers come from the captured
record, not the client. Alert destination writes explicitly use `test=0`.
