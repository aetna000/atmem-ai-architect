// Generated operator tool; never run during export or local schema/mock qualification.
export function modelPolicyPreflightFiles(){return {
 'verify-model-policy.py':`"""Read-only model policy check. Account access needs separate authorization."""
import argparse
import json
import re

def inspect_policy(session,expected_account):
    from botocore.config import Config
    config=Config(connect_timeout=2,read_timeout=5,retries={"total_max_attempts":1})
    identity=session.client("sts",config=config).get_caller_identity()
    if identity.get("Account")!=expected_account:return {"status":"blocked","reason":"Unexpected AWS account; no model policy was read."}
    client=session.client("bedrock",config=config)
    mode=client.get_account_data_retention().get("mode")
    logging=client.get_model_invocation_logging_configuration().get("loggingConfig",{})
    verified=mode=="none" and isinstance(logging,dict) and logging.get("textDataDeliveryEnabled",False) is False
    return {"status":"passed" if verified else "blocked","retentionMode":mode,"textLoggingDisabled":isinstance(logging,dict) and logging.get("textDataDeliveryEnabled",False) is False,"boundary":"Read-only policy observation; not model-quality, authentication or deployment evidence."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account",required=True);parser.add_argument("--region",required=True);parser.add_argument("--confirm-read",action="store_true")
    args=parser.parse_args()
    if not args.confirm_read:parser.error("Obtain authorization for account access before supplying --confirm-read")
    if not re.fullmatch(r"[0-9]{12}",args.account) or not re.fullmatch(r"[a-z]{2}-[a-z]+-[1-9]",args.region):parser.error("Supply the exact commercial AWS account and region")
    try:
        import boto3
        result=inspect_policy(boto3.Session(region_name=args.region),args.account)
    except Exception:result={"status":"unavailable","reason":"Policy read failed. Check the hash-locked SDK installation, authorized credential chain and read permissions; no policy was changed."}
    print(json.dumps(result));return 0 if result["status"]=="passed" else 2

if __name__=="__main__":raise SystemExit(main())
`,
 'MODEL-POLICY.md':`# Verify model data handling\n\nThe structured operation requires regional Bedrock account retention mode none and disabled text invocation logging. It reads these controls before sending input and fails closed when verification is unavailable. It never changes account policy.\n\nAfter authorization for read-only account access, install the hash-locked runtime requirements in an isolated operator environment, then run:\n\n\`python3 verify-model-policy.py --account REVIEWED_12_DIGIT_ACCOUNT --region REVIEWED_REGION --confirm-read\`\n\nKeep the returned observation with the account/region and timestamp in protected deployment evidence. A passing read is not a model-quality or deployment test. Check that the selected model is available with this policy. Changing an account-wide setting can affect other workloads; obtain separate approval and review existing systems. Use a suitable isolated account/region when a shared account cannot satisfy this contract. Never relax the policy or replace the client's no-retention requirement just to make inference work.\n\nThe operator needs sts:GetCallerIdentity, bedrock:GetAccountDataRetention and bedrock:GetModelInvocationLoggingConfiguration. These are reads; credentials remain outside the package.\n`
};}
