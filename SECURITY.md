# Security

## Trust model

`dredge.toml` executes arbitrary commands: the `runner` key is an argv that dredge runs verbatim. Treat config files like Makefiles - do not run a `dredge.toml` you have not read. dredge itself never invokes a shell and never expands runner arguments.

`dredge config` prints runner argv verbatim; redact credentials before sharing its output.

## Reporting

Report vulnerabilities privately via GitHub Security Advisories on this repository (Security tab -> Report a vulnerability). Expect an acknowledgment within a week; fixes to the dredge scheduler itself are in scope, misbehavior of arbitrary configured runners is not.
