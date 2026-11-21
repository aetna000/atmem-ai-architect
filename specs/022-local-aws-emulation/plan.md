# Plan

1. Pin optional Moto dependencies and notices.
2. Implement a provider-neutral job/result contract and local subprocess backend, accepting only a project through the trusted generator.
3. Provision supported stateful services from generated contracts; run actual emitted handlers and connector/catalog code. Exercise versions, duplicate/poison messages, conditional writes, ACLs, revocations, updates and deletes. Clearly label scripted model/auth transport.
4. Add pre-download emulation controls and stale-result cancellation to both output views.
5. Validate all seven examples, failure injection, isolation, unsupported coverage and UI flow. Archive reproducible reports under examples/aws/evidence/emulation without changing prior evidence.
6. Document hosted worker requirements and emulator gaps separately from product failures.

Constitution: explicitly user-authorized local simulation only; outputs distinguish all evidence levels; no secret loading; current project is sole source; no extra memory side effects; compact visible UI results; regression + boundary + real browser tests.
