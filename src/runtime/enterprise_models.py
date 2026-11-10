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


def native_generator(provider, environment):
    if provider not in {'aws', 'azure', 'gcp', 'ibm'}:
        raise ValueError('Supply the owned model provider')
    env = dict(environment)
    # Reuse the same account policy, identity, regional endpoints, response bounds
    # and no-tool checks already implemented for generated structured operations.
    if provider == 'aws':
        from aws_json_model import BedrockJsonModel, read_model_config
        model = BedrockJsonModel(read_model_config(env))
    elif provider == 'azure':
        from azure_structured import AzureModel, read_model_config
        model = AzureModel(read_model_config(env))
    elif provider == 'gcp':
        from gcp_structured import VertexModel, read_model_config
        model = VertexModel(read_model_config(env))
    else:
        from ibm_structured import WatsonModel, read_model_config
        # Workspace account IDs are not IBM cloud account IDs.
        model = WatsonModel(read_model_config({**env, 'ACCOUNT_ID': env['IBM_ACCOUNT_ID']}))

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
