# IBM fixed invoice operating tasks

This package delivers initialize/maintain/monitor task definitions, an explicit
owned cron installer/observer, and Cloud Logs alert definitions. Local tests do not
prove real native execution, log routing, notification delivery or deployment.

Foundation uses applications_enabled=false, operations_enabled=false and
maintenance_enabled=false. Publish
the reviewed immutable runtime image into the owned registry only when authorized.
Set operations_enabled=true with applications still false to create fixed tasks.
Populate the separate operator SQL secret outside Terraform. databaseConfig also
needs operator_user: the exact administrative login for this new owned database.
Only initialize receives the separate API and worker SQL password keys. No task
receives the accounting token, parser token, model or object-store authority.

The destination operator installs/authenticates IBM Cloud CLI and its reviewed Code
Engine plugin in a dedicated private CLI home. For example, set IBMCLOUD_HOME to
this package's .local/ibm-operator-cli during login/plugin setup. Keep that directory
mode 0700 and outside source control. Never copy a user's global CLI credentials.

Preview: python3 scripts/run-operator.py initialize
Authorized execution adds --execute. The helper reads this package's Terraform
output, explicitly selects its account/region/project in the isolated CLI home,
then submits the fixed task with --wait. It supplies no image, environment, command
or service-account overrides. Job-launch permission is privileged; do not grant it
to the application, worker, model or public user. Retain the actual completed job
and initialized:true/monitor/maintenance receipt, not merely submit acceptance.

After bootstrap, run maintain and monitor once and inspect actual successful
receipts in the existing Cloud Logs destination. Verify that regional Code Engine
platform logging is routed to operator_logs_instance_id through the existing
account routing. Review its region/data custody and the existing outgoing
notification integration. Do not replace account log routing or expose credentials.
Read terraform output -json operator_log_queries for resolved queries; monitoring/
files are readable Terraform expression templates, not resolved instance selectors.
The Lucene filters use documented app/codeengine.projectGuid/region/component and
message/level fields, never deprecated label.Namespace/Project/Stream fields.
Verify the actual native samples match each emitted query before enabling alerts;
account parsing/routing can change message layout. Missing SQL monitor alerts after
two hours; missing daily maintenance after 36 hours. Undetected values trigger
missing-run alerts; native zero-sample evaluation/delivery still need acceptance.
Notifications exclude payload fields; no invoice/subject/amount is emitted by jobs.

Keep applications false, set maintenance_enabled=true, apply reviewed alerts, then
preview python3 scripts/run-operator.py install-schedules. With authorized --execute,
the helper uses supported Knative PingSource and IBM JobDefinition APIs in this
project's isolated KUBECONFIG. Only maintain (02:17 UTC daily) and monitor (hourly at
minute 7) are scheduled. Initialize is never scheduled. It refuses unrelated source
ownership and uses native resourceVersion to avoid overwriting concurrent changes.
Use check-schedules --execute to observe configuration and current Ready generation.
Ready means reconciled source configuration, not successful SQL work. Retain actual
successful scheduled task/log/alert delivery evidence before application release.
Cron sources are explicitly operated resources outside Terraform because IBM 2.9
has no cron subscription resource; do not hide account writes in a provisioner.
Before rollback, identify the two exact owned PingSource names/UIDs, verify their
owner references and remove only those sources with the authorized native operator;
do not delete the namespace/project. Disable alerts during an approved maintenance
window. Installed sources persist independently of the Terraform boolean: changing
maintenance_enabled=false does not pause or delete an installed source.

Each task uses one array index, no automatic retries and a 960-second platform
limit; the application enforces its own 900-second work deadline. Private SQL TLS,
actual native login privileges, task outcome, schedules and alert delivery still
need separately authorized destination checks. Provider schema/mocks are not
deployment, SQL runtime or scheduling evidence.
