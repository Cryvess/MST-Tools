# Security

Do not post live credentials or private source in public issues. For MSTTools vulnerabilities,
use GitHub private vulnerability reporting if enabled, or contact the maintainer privately.

`audit` and `security` are heuristic checks, not security certification. `jwt` never verifies signatures.
`deps` does not query advisory databases or resolve transitive dependencies.
Only serve directories you intend to expose to local processes. Review report filenames and dependencies
before sharing them.
