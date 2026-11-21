# Local normalized source contracts

The user explicitly approved local connector test servers for this stage. Implement complete normalized source snapshots with explicit resolved ACLs, source ownership, conditional updates/deletes, durable pending inventory, retry recovery and short authorization leases. Never treat incomplete permissions as public access. Expired source authorization must be excluded before model invocation and response delivery.

This contract is not a native Microsoft Graph or Confluence REST implementation. Tenant authentication, group expansion, inherited restrictions and vendor paging still require real source adapters and qualification. Production exports with these local source bindings remain blocked; staging contract success must not remove that gate. Preserve the web application requirement and deferred Teams scope.
