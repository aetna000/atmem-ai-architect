# IBM fixed invoice operating tasks

This slice delivers initialize, maintain and monitor task definitions. It does not
yet deliver scheduled subscriptions or Cloud Logs alerts. Do not count it as full
operating acceptance or release the application on this evidence alone.

Foundation uses applications_enabled=false and operations_enabled=false. Publish
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

Each task uses one array index, no automatic retries and a 960-second platform
limit; the application enforces its own 900-second work deadline. Private SQL TLS,
actual native login privileges, task outcome, schedules and alert delivery still
need separately authorized destination checks. Provider schema/mocks are not
deployment, SQL runtime or scheduling evidence.
