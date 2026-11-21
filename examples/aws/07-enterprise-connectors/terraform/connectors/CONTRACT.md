# Local source-contract qualification

These adapters consume a normalized snapshot contract from explicitly configured endpoints. They are not native Microsoft Graph or Confluence REST adapters. SharePoint/Confluence permission mapping, group expansion, inherited restrictions, API paging and tenant authentication must be independently qualified before real integration. Local fixtures prove this contract only.

An endpoint returns snapshotId, complete=true, permissionsComplete=true and documents (maximum 100). Each document supplies sourceId, sourceVersion, title, text, allowedSubjects and allowedRegions. The entire snapshot must be complete before publishing; missing entries are deletions. Unknown or incomplete permissions fail closed. Redirects are refused; HTTPS is required except with the explicit loopback fixture option. Credentials come from ATMEM_SOURCE_TOKEN.

Run connector_cli.py with the exact source ID in sources.json, reviewed endpoint/catalog/account/region, a private checkpoint path and --confirm-sync. It journals pending inventory before writes and commits after reconciliation. Retry from the same checkpoint after failure; conditional revisions prevent blind overwrites. Use one designated sync runner per source. A local lock prevents overlapping runs; review a stale lock after a crash rather than blindly deleting it.

Source-derived document access expires after 60 seconds unless refreshed by a complete authorized snapshot. Refresh more often than the lease, monitor failures and test timing. Expired documents are excluded before model invocation and response delivery. This favors access revocation over stale-source availability. Do not remove the lease to make outage tests pass.
