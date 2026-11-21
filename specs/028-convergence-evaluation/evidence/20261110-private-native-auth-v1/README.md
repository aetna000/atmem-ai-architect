# Private identity, native OAuth and encrypted store checkpoint

The existing company API identity verifier, actual MSAL Graph protocol/cache path,
Confluence Cloud confidential 3LO driver and encrypted transactional source store
are implemented. The retrieval coordinator checks live company access as well as
source document access before context/release. Final local evidence: 34 contract/
policy/SDK/crypto tests, 16 restricted native SQL tests on each PG17 and PG18, 347 JS
and 214 server tests. Original private-knowledge requirements remain unchanged.

The first SQL test caught FOR SHARE requiring authority-table UPDATE privilege.
The fix preserves the broker's read-only authority grants; it does not grant that
write access. Independent refresh intents/revision fencing allow disconnection or
revocation while HTTP runs. Tests cover one-use concurrent callbacks, browser/
person/source binding, replay/expiry, encryption context isolation, native SDK+
SQL composition, process crash/uncertainty, token rotation and late responses.
A later integration failure caught MSAL's shorter default state not meeting the
store's strong-binding format. The driver now supplies its own 32-byte random state;
the binding check was not weakened. Initial failures are retained separately.

Five primary documentation bodies were reviewed and hashed locally; metadata is
preserved here. Twelve dependencies are sliced deterministically from existing
reviewed pins and metadata, without upgrades or network resolution. Their clean
Linux installation/runtime/security composition remains unqualified.

No browser/controller, real IdP/source consent, cloud key/secret transport, key
rotation/recovery, native cloud footprint or complete medium case is claimed.
API callbacks/session/CSRF, isolated extraction/model/audit and all4 export wiring
remain next. No cloud account, publish, plan/apply or deployment ran. Private fixture
credentials, encrypted fixture databases and dumps are excluded from this archive.
