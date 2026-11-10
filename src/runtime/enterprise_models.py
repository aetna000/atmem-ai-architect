"""Owned private-answer operation over the reviewed native cloud transports.

The deployment chooses provider/model. Neither question nor source content can
select endpoints, tools, credentials, another operation/schema or a weaker policy.
The coordinator still validates exact supporting citations after this transport.
Construct one generator per engine; do not share mutable HTTP sessions across jobs.
"""
import json
from enterprise_knowledge import INSTRUCTION
from enterprise_sources import SourceUnavailable, query_text
from public_faq import answer_schema, object_pairs


def model_configuration(provider, environment):
    if provider not in {'aws', 'azure', 'gcp', 'ibm'}:
        raise ValueError('Supply the owned model provider')
    env = dict(environment)
    if provider == 'aws':
        from aws_json_model import read_model_config
    elif provider == 'azure':
        from azure_structured import read_model_config
    elif provider == 'gcp':
        from gcp_structured import read_model_config
    else:
        from ibm_structured import read_model_config
        # Workspace account IDs are not IBM cloud account IDs.
        env = {**env, 'ACCOUNT_ID': env['IBM_ACCOUNT_ID']}
    return read_model_config(env)


def native_generator(provider, environment):
    config = model_configuration(provider, environment)
    # Reuse the same account policy, identity, regional endpoints, response bounds
    # and no-tool checks already implemented for generated structured operations.
    if provider == 'aws':
        from aws_json_model import BedrockJsonModel
        model = BedrockJsonModel(config)
    elif provider == 'azure':
        from azure_structured import AzureModel
        model = AzureModel(config)
    elif provider == 'gcp':
        from gcp_structured import VertexModel
        model = VertexModel(config)
    else:
        from ibm_structured import WatsonModel
        model = WatsonModel(config)

    def generate(payload, schema, instruction):
        if schema != answer_schema() or instruction != INSTRUCTION:
            raise ValueError('Use the owned private-answer operation')
        if not isinstance(payload, str) or not 0 < len(payload.encode('utf-8')) <= 64000:
            raise ValueError('Private context exceeds its operation boundary')
        try:
            request = json.loads(payload, object_pairs_hook=object_pairs)
            if not isinstance(request, dict) or set(request) != {'question', 'articles'}:
                raise ValueError()
            query_text(request['question'])
            articles = request['articles']
            if not isinstance(articles, list) or not 1 <= len(articles) <= 80:
                raise ValueError()
            for article in articles:
                if (not isinstance(article, dict) or set(article) != {'id', 'revision', 'title', 'text'}
                    or any(not isinstance(article[key], str) or not article[key] for key in article)):
                    raise ValueError()
            if len({article['id'] for article in articles}) != len(articles):
                raise ValueError()
        except Exception:
            raise ValueError('Invalid owned private context') from None
        try:
            return model.generate(payload, schema, instruction)
        except Exception:
            # SDK exceptions can contain prompts, credentials or source bodies.
            # The queue owns bounded retries; no hidden transport fallback.
            raise SourceUnavailable('knowledge_model_unavailable') from None
    return generate


def validate_configured_review(provider, config):
    """Fail worker startup for missing scoped offline policy evidence.

    Native transports still recheck their account policy on every generation.
    AWS/Azure use native account reads, so no approval is fabricated here.
    """
    try:
        if provider == 'gcp':
            from gcp_structured import verify_operator_review
            verify_operator_review(config)
        elif provider == 'ibm':
            from policy_review import verify_policy_review
            verify_policy_review(config['policy_review'], {'accountId': config['ACCOUNT_ID'],
                'projectId': config['WATSONX_PROJECT_ID'], 'runtimeInstanceId': config['RUNTIME_INSTANCE_ID'],
                'region': config['MODEL_REGION'], 'model': config['MODEL_ID'], 'retentionReview': 'reviewed-no-prompt-retention'})
    except Exception:
        raise ValueError('Supply the current scoped ' + provider + ' model retention review before starting the worker') from None
