"""Read-only checks against a saved Terraform plan; never applies or changes quotas."""
import argparse
import json
from pathlib import Path
import boto3
from botocore.config import Config

def concurrency_requirement(plan):
    required=0
    for item in plan.get("resource_changes",[]):
        if item.get("type")!="aws_lambda_function":continue
        change=item["change"]
        if change.get("actions")==["delete"]:continue
        after=(change.get("after") or {}).get("reserved_concurrent_executions")
        before=(change.get("before") or {}).get("reserved_concurrent_executions")
        if not isinstance(after,int) or after<1:raise ValueError("A positive explicit function concurrency bound is required")
        # A replacement must reserve fresh capacity; do not rely on destruction ordering.
        previous=before if isinstance(before,int) and before>0 and "delete" not in change.get("actions",[]) else 0
        required+=max(0,after-previous)
    return required

def check_concurrency(plan,limits):
    needed=concurrency_requirement(plan)
    available=max(0,int(limits["UnreservedConcurrentExecutions"])-100)
    return {"name":"lambda-reserved-concurrency-capacity","passed":needed<=available,"additionalRequired":needed,"availableForReservation":available,"accountLimit":limits["ConcurrentExecutions"],"action":None if needed<=available else "Request and wait for an appropriate regional concurrency quota increase; do not remove the per-function limit to bypass this check."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json",type=Path,required=True)
    parser.add_argument("--receipt",type=Path,required=True)
    args=parser.parse_args();plan=json.loads(args.plan_json.read_text())
    values={key:entry.get("value") for key,entry in plan.get("variables",{}).items()}
    account=values.get("aws_account_id");region=values.get("aws_region")
    if not isinstance(account,str) or len(account)!=12 or not account.isdigit() or not isinstance(region,str):raise SystemExit("The plan must contain the reviewed AWS account and region")
    session=boto3.Session(region_name=region)
    config=Config(connect_timeout=5,read_timeout=20,retries={"total_max_attempts":2},ignore_configured_endpoint_urls=True)
    identity=session.client("sts",config=config).get_caller_identity()
    if identity["Account"]!=account:raise SystemExit("Account mismatch; target service checks were not run")
    checks=[]
    if any(r.get("type")=="aws_lambda_function" for r in plan.get("resource_changes",[])):
        limits=session.client("lambda",config=config).get_account_settings()["AccountLimit"]
        checks.append(check_concurrency(plan,limits))
    models=sorted({value for key,value in values.items() if key.endswith("_model_id") and isinstance(value,str)})
    if models:
        bedrock=session.client("bedrock",config=config)
        for model in models:
            availability=bedrock.get_foundation_model_availability(modelId=model)
            details=bedrock.get_foundation_model(modelIdentifier=model)["modelDetails"]
            checks.append({"name":"bedrock-control-plane-availability","modelId":model,"passed":availability.get("authorizationStatus")=="AUTHORIZED" and availability.get("regionAvailability")=="AVAILABLE" and availability.get("entitlementAvailability")=="AVAILABLE" and "ON_DEMAND" in details.get("inferenceTypesSupported",[]),"runtimeInvocation":"not_tested"})
    result={"kind":"read-only-account-preflight","status":"passed" if all(c["passed"] for c in checks) else "blocked","accountSuffix":account[-4:],"region":region,"checks":checks,"deployment":"not_run","limitations":"Does not establish apply permissions, model quality, runtime authorization, recovery, billing or production readiness."}
    args.receipt.parent.mkdir(parents=True,exist_ok=True);args.receipt.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
    if result["status"]!="passed":raise SystemExit(1)
if __name__=="__main__":main()
