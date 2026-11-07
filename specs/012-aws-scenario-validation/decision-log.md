# Validation decisions

## 2026-11-07 — AWS test scope

User authorized Australian-region tests and up to $20 total, with US access checks if Bedrock or SageMaker requires them. Select Sydney (ap-southeast-2) as the initial candidate for proximity, without claiming it is the cheapest region. Currency was not specified; use AUD as the conservative planning assumption before paid work. No spending occurred during this preflight.

STS identity succeeded. Bedrock control-plane checks report Nova Micro and Nova Lite authorized and available in Sydney, Northern Virginia and Oregon. This is not an inference test or a guarantee of runtime quota. SageMaker is not needed for the immediate storage scenario and was not probed or provisioned.

The first storage export remains blocked by its operator identity and access integration gaps. Preserve those gates until the product implements a reviewed binding. Do not edit exported Terraform to bypass them.

## Qualification loop before cloud execution

User clarified that AWS deployment is the final verification stage after fixing AI Architect, its skills and generated artifacts. Two conversational rounds per scenario now preserve original and refined outputs. Evaluator changes reject explicit-service/label contradictions, disconnected graphs and empty Terraform. AWS/Terraform/DevOps specialist guidance updated to 1.1.0 with refreshed integrity hashes; registry now reports the actual file version. No cloud operations are part of this loop.
