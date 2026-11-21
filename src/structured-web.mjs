import structuredWebSource from './runtime/structured-web-source.json' with {type:'json'};
import {RAG_WEB_HTML,RAG_WEB_CSS} from './rag-web-assets.mjs';
export const STRUCTURED_WEB_HTML=RAG_WEB_HTML.replaceAll('Knowledge assistant','AI workspace').replace('Answers grounded in documents you can access.','A bounded AI operation. Review every result before acting.').replace('Your question','Your input').replace('maxlength="2000"','maxlength="20000"').replace('>Ask</button>','>Process</button>').replace('>Answer</h2>','>Result</h2>').replace('<p id="answer"></p>','<dl id="answer"></dl>');
export const STRUCTURED_WEB_CSS=RAG_WEB_CSS.replace('#147d83','#F3A2B4').replace('color:white;padding','color:#182d38;padding')+'#answer dt{font-weight:600;margin-top:1rem;color:#526570}#answer dd{margin:.25rem 0 0;white-space:pre-wrap}';
export const STRUCTURED_WEB_JS=structuredWebSource;
export const STRUCTURED_WEB_GUIDE=`# Authenticated structured AI workspace

Private S3 assets are served through CloudFront. API Gateway validates Cognito access tokens, issuer, audience and atmem/ask scope. Authorization-code/S256 PKCE tokens remain in browser memory. Only administrator-created, MFA-enrolled users can sign in. The application does not persist input/results. Before sending input, the handler reads regional Bedrock account retention and requires mode none and disabled text invocation logging; unknown settings or a failed check stop inference. It never changes that account-wide setting. An authorized account owner must review shared workloads and preserve this policy.

The Lambda only admits the expected API ID and JWT route, checks the authoritative Cognito user's enabled/confirmed status and subject before model invocation and again before returning. A disabled user or identity outage fails closed. Administrators with broad IAM permissions remain a separate trust boundary. There is no direct end-user Lambda grant. Recheck destination IAM and organization policies.

Create/disable users through the AWS Cognito administrator workflow in the exact output user pool; distribute temporary credentials securely. Never put passwords in Terraform or source control. Disabling takes effect at the application check; an in-flight model request can still incur cost but its result is withheld if the user is disabled before the second check.

The operation returns schema-checked JSON and a human-review marker. Schema validation does not prove factual or classification accuracy. Establish representative model acceptance fixtures before deployment. There are no model tools or automated actions. Non-JSON, duplicate fields, unexpected fields, incorrect types, out-of-enum values and incomplete output fail closed. Retries are not automatic in the browser. Throttling, concurrency and output limits bound requests; they are not an account budget or an invoice cap.

See MODEL-POLICY.md for the authorized read-only account-policy check. Review source and run emitted application tests, provider schema/mocks, actual sign-in/MFA/revocation tests, model-quality tests and an authorized account plan. No cloud test, model correctness or deployment is established by export. Review CloudFront edge processing against any strict residency requirement; in-region inference does not establish whole-system residency.
`;
