# AWS native partition lowering

The78bab01 China ARN defect is repaired for supplied-image units without changing
their selected region, provider or ownership. Native aws_partition metadata now
supplies ECS trust ARN partitions. Native guards compare metadata to the selected
commercial/China/GovCloud region family, and require ECR ARN partition and region
family to agree. Exact repository grants and scoped account/region trust remain;
no cross-partition application or network connection is inferred.

The provider's pinned data-source source reads configured client metadata with
region override disabled. It is not an additional account-resource discovery
query. Actual qualifier plans use explicit mock data, not cloud credentials.
Independent inspection rejects metadata/provider substitution, hardcoded trust,
removed native region/repository checks and wildcard-grant changes.

Invoice support is a separate domain policy. Its commercial ARN/registry/model
contracts cannot inherit supplied-image support. China/GovCloud invoice requests
retain their original region and implementation blocker. Independent inspection
still refuses completeness if planner gaps and root blockers are suppressed.
Producer canonical-region validation retains valid GovCloud identifiers without
inventing adapter availability or rewriting them into another destination.

Evidence:

- `before-native/cn-north-1/test.log`: the unmodified frozen78bab01 compiler passes
  its8 generated mock tests, then fails an independent exact ARN assertion: actual
  arn:aws:ecs:cn-north-1 versus required arn:aws-cn:ecs:cn-north-1. Only a separate
  oracle test was added; generated implementation was untouched. Frozen source
  and dependency aliases remain on MEM0.
- `after.json`: the same public mixed-project counterexample now retains China
  placement and derives trust from native partition metadata.
- `native-v3/summary.json`:7 current packages,97 native mock-plan runs, all passed.
  Five standalone region cases span commercial, both China regions and both
  GovCloud regions; a commercial invoice plus China instrument and a three-
  partition independent composition demonstrate transfer. Independent oracles
  assert literal trust ARNs and deny foreign repository/region/partition values.
- `four-provider-v1/summary.json`:12 existing standalone/mixed/two-region
  regression packages,108 native mock plans, all passed across four providers.
- `service-commercial-invoice-china-container/receipt.json` and
  `service-three-independent-partitions/receipt.json`: actual public service
  generation/admission/native checks pass both/three modules,20+33=53 unit mock
  plans. These overlap the diagnostic cases and are not additional generality or
  complete-project acceptances.
- `js-tests-release.log`:537 passed, no failures/skips. `server-tests.log`:430
  passed. `build-final.log`: production build passed.
- `generated-final-manifest.json` and `final-artifact-comparison.json`: final
  changes after native-v3 are supplied-image README text only; configuration,
  tests, locks and separate oracles are identical. Four-provider regression
  manifest records its exact earlier artifact bytes separately.
- `source-manifest.json`: exact source/checker hashes; `references.json`: pinned
  AWS6.72.0 schema/source and dated primary partition/service-principal sources.

Preserved unsuccessful attempts are excluded: v1's separate oracle used invalid
single-line HCL formatting; v2 exposed an invalid generated-test expectation that
a dependent service would also evaluate after its IAM-policy precondition failed.
Separate cases now exercise the policy denial and the service region-family guard
independently, with coherent foreign repository data for the latter. No guard,
negative test or acceptance requirement was removed. The before compiler's
expected oracle failure remains a failure, not a current pass or live blocker.

Terraform1.17.1 with cached AWS6.72.0 performs init -backend=false, validate and
mock-provider plan tests only. Root composition gates may defer data reads; unit
plans exercise resolved fixtures separately. This does not prove regional ECS/
Fargate/model availability, destination IAM, registry/image behavior, TLS/network
access, deployment or an application system. Other AWS partitions remain outside
this supplied-image contract. No cloud/account access or deployment occurred.

The previously reported supplied-image partition release blocker is resolved.
GE-005 remains in progress pending frozen runnable alpha.4 qualification and its
manual card/rollback records. Three increments and1/28 full local originals remain
the current counts; overall quality is unmeasured. Remaining application contracts,
judgment, knowledge, recovery, all28 and unfamiliar local block/connection/system
evaluations remain required. No owner preview/UI/job was changed.
