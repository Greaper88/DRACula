# Next steps

1. Inspect Java launch metadata without invoking console state transitions.
   Determine whether requesting JNLP allocates a session and what input controls
   exist before making that request under read-only authorization.
2. Identify viewer main class, JAR/native dependencies, platform architecture and
   compatible Java build. Download into private cache; record hashes and provenance.
3. Verify a view-only worker locally before connecting to live KVM. Build modern
   browser transport around that worker; demonstrate frontend isolation.
4. Add credential-store integration and bounded read-only DRAC transport using the
   observed XML endpoints. Select frontend and portable packaging after viewer
   constraints are understood.
5. Validate IPMI reads only where enabled, without enabling it on other devices.
6. Add explicit approvals and mutation support later using .252 when its owner
   brings it online and grants approval. Do not treat that future plan as approval.
