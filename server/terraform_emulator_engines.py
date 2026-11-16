"""AtMem-built AWS service engines for the Terraform apply emulator.

Moto is the open-source base. Where it has no implementation for an API the
Terraform AWS provider needs, the engine for that API lives here: stateful,
speaking the service's real wire protocol and error codes, and reported by name
in every emulation report so it is always clear which component answered.

An engine sees a request before Moto. It returns `None` to pass it on.
"""
import datetime
import json
import random
import re
import string
import urllib.parse
import xml.etree.ElementTree as ElementTree
from xml.sax.saxutils import escape

CLOUDFRONT_NS = 'http://cloudfront.amazonaws.com/doc/2020-05-31/'


class Reply:
    def __init__(self, operation, status=200, body=b'', content_type='text/xml', headers=()):
        self.operation, self.status, self.body, self.content_type, self.headers = operation, status, body, content_type, list(headers)


def strip_namespace(element):
    for node in element.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    return element


def text(element, path, default=None):
    found = element.find(path)
    return found.text if found is not None and found.text is not None else default


# ------------------------------------------------------- CloudFront policies

def _items(tag, names):
    if not names:
        return ''
    return f'<{tag}><Quantity>{len(names)}</Quantity><Items>' + ''.join(f'<Name>{escape(name)}</Name>' for name in names) + f'</Items></{tag}>'


def _cache_policy(name, comment, minimum, maximum, default, gzip, brotli, headers=(), cookies='none', queries='none', query_names=()):
    return (f'<CachePolicyConfig><Comment>{escape(comment)}</Comment><Name>{name}</Name><DefaultTTL>{default}</DefaultTTL><MaxTTL>{maximum}</MaxTTL><MinTTL>{minimum}</MinTTL>'
            f'<ParametersInCacheKeyAndForwardedToOrigin><EnableAcceptEncodingGzip>{str(gzip).lower()}</EnableAcceptEncodingGzip><EnableAcceptEncodingBrotli>{str(brotli).lower()}</EnableAcceptEncodingBrotli>'
            f'<HeadersConfig><HeaderBehavior>{"whitelist" if headers else "none"}</HeaderBehavior>{_items("Headers", headers)}</HeadersConfig>'
            f'<CookiesConfig><CookieBehavior>{cookies}</CookieBehavior></CookiesConfig>'
            f'<QueryStringsConfig><QueryStringBehavior>{queries}</QueryStringBehavior>{_items("QueryStrings", query_names)}</QueryStringsConfig>'
            '</ParametersInCacheKeyAndForwardedToOrigin></CachePolicyConfig>')


def _origin_policy(name, comment, behavior, headers=(), cookies='none', queries='none'):
    return (f'<OriginRequestPolicyConfig><Comment>{escape(comment)}</Comment><Name>{name}</Name>'
            f'<HeadersConfig><HeaderBehavior>{behavior}</HeaderBehavior>{_items("Headers", headers)}</HeadersConfig>'
            f'<CookiesConfig><CookieBehavior>{cookies}</CookieBehavior></CookiesConfig>'
            f'<QueryStringsConfig><QueryStringBehavior>{queries}</QueryStringBehavior></QueryStringsConfig></OriginRequestPolicyConfig>')


def _list(tag, item, values):
    return f'<{tag}><Quantity>{len(values)}</Quantity><Items>' + ''.join(f'<{item}>{escape(value)}</{item}>' for value in values) + f'</Items></{tag}>'


def _response_policy(name, comment, cors=None, security=False):
    parts = [f'<ResponseHeadersPolicyConfig><Comment>{escape(comment)}</Comment><Name>{name}</Name>']
    if cors is not None:
        # AllowHeaders and AllowMethods are required by the API. Where the AWS
        # page states no value for a managed policy, the simple-request set is used.
        methods = cors or ['GET', 'HEAD']
        parts.append('<CorsConfig>' + _list('AccessControlAllowOrigins', 'Origin', ['*']) + _list('AccessControlAllowHeaders', 'Header', ['*']) + _list('AccessControlAllowMethods', 'Method', methods)
                     + '<AccessControlAllowCredentials>false</AccessControlAllowCredentials>' + (_list('AccessControlExposeHeaders', 'Header', ['*']) if cors else '') + '<OriginOverride>false</OriginOverride></CorsConfig>')
    if security:
        parts.append('<SecurityHeadersConfig><XSSProtection><Override>false</Override><Protection>true</Protection><ModeBlock>true</ModeBlock></XSSProtection>'
                     '<FrameOptions><Override>false</Override><FrameOption>SAMEORIGIN</FrameOption></FrameOptions>'
                     '<ReferrerPolicy><Override>false</Override><ReferrerPolicy>strict-origin-when-cross-origin</ReferrerPolicy></ReferrerPolicy>'
                     '<ContentTypeOptions><Override>true</Override></ContentTypeOptions>'
                     '<StrictTransportSecurity><Override>false</Override><AccessControlMaxAgeSec>31536000</AccessControlMaxAgeSec></StrictTransportSecurity></SecurityHeadersConfig>')
    return ''.join(parts) + '</ResponseHeadersPolicyConfig>'


YEAR, DAY = 31536000, 86400
ORIGIN_METHOD_HEADERS = ['Host', 'Origin', 'X-HTTP-Method-Override', 'X-HTTP-Method', 'X-Method-Override']
CLOUDFRONT_VIEWER_HEADERS = ['CloudFront-Forwarded-Proto', 'CloudFront-Is-Android-Viewer', 'CloudFront-Is-Desktop-Viewer', 'CloudFront-Is-IOS-Viewer', 'CloudFront-Is-Mobile-Viewer', 'CloudFront-Is-SmartTV-Viewer', 'CloudFront-Is-Tablet-Viewer', 'CloudFront-Viewer-Address', 'CloudFront-Viewer-ASN', 'CloudFront-Viewer-City', 'CloudFront-Viewer-Country', 'CloudFront-Viewer-Country-Name', 'CloudFront-Viewer-Country-Region', 'CloudFront-Viewer-Country-Region-Name', 'CloudFront-Viewer-Http-Version', 'CloudFront-Viewer-Latitude', 'CloudFront-Viewer-Longitude', 'CloudFront-Viewer-Metro-Code', 'CloudFront-Viewer-Postal-Code', 'CloudFront-Viewer-Time-Zone', 'CloudFront-Viewer-TLS']
PREFLIGHT_METHODS = ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
# AWS managed policies: IDs and settings from the CloudFront Developer Guide
# (using-managed-cache-policies, -origin-request-policies, -response-headers-policies), read 2026-11-17.
MANAGED = {
    'cache-policy': {
        '2e54312d-136d-493c-8eb9-b001f22f67d2': _cache_policy('Managed-Amplify', 'Policy for Amplify Origin', 2, 600, 2, True, True, ['Authorization', 'CloudFront-Viewer-Country', 'Host'], 'all', 'all'),
        '4135ea2d-6df8-44a3-9df3-4b5a84be39ad': _cache_policy('Managed-CachingDisabled', 'Policy with caching disabled', 0, 0, 0, False, False),
        '658327ea-f89d-4fab-a63d-7e88639e58f6': _cache_policy('Managed-CachingOptimized', 'Policy with caching enabled. Supports Gzip and Brotli compression.', 1, YEAR, DAY, True, True),
        'b2884449-e4de-46a7-ac36-70bc7f1ddd6d': _cache_policy('Managed-CachingOptimizedForUncompressedObjects', 'Default policy when compression is disabled', 1, YEAR, DAY, False, False),
        '08627262-05a9-4f76-9ded-b50ca2e3a84f': _cache_policy('Managed-Elemental-MediaPackage', 'Policy for Elemental MediaPackage Origin', 0, YEAR, DAY, True, False, ['Origin'], 'none', 'whitelist', ['aws.manifestfilter', 'start', 'end', 'm']),
        '83da9c7e-98b4-4e11-a168-04f0df8e2c65': _cache_policy('Managed-UseOriginCacheControlHeaders', 'Policy for origins that return Cache-Control headers. Query strings are not included in the cache key.', 0, YEAR, 0, True, True, ORIGIN_METHOD_HEADERS, 'all', 'none'),
        '4cc15a8a-d715-48a4-82b8-cc0b614638fe': _cache_policy('Managed-UseOriginCacheControlHeaders-QueryStrings', 'Policy for origins that return Cache-Control headers and serve different content based on values present in the query string.', 0, YEAR, 0, True, True, ORIGIN_METHOD_HEADERS, 'all', 'all'),
    },
    'origin-request-policy': {
        '216adef6-5c7f-47e4-b989-5492eafa07d3': _origin_policy('Managed-AllViewer', 'Policy to forward all parameters in viewer requests', 'allViewer', (), 'all', 'all'),
        '33f36d7e-f396-46d9-90e0-52428a34d9dc': _origin_policy('Managed-AllViewerAndCloudFrontHeaders-2022-06', 'Policy to forward all parameters in viewer requests and all CloudFront headers that were released on June 2022', 'allViewerAndWhitelistCloudFront', CLOUDFRONT_VIEWER_HEADERS, 'all', 'all'),
        'b689b0a8-53d0-40ab-baf2-68738e2966ac': _origin_policy('Managed-AllViewerExceptHostHeader', 'Policy to forward all parameters in viewer requests except for the Host header', 'allExcept', ['Host'], 'all', 'all'),
        '59781a5b-3903-41f3-afcb-af62929ccde1': _origin_policy('Managed-CORS-CustomOrigin', 'Policy for CORS requests to a custom origin', 'whitelist', ['Origin']),
        '88a5eaf4-2fd4-4709-b370-b4c650ea3fcf': _origin_policy('Managed-CORS-S3Origin', 'Policy for S3 origin with CORS', 'whitelist', ['Origin', 'Access-Control-Request-Headers', 'Access-Control-Request-Method']),
        '775133bc-15f2-49f9-abea-afb2e0bf67d2': _origin_policy('Managed-Elemental-MediaTailor-PersonalizedManifests', 'Policy for Elemental MediaTailor Origin', 'whitelist', ['Origin', 'Access-Control-Request-Headers', 'Access-Control-Request-Method', 'User-Agent', 'X-Forwarded-For'], 'none', 'all'),
        'bf0718e1-ba1e-49d1-88b1-f726733018ae': _origin_policy('Managed-HostHeaderOnly', 'Policy to forward only the Host header', 'whitelist', ['Host']),
        'acba4595-bd28-49b8-b9fe-13317c0390fa': _origin_policy('Managed-UserAgentRefererHeaders', 'Policy to forward user-agent and referer headers to origin', 'whitelist', ['User-Agent', 'Referer']),
    },
    'response-headers-policy': {
        'e61eb60c-9c35-4d20-a928-2b84e02af89c': _response_policy('Managed-CORS-and-SecurityHeadersPolicy', 'Allows all origins for simple CORS requests and adds security headers', [], True),
        '5cc3b908-e619-4b99-88e5-2cf7f45965bd': _response_policy('Managed-CORS-With-Preflight', 'Allows all origins for CORS requests, including preflight requests', PREFLIGHT_METHODS),
        'eaab4381-ed33-4a86-88ca-d9558dc6cd63': _response_policy('Managed-CORS-with-preflight-and-SecurityHeadersPolicy', 'Allows all origins for CORS requests, including preflight requests, and adds security headers', PREFLIGHT_METHODS, True),
        '67f7725c-6f97-4210-82d7-5512b31e9d03': _response_policy('Managed-SecurityHeadersPolicy', 'Adds a set of security headers to every response', None, True),
        '60669652-455b-4ae9-85a4-c4c02393f86c': _response_policy('Managed-SimpleCORS', 'Allows all origins for simple CORS requests', []),
    },
}

def ensure(parent, tag, default=None):
    """The child element `tag`, created with CloudFront's default when the caller omitted it."""
    child = parent.find(tag)
    if child is None:
        child = ElementTree.SubElement(parent, tag)
        if isinstance(default, str):
            child.text = default
        elif default is not None:
            for name, value in default:
                ensure(child, name, value)
    return child


EMPTY, DISABLED_LIST = [('Quantity', '0')], [('Enabled', 'false'), ('Quantity', '0')]
METHODS = [('Quantity', '2'), ('Items', [])]


def normalize_behavior(behavior):
    for tag, default in (('SmoothStreaming', 'false'), ('Compress', 'false'), ('FieldLevelEncryptionId', ''), ('LambdaFunctionAssociations', EMPTY), ('FunctionAssociations', EMPTY),
                         ('TrustedSigners', DISABLED_LIST), ('TrustedKeyGroups', DISABLED_LIST)):
        ensure(behavior, tag, default)
    allowed = behavior.find('AllowedMethods')
    if allowed is None:
        allowed = ensure(behavior, 'AllowedMethods', METHODS)
        for method in ('HEAD', 'GET'):
            ElementTree.SubElement(allowed.find('Items'), 'Method').text = method
    if allowed.find('CachedMethods') is None:
        cached = ensure(allowed, 'CachedMethods', METHODS)
        for method in ('HEAD', 'GET'):
            ElementTree.SubElement(cached.find('Items'), 'Method').text = method


def normalize_distribution(config):
    """Fill the members CloudFront adds to every stored distribution configuration.

    Values the caller sent are never changed; only absent members receive the
    service default, as documented for DistributionConfig, Origin and CacheBehavior.
    """
    for tag, default in (('Aliases', EMPTY), ('DefaultRootObject', ''), ('OriginGroups', EMPTY), ('CacheBehaviors', EMPTY), ('CustomErrorResponses', EMPTY),
                         ('Logging', [('Enabled', 'false'), ('IncludeCookies', 'false'), ('Bucket', ''), ('Prefix', '')]), ('PriceClass', 'PriceClass_All'),
                         ('ViewerCertificate', [('CloudFrontDefaultCertificate', 'true')]), ('Restrictions', [('GeoRestriction', [('RestrictionType', 'none'), ('Quantity', '0')])]),
                         ('WebACLId', ''), ('HttpVersion', 'http2'), ('IsIPV6Enabled', 'true'), ('ContinuousDeploymentPolicyId', ''), ('Staging', 'false')):
        ensure(config, tag, default)
    certificate = config.find('ViewerCertificate')
    if (certificate.findtext('CloudFrontDefaultCertificate') or '').lower() == 'true':
        ensure(certificate, 'MinimumProtocolVersion', 'TLSv1')
        ensure(certificate, 'CertificateSource', 'cloudfront')
    for origin in config.findall('Origins/Items/Origin'):
        for tag, default in (('OriginPath', ''), ('CustomHeaders', EMPTY), ('ConnectionAttempts', '3'), ('ConnectionTimeout', '10'), ('OriginShield', [('Enabled', 'false')]), ('OriginAccessControlId', '')):
            ensure(origin, tag, default)
        custom = origin.find('CustomOriginConfig')
        if custom is not None:
            for tag, default in (('OriginReadTimeout', '30'), ('OriginKeepaliveTimeout', '5')):
                ensure(custom, tag, default)
        elif origin.find('S3OriginConfig') is None and origin.find('VpcOriginConfig') is None:
            ensure(origin, 'S3OriginConfig', [('OriginAccessIdentity', '')])
    for behavior in [config.find('DefaultCacheBehavior'), *config.findall('CacheBehaviors/Items/CacheBehavior')]:
        normalize_behavior(behavior)
    return config


POLICY_KINDS = {
    'cache-policy': {'root': 'CachePolicy', 'label': 'cache policy', 'reference': 'CachePolicyId', 'required': ['Name', 'MinTTL']},
    'origin-request-policy': {'root': 'OriginRequestPolicy', 'label': 'origin request policy', 'reference': 'OriginRequestPolicyId', 'required': ['Name', 'HeadersConfig', 'CookiesConfig', 'QueryStringsConfig']},
    'response-headers-policy': {'root': 'ResponseHeadersPolicy', 'label': 'response headers policy', 'reference': 'ResponseHeadersPolicyId', 'required': ['Name']},
}


class CloudFrontEngine:
    """Distributions with their tags, and cache, origin request and response headers
    policies including the AWS managed catalog.

    A policy's configuration is validated for its required members, stored and
    returned exactly as the caller sent it. Versions follow CloudFront's
    optimistic locking: every write returns a new ETag and updates or deletes
    must present the current one.
    """
    name = 'atmem-cloudfront'
    service = 'cloudfront'
    reference = 'https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_Operations.html'
    operations = [verb + POLICY_KINDS[kind]['root'] + suffix for kind in POLICY_KINDS for verb, suffix in (('Create', ''), ('Get', ''), ('Get', 'Config'), ('Update', ''), ('Delete', ''))] + ['ListCachePolicies', 'ListOriginRequestPolicies', 'ListResponseHeadersPolicies', 'CreateDistribution', 'CreateDistributionWithTags', 'GetDistribution', 'GetDistributionConfig', 'UpdateDistribution', 'DeleteDistribution', 'ListDistributions', 'ListTagsForResource', 'TagResource', 'UntagResource']
    PATH = re.compile(r'/2020-05-31/(cache-policy|origin-request-policy|response-headers-policy)(?:/([^/]+)(/config)?)?')

    def __init__(self, account='123456789012'):
        self.account = account
        self.distributions_store = {}
        self.policies = {kind: {} for kind in POLICY_KINDS}
        epoch = datetime.datetime(2020, 7, 22, tzinfo=datetime.timezone.utc)
        for kind, catalog in MANAGED.items():
            for identity, config in catalog.items():
                self.policies[kind][identity] = {'config': ElementTree.fromstring(config), 'etag': 'E23ZP02F085DFQ', 'modified': epoch, 'managed': True}

    # -- helpers
    @staticmethod
    def error(operation, status, code, message):
        body = f'<?xml version="1.0"?>\n<ErrorResponse xmlns="{CLOUDFRONT_NS}"><Error><Type>Sender</Type><Code>{code}</Code><Message>{escape(message)}</Message></Error><RequestId>atmem-engine</RequestId></ErrorResponse>'
        return Reply(operation, status, body.encode())

    @staticmethod
    def token(length, alphabet=string.ascii_uppercase + string.digits):
        return ''.join(random.choices(alphabet, k=length))

    def document(self, kind, identity, config_only=False):
        policy, root = self.policies[kind][identity], POLICY_KINDS[kind]['root']
        config = ElementTree.tostring(policy['config'], encoding='unicode')
        if config_only:
            return config.replace(f'<{root}Config>', f'<{root}Config xmlns="{CLOUDFRONT_NS}">', 1)
        modified = policy['modified'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        return f'<{root}><Id>{identity}</Id><LastModifiedTime>{modified}</LastModifiedTime>{config}</{root}>'

    def reply(self, operation, kind, identity, status=200, config_only=False):
        body = self.document(kind, identity, config_only)
        if not config_only:
            root = POLICY_KINDS[kind]['root']
            body = body.replace(f'<{root}>', f'<{root} xmlns="{CLOUDFRONT_NS}">', 1)
        headers = [('ETag', self.policies[kind][identity]['etag'])]
        if status == 201:
            headers.append(('Location', f'https://cloudfront.amazonaws.com/2020-05-31/{kind}/{identity}'))
        return Reply(operation, status, ('<?xml version="1.0"?>\n' + body).encode(), headers=headers)

    def parse(self, kind, body):
        root = POLICY_KINDS[kind]['root']
        try:
            config = strip_namespace(ElementTree.fromstring(body))
        except ElementTree.ParseError as error:
            return None, f'The request body is not well-formed XML: {error}'
        if config.tag != root + 'Config':
            return None, f'Expected a {root}Config document.'
        missing = [member for member in POLICY_KINDS[kind]['required'] if config.find(member) is None or (member == 'Name' and not (config.findtext('Name') or '').strip())]
        if missing:
            return None, 'Missing required member: ' + ', '.join(missing)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', config.findtext('Name')):
            return None, 'The policy name may contain only letters, digits, hyphens and underscores (1-128).'
        return config, None

    def referenced(self, kind):
        """Policy IDs referenced by any cache behavior of a stored distribution."""
        tag = POLICY_KINDS[kind]['reference']
        return {node.text for item in self.distributions_store.values() for node in item['config'].iter(tag) if node.text}

    def inventory(self):
        return [f'cloudfront:{kind}/{identity}' for kind, policies in self.policies.items() for identity, policy in policies.items() if not policy['managed']] + [f'cloudfront:distribution/{identity}' for identity in self.distributions_store]

    # -- requests
    def handle(self, method, path, query, headers, body):
        answered = self.handle_distribution(method, path, query, headers, body)
        if answered is not None:
            return answered
        match = self.PATH.fullmatch(path)
        if not match:
            return None
        kind, identity, config_only = match[1], match[2], bool(match[3])
        root, label, store = POLICY_KINDS[kind]['root'], POLICY_KINDS[kind]['label'], self.policies[kind]
        plural = {'cache-policy': 'CachePolicies', 'origin-request-policy': 'OriginRequestPolicies', 'response-headers-policy': 'ResponseHeadersPolicies'}[kind]
        if identity is None:
            if method == 'GET':
                return self.list(kind, plural, query)
            if method != 'POST':
                return None
            operation = 'Create' + root
            config, problem = self.parse(kind, body)
            if problem:
                return self.error(operation, 400, 'InvalidArgument', problem)
            if any(policy['config'].findtext('Name') == config.findtext('Name') for policy in store.values()):
                return self.error(operation, 409, root + 'AlreadyExists', f'A {label} with this name already exists.')
            identity = '-'.join(self.token(size, '0123456789abcdef') for size in (8, 4, 4, 4, 12))
            store[identity] = {'config': config, 'etag': 'E' + self.token(13), 'modified': datetime.datetime.now(datetime.timezone.utc), 'managed': False}
            return self.reply(operation, kind, identity, 201)
        operation = {'GET': 'Get' + root + ('Config' if config_only else ''), 'PUT': 'Update' + root, 'DELETE': 'Delete' + root}.get(method)
        if operation is None or (config_only and method != 'GET'):
            return None
        policy = store.get(identity)
        if policy is None:
            return self.error(operation, 404, 'NoSuch' + root, f'The {label} does not exist.')
        if method == 'GET':
            return self.reply(operation, kind, identity, config_only=config_only)
        if policy['managed']:
            return self.error(operation, 400, 'IllegalUpdate' if method == 'PUT' else 'IllegalDelete', f'An AWS managed {label} cannot be changed or deleted.')
        presented = headers.get('If-Match')
        if not presented:
            return self.error(operation, 400, 'InvalidIfMatchVersion', 'The If-Match version is missing or not valid for the resource.')
        if presented != policy['etag']:
            return self.error(operation, 412, 'PreconditionFailed', 'The precondition in one or more of the request fields evaluated to false.')
        if method == 'DELETE':
            if identity in self.referenced(kind):
                return self.error(operation, 409, root + 'InUse', f'Cannot delete the {label} because it is attached to one or more cache behaviors.')
            del store[identity]
            return Reply(operation, 204)
        config, problem = self.parse(kind, body)
        if problem:
            return self.error(operation, 400, 'InvalidArgument', problem)
        if any(other is not policy and other['config'].findtext('Name') == config.findtext('Name') for other in store.values()):
            return self.error(operation, 409, root + 'AlreadyExists', f'A {label} with this name already exists.')
        policy.update(config=config, etag='E' + self.token(13), modified=datetime.datetime.now(datetime.timezone.utc))
        return self.reply(operation, kind, identity)

    def list(self, kind, plural, query):
        root, operation = POLICY_KINDS[kind]['root'], 'List' + plural
        wanted = (query.get('Type') or [None])[0]
        if wanted not in (None, 'managed', 'custom'):
            return self.error(operation, 400, 'InvalidArgument', 'Type must be managed or custom.')
        try:
            limit = int((query.get('MaxItems') or ['100'])[0])
        except ValueError:
            return self.error(operation, 400, 'InvalidArgument', 'MaxItems must be a number.')
        ordered = sorted((identity for identity, policy in self.policies[kind].items() if wanted is None or policy['managed'] == (wanted == 'managed')))
        marker = (query.get('Marker') or [None])[0]
        if marker:
            ordered = [identity for identity in ordered if identity > marker]
        page, more = ordered[:limit], len(ordered) > limit
        items = ''.join(f'<{root}Summary><Type>{"managed" if self.policies[kind][identity]["managed"] else "custom"}</Type>{self.document(kind, identity)}</{root}Summary>' for identity in page)
        body = (f'<?xml version="1.0"?>\n<{root}List xmlns="{CLOUDFRONT_NS}">' + (f'<NextMarker>{page[-1]}</NextMarker>' if more and page else '') + f'<MaxItems>{limit}</MaxItems><Quantity>{len(page)}</Quantity>'
                + (f'<Items>{items}</Items>' if page else '') + f'</{root}List>')
        return Reply(operation, 200, body.encode())

    # -- distributions
    DISTRIBUTION = re.compile(r'/2020-05-31/distribution(?:/([^/]+)(/config)?)?')

    def distribution_document(self, identity):
        item = self.distributions_store[identity]
        modified = item['modified'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        return (f'<Distribution xmlns="{CLOUDFRONT_NS}"><Id>{identity}</Id><ARN>{item["arn"]}</ARN><Status>Deployed</Status><LastModifiedTime>{modified}</LastModifiedTime>'
                f'<InProgressInvalidationBatches>0</InProgressInvalidationBatches><DomainName>{item["domain"]}</DomainName>'
                '<ActiveTrustedSigners><Enabled>false</Enabled><Quantity>0</Quantity></ActiveTrustedSigners><ActiveTrustedKeyGroups><Enabled>false</Enabled><Quantity>0</Quantity></ActiveTrustedKeyGroups>'
                + ElementTree.tostring(item['config'], encoding='unicode') + '</Distribution>')

    def distribution_reply(self, operation, identity, status=200, config_only=False):
        item = self.distributions_store[identity]
        body = ElementTree.tostring(item['config'], encoding='unicode').replace('<DistributionConfig>', f'<DistributionConfig xmlns="{CLOUDFRONT_NS}">', 1) if config_only else self.distribution_document(identity)
        headers = [('ETag', item['etag'])] + ([('Location', f'https://cloudfront.amazonaws.com/2020-05-31/distribution/{identity}')] if status == 201 else [])
        return Reply(operation, status, ('<?xml version="1.0"?>\n' + body).encode(), headers=headers)

    def parse_distribution(self, operation, config):
        """CloudFront's own request validation for the members a distribution cannot exist without."""
        if config is None or config.tag != 'DistributionConfig':
            return self.error(operation, 400, 'MalformedInput', 'Expected a DistributionConfig document.')
        for member in ('CallerReference', 'Origins', 'DefaultCacheBehavior', 'Comment', 'Enabled'):
            if config.find(member) is None:
                return self.error(operation, 400, 'MissingBody' if member == 'Origins' else 'InvalidArgument', f'The parameter {member} is required.')
        origins = [origin.findtext('Id') for origin in config.findall('Origins/Items/Origin')]
        if not origins:
            return self.error(operation, 400, 'InvalidArgument', 'A distribution needs at least one origin.')
        if len(set(origins)) != len(origins):
            return self.error(operation, 400, 'InvalidArgument', 'Origin IDs must be unique within a distribution.')
        behaviors = [config.find('DefaultCacheBehavior'), *config.findall('CacheBehaviors/Items/CacheBehavior')]
        for behavior in behaviors:
            if behavior.findtext('TargetOriginId') not in origins:
                return self.error(operation, 404, 'NoSuchOrigin', 'One or more of your origins or origin groups do not exist.')
            if behavior.find('ViewerProtocolPolicy') is None:
                return self.error(operation, 400, 'InvalidArgument', 'The parameter ViewerProtocolPolicy is required.')
            if not behavior.findtext('CachePolicyId') and behavior.find('ForwardedValues') is None:
                return self.error(operation, 400, 'InvalidArgument', 'A cache behavior needs either a CachePolicyId or ForwardedValues.')
        return self.check_distribution(ElementTree.tostring(config), operation)

    def handle_distribution(self, method, path, query, headers, body):
        if path == '/2020-05-31/tagging':
            return self.handle_tags(method, query, body)
        match = self.DISTRIBUTION.fullmatch(path)
        if not match:
            return None
        identity, config_only, store = match[1], bool(match[2]), self.distributions_store
        if identity is None:
            if method == 'GET':
                return self.list_distributions(query)
            if method != 'POST':
                return None
            with_tags = 'WithTags' in query
            operation = 'CreateDistributionWithTags' if with_tags else 'CreateDistribution'
            try:
                document = strip_namespace(ElementTree.fromstring(body))
            except ElementTree.ParseError as error:
                return self.error(operation, 400, 'MalformedXML', f'The request body is not well-formed XML: {error}')
            config = document.find('DistributionConfig') if document.tag == 'DistributionConfigWithTags' else document
            problem = self.parse_distribution(operation, config)
            if problem:
                return problem
            reference = config.findtext('CallerReference')
            if any(item['config'].findtext('CallerReference') == reference for item in store.values()):
                return self.error(operation, 409, 'DistributionAlreadyExists', 'The caller reference you attempted to create the distribution with is associated with another distribution.')
            identity = 'E' + self.token(13)
            tags = {tag.findtext('Key'): tag.findtext('Value') or '' for tag in document.findall('Tags/Items/Tag')} if document.tag == 'DistributionConfigWithTags' else {}
            store[identity] = {'config': normalize_distribution(config), 'etag': 'E' + self.token(13), 'modified': datetime.datetime.now(datetime.timezone.utc), 'tags': tags,
                               'arn': f'arn:aws:cloudfront::{self.account}:distribution/{identity}', 'domain': 'd' + self.token(13, string.ascii_lowercase + string.digits) + '.cloudfront.net'}
            return self.distribution_reply(operation, identity, 201)
        operation = {('GET', False): 'GetDistribution', ('GET', True): 'GetDistributionConfig', ('PUT', True): 'UpdateDistribution', ('DELETE', False): 'DeleteDistribution'}.get((method, config_only))
        if operation is None:
            return None
        item = store.get(identity)
        if item is None:
            return self.error(operation, 404, 'NoSuchDistribution', 'The specified distribution does not exist.')
        if method == 'GET':
            return self.distribution_reply(operation, identity, config_only=config_only)
        presented = headers.get('If-Match')
        if not presented:
            return self.error(operation, 400, 'InvalidIfMatchVersion', 'The If-Match version is missing or not valid for the resource.')
        if presented != item['etag']:
            return self.error(operation, 412, 'PreconditionFailed', 'The precondition in one or more of the request fields evaluated to false.')
        if method == 'DELETE':
            if (item['config'].findtext('Enabled') or '').lower() == 'true':
                return self.error(operation, 409, 'DistributionNotDisabled', 'The distribution you are trying to delete has not been disabled.')
            del store[identity]
            return Reply(operation, 204)
        try:
            config = strip_namespace(ElementTree.fromstring(body))
        except ElementTree.ParseError as error:
            return self.error(operation, 400, 'MalformedXML', f'The request body is not well-formed XML: {error}')
        problem = self.parse_distribution(operation, config)
        if problem:
            return problem
        if config.findtext('CallerReference') != item['config'].findtext('CallerReference'):
            return self.error(operation, 400, 'IllegalUpdate', 'The CallerReference of a distribution cannot be changed.')
        item.update(config=normalize_distribution(config), etag='E' + self.token(13), modified=datetime.datetime.now(datetime.timezone.utc))
        return self.distribution_reply(operation, identity)

    def list_distributions(self, query):
        summaries = []
        for identity in sorted(self.distributions_store):
            item, config = self.distributions_store[identity], self.distributions_store[identity]['config']
            copied = ''.join(ElementTree.tostring(config.find(member), encoding='unicode') for member in ('Aliases', 'Origins', 'OriginGroups', 'DefaultCacheBehavior', 'CacheBehaviors', 'CustomErrorResponses', 'Comment', 'PriceClass', 'Enabled', 'ViewerCertificate', 'Restrictions', 'WebACLId', 'HttpVersion', 'IsIPV6Enabled') if config.find(member) is not None)
            modified = item['modified'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            summaries.append(f'<DistributionSummary><Id>{identity}</Id><ARN>{item["arn"]}</ARN><Status>Deployed</Status><LastModifiedTime>{modified}</LastModifiedTime><DomainName>{item["domain"]}</DomainName>{copied}<Staging>false</Staging></DistributionSummary>')
        body = (f'<?xml version="1.0"?>\n<DistributionList xmlns="{CLOUDFRONT_NS}"><Marker></Marker><MaxItems>100</MaxItems><IsTruncated>false</IsTruncated><Quantity>{len(summaries)}</Quantity>'
                + (f'<Items>{"".join(summaries)}</Items>' if summaries else '') + '</DistributionList>')
        return Reply('ListDistributions', 200, body.encode())

    def handle_tags(self, method, query, body):
        """Tags of distributions this engine owns; other resources stay with the base emulator."""
        arn = (query.get('Resource') or [''])[0]
        item = next((item for item in self.distributions_store.values() if item['arn'] == arn), None)
        if item is None:
            return None
        if method == 'GET':
            tags = ''.join(f'<Tag><Key>{escape(key)}</Key><Value>{escape(value)}</Value></Tag>' for key, value in item['tags'].items())
            return Reply('ListTagsForResource', 200, f'<?xml version="1.0"?>\n<Tags xmlns="{CLOUDFRONT_NS}"><Items>{tags}</Items></Tags>'.encode())
        operation = (query.get('Operation') or [''])[0]
        document = strip_namespace(ElementTree.fromstring(body))
        if operation == 'Tag':
            item['tags'].update({tag.findtext('Key'): tag.findtext('Value') or '' for tag in document.iter('Tag')})
            return Reply('TagResource', 204)
        if operation == 'Untag':
            for key in document.iter('Key'):
                item['tags'].pop(key.text, None)
            return Reply('UntagResource', 204)
        return None

    def check_distribution(self, body, operation='CreateDistribution'):
        """CloudFront rejects a distribution that references a policy that does not exist."""
        document = body.decode('utf-8', 'replace')
        for kind, details in POLICY_KINDS.items():
            for identity in re.findall(rf'<{details["reference"]}>([^<]+)</{details["reference"]}>', document):
                if identity not in self.policies[kind]:
                    return self.error(operation, 404, 'NoSuch' + details['root'], f'The {details["label"]} does not exist.')
        return None


# -------------------------------------------------------- Step Functions ASL

STATE_TYPES = {'Task', 'Pass', 'Choice', 'Wait', 'Succeed', 'Fail', 'Parallel', 'Map'}


def validate_state_machine(definition, path='', diagnostics=None):
    """Structural validation of an Amazon States Language definition.

    Covers JSON syntax, StartAt, state types, transition targets, terminal
    states, Choice rules and nested Parallel/Map machines. It does not evaluate
    JSONPath/JSONata expressions or resource ARNs.
    """
    diagnostics = [] if diagnostics is None else diagnostics

    def report(code, message, location):
        diagnostics.append({'severity': 'ERROR', 'code': code, 'message': message, 'location': location})
    states = definition.get('States') if isinstance(definition, dict) else None
    if not isinstance(states, dict) or not states:
        report('MISSING_STATES', 'A state machine needs a non-empty States object.', path + '/States')
        return diagnostics
    start = definition.get('StartAt')
    if not isinstance(start, str):
        report('MISSING_START_AT', 'A state machine needs a StartAt string.', path + '/StartAt')
    elif start not in states:
        report('MISSING_TRANSITION_TARGET', f'StartAt refers to the undefined state {start}.', path + '/StartAt')
    for name, state in states.items():
        here = f'{path}/States/{name}'
        kind = state.get('Type') if isinstance(state, dict) else None
        if kind not in STATE_TYPES:
            report('INVALID_STATE_TYPE', f'State {name} has a missing or unknown Type.', here + '/Type')
            continue
        targets = [(here + '/Next', state['Next'])] if 'Next' in state else []
        for index, catcher in enumerate(state.get('Catch') or []):
            targets.append((f'{here}/Catch/{index}/Next', catcher.get('Next') if isinstance(catcher, dict) else None))
        if kind == 'Choice':
            choices = state.get('Choices')
            if not isinstance(choices, list) or not choices:
                report('MISSING_CHOICES', f'Choice state {name} needs a non-empty Choices array.', here + '/Choices')
            for index, rule in enumerate(choices if isinstance(choices, list) else []):
                targets.append((f'{here}/Choices/{index}/Next', rule.get('Next') if isinstance(rule, dict) else None))
            if 'Default' in state:
                targets.append((here + '/Default', state['Default']))
            if 'End' in state or 'Next' in state:
                report('INVALID_TRANSITION', f'Choice state {name} cannot have Next or End.', here)
        elif kind in ('Succeed', 'Fail'):
            if 'Next' in state or 'End' in state:
                report('INVALID_TRANSITION', f'Terminal state {name} cannot have Next or End.', here)
        elif ('Next' in state) == (state.get('End') is True):
            report('MISSING_TRANSITION', f'State {name} needs exactly one of Next or "End": true.', here)
        if kind == 'Task' and not isinstance(state.get('Resource'), str):
            report('MISSING_RESOURCE', f'Task state {name} needs a Resource.', here + '/Resource')
        if kind == 'Wait' and sum(key in state for key in ('Seconds', 'Timestamp', 'SecondsPath', 'TimestampPath')) != 1:
            report('INVALID_WAIT', f'Wait state {name} needs exactly one of Seconds, Timestamp, SecondsPath or TimestampPath.', here)
        for location, target in targets:
            if not isinstance(target, str) or target not in states:
                report('MISSING_TRANSITION_TARGET', f'State {name} transitions to the undefined state {target}.', location)
        if kind == 'Parallel':
            branches = state.get('Branches')
            if not isinstance(branches, list) or not branches:
                report('MISSING_BRANCHES', f'Parallel state {name} needs a non-empty Branches array.', here + '/Branches')
            for index, branch in enumerate(branches if isinstance(branches, list) else []):
                validate_state_machine(branch, f'{here}/Branches/{index}', diagnostics)
        if kind == 'Map':
            processor = state.get('ItemProcessor', state.get('Iterator'))
            if not isinstance(processor, dict):
                report('MISSING_ITEM_PROCESSOR', f'Map state {name} needs an ItemProcessor.', here + '/ItemProcessor')
            else:
                validate_state_machine(processor, here + '/ItemProcessor', diagnostics)
    return diagnostics


class JsonEngine:
    """Base for engines on awsJson services, selected by X-Amz-Target."""
    targets = {}

    def handle(self, method, path, query, headers, body):
        target = headers.get('X-Amz-Target', '')
        handler = self.targets.get(target)
        if method != 'POST' or handler is None:
            return None
        operation = target.rsplit('.', 1)[-1]
        try:
            request = json.loads(body or b'{}')
        except ValueError:
            return self.error(operation, 'SerializationException', 'The request body is not valid JSON.')
        if not isinstance(request, dict):
            return self.error(operation, 'SerializationException', 'The request body must be an object.')
        return getattr(self, handler)(operation, request, headers)

    @staticmethod
    def ok(operation, payload):
        return Reply(operation, 200, json.dumps(payload).encode(), 'application/x-amz-json-1.0')

    @staticmethod
    def error(operation, code, message, status=400):
        return Reply(operation, status, json.dumps({'__type': code, 'message': message}).encode(), 'application/x-amz-json-1.0', [('x-amzn-ErrorType', code)])

    def inventory(self):
        return []


class StepFunctionsValidationEngine(JsonEngine):
    """ValidateStateMachineDefinition, which the provider calls while planning."""
    name = 'atmem-stepfunctions-validation'
    service = 'states'
    reference = 'https://docs.aws.amazon.com/step-functions/latest/apireference/API_ValidateStateMachineDefinition.html'
    operations = ['ValidateStateMachineDefinition', 'ListStateMachineVersions']
    targets = {'AWSStepFunctions.ValidateStateMachineDefinition': 'validate', 'AWSStepFunctions.ListStateMachineVersions': 'versions'}

    def __init__(self, machines=lambda region: []):
        self.machines = machines  # region -> state machine ARNs held by the base emulator

    def versions(self, operation, request, headers):
        """No version exists until one is published; publishing is not implemented here."""
        arn = request.get('stateMachineArn')
        if not isinstance(arn, str) or not re.fullmatch(r'arn:aws[\w-]*:states:[\w-]+:\d{12}:stateMachine:[\w.-]+', arn):
            return self.error(operation, 'InvalidArn', f"Invalid Arn: '{arn}'")
        if arn not in self.machines(arn.split(':')[3]):
            return self.error(operation, 'StateMachineDoesNotExist', f"State Machine Does Not Exist: '{arn}'")
        return self.ok(operation, {'stateMachineVersions': []})

    def validate(self, operation, request, headers):
        if not isinstance(request.get('definition'), str):
            return self.error(operation, 'ValidationException', 'definition is required.')
        try:
            definition = json.loads(request['definition'])
        except ValueError as error:
            diagnostics = [{'severity': 'ERROR', 'code': 'INVALID_JSON_DESCRIPTION', 'message': f'Invalid JSON: {error}', 'location': '/'}]
        else:
            diagnostics = validate_state_machine(definition)
        limit = request.get('maxResults') or 100
        return self.ok(operation, {'result': 'FAIL' if diagnostics else 'OK', 'diagnostics': diagnostics[:limit], 'truncated': len(diagnostics) > limit})


class CognitoResourceServerEngine(JsonEngine):
    """DeleteResourceServer on the base emulator's own user-pool state."""
    name = 'atmem-cognito-resource-servers'
    service = 'cognito-idp'
    reference = 'https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_DeleteResourceServer.html'
    operations = ['DeleteResourceServer']
    targets = {'AWSCognitoIdentityProviderService.DeleteResourceServer': 'delete'}

    def __init__(self, pools):
        self.pools = pools  # region -> {pool id: user pool}

    def delete(self, operation, request, headers):
        pool_id, identifier = request.get('UserPoolId'), request.get('Identifier')
        if not isinstance(pool_id, str) or not isinstance(identifier, str):
            return self.error(operation, 'InvalidParameterException', 'UserPoolId and Identifier are required.')
        region = pool_id.split('_', 1)[0]
        pool = self.pools(region).get(pool_id)
        if pool is None:
            return self.error(operation, 'ResourceNotFoundException', f'User pool {pool_id} does not exist.')
        if identifier not in pool.resource_servers:
            return self.error(operation, 'ResourceNotFoundException', f'Resource server {identifier} does not exist.')
        del pool.resource_servers[identifier]
        return Reply(operation, 200, b'{}', 'application/x-amz-json-1.1')


def dispatch(engines, service, environ, path, body):
    """First engine of the request's service that answers, as (engine, Reply)."""
    candidates = [engine for engine in engines if engine.service == service]
    if not candidates:
        return None
    headers = {key[5:].replace('_', '-').title(): value for key, value in environ.items() if key.startswith('HTTP_')}
    headers = {**headers, **{name: headers[name.title()] for name in ('X-Amz-Target', 'If-Match', 'ETag') if name.title() in headers}}
    query = urllib.parse.parse_qs(environ.get('QUERY_STRING', ''))
    for engine in candidates:
        reply = engine.handle(environ.get('REQUEST_METHOD', ''), path, query, headers, body)
        if reply is not None:
            return engine, reply
    return None


class AppRunnerEngine(JsonEngine):
    """Stateful image-service control plane; no image pull or application execution."""
    name = 'atmem-apprunner'
    service = 'apprunner'
    reference = 'https://docs.aws.amazon.com/apprunner/latest/api/API_CreateService.html'
    operations = ['CreateService', 'DescribeService', 'UpdateService', 'DeleteService', 'ListServices', 'ListOperations', 'ListTagsForResource', 'TagResource', 'UntagResource']
    targets = {'AppRunner.' + op: 'operate' for op in operations}

    def __init__(self, account='123456789012'):
        self.account, self.services, self.tags, self.history = account, {}, {}, {}

    def inventory(self):
        return [f'apprunner:{arn}' for arn in self.services]

    def operate(self, operation, request, headers):
        import copy
        import uuid
        scope = re.search(r'Credential=[^/]+/[^/]+/([^/]+)/', headers.get('Authorization', ''))
        region = scope[1] if scope else 'us-east-1'
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if operation == 'ListServices':
            services = [s for s in self.services.values() if s['ServiceArn'].split(':')[3] == region]
            return self.ok(operation, {'ServiceSummaryList': [{k: s[k] for k in ('ServiceArn','ServiceId','ServiceName','ServiceUrl','CreatedAt','UpdatedAt','Status')} for s in services]})
        if operation == 'CreateService':
            if any(k not in {'ServiceName','SourceConfiguration','InstanceConfiguration','HealthCheckConfiguration','NetworkConfiguration','ObservabilityConfiguration','Tags','AutoScalingConfigurationArn','EncryptionConfiguration'} for k in request):
                return self.error(operation,'EmulatorNotImplemented','This create member has not been qualified.')
            name, source = request.get('ServiceName'), request.get('SourceConfiguration')
            if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{3,39}',name):
                return self.error(operation,'InvalidRequestException','Invalid service name.')
            if not isinstance(source,dict) or ('ImageRepository' in source) == ('CodeRepository' in source):
                return self.error(operation,'InvalidRequestException','Specify exactly one image or code repository.')
            if 'CodeRepository' in source or request.get('AutoScalingConfigurationArn') or request.get('EncryptionConfiguration'):
                return self.error(operation,'EmulatorNotImplemented','Code repositories, custom autoscaling and encryption need further qualification.')
            image = source['ImageRepository']
            if not image.get('ImageIdentifier') or image.get('ImageRepositoryType') not in ('ECR','ECR_PUBLIC'):
                return self.error(operation,'InvalidRequestException','A valid image identifier and repository type are required.')
            if any(s['ServiceName']==name and s['ServiceArn'].split(':')[3]==region for s in self.services.values()):
                return self.error(operation,'InvalidRequestException','Service name already exists.')
            identifier = uuid.uuid4().hex
            arn=f'arn:aws:apprunner:{region}:{self.account}:service/{name}/{identifier}'
            source=copy.deepcopy(source)
            source.setdefault('AutoDeploymentsEnabled',image['ImageRepositoryType']!='ECR_PUBLIC')
            source['ImageRepository'].setdefault('ImageConfiguration',{}).setdefault('Port','8080')
            service={'ServiceArn':arn,'ServiceId':identifier,'ServiceName':name,'ServiceUrl':f'{identifier}.{region}.awsapprunner.com',
                     'CreatedAt':now,'UpdatedAt':now,'Status':'RUNNING','SourceConfiguration':source,
                     'InstanceConfiguration':{'Cpu':'1024','Memory':'2048',**request.get('InstanceConfiguration',{})},
                     'HealthCheckConfiguration':{'Protocol':'TCP','Path':'/','Interval':5,'Timeout':2,'HealthyThreshold':1,'UnhealthyThreshold':5,**request.get('HealthCheckConfiguration',{})},
                     'NetworkConfiguration':{'EgressConfiguration':{'EgressType':'DEFAULT'},'IngressConfiguration':{'IsPubliclyAccessible':True},'IpAddressType':'IPV4',**request.get('NetworkConfiguration',{})},
                     'AutoScalingConfigurationSummary':{'AutoScalingConfigurationArn':f'arn:aws:apprunner:{region}:{self.account}:autoscalingconfiguration/DefaultConfiguration/1/00000000000000000000000000000001','AutoScalingConfigurationName':'DefaultConfiguration','AutoScalingConfigurationRevision':1}}
            if 'ObservabilityConfiguration' in request:
                service['ObservabilityConfiguration']=copy.deepcopy(request['ObservabilityConfiguration'])
            self.services[arn]=service; self.tags[arn]={t['Key']:t.get('Value','') for t in request.get('Tags',[])};self.history[arn]=[]
        else:
            arn=request.get('ServiceArn') or request.get('ResourceArn')
            service=self.services.get(arn)
            if not service or service['ServiceArn'].split(':')[3] != region:
                return self.error(operation,'ResourceNotFoundException','Service does not exist.')
            if operation=='DescribeService':return self.ok(operation,{'Service':copy.deepcopy(service)})
            if operation=='ListOperations':return self.ok(operation,{'OperationSummaryList':copy.deepcopy(self.history[arn])})
            if operation=='ListTagsForResource':return self.ok(operation,{'Tags':[{'Key':k,'Value':v} for k,v in self.tags[arn].items()]})
            if operation=='TagResource':
                self.tags[arn].update({t['Key']:t.get('Value','') for t in request.get('Tags',[])})
                return self.ok(operation,{})
            if operation=='UntagResource':
                for key in request.get('TagKeys',[]):self.tags[arn].pop(key,None)
                return self.ok(operation,{})
            if operation=='UpdateService':
                if any(k not in {'ServiceArn','SourceConfiguration','InstanceConfiguration','HealthCheckConfiguration','NetworkConfiguration','ObservabilityConfiguration'} for k in request):
                    return self.error(operation,'EmulatorNotImplemented','This update member has not been qualified.')
                if request.get('SourceConfiguration',{}).get('CodeRepository'):
                    return self.error(operation,'EmulatorNotImplemented','Code repositories are not implemented.')
                for key,value in request.items():
                    if key!='ServiceArn':service[key]={**service.get(key,{}),**copy.deepcopy(value)}
                service['UpdatedAt']=now
            elif operation=='DeleteService':
                service=copy.deepcopy(service);service.update(Status='DELETED',DeletedAt=now)
                del self.services[arn];self.tags.pop(arn,None)
        op_id=uuid.uuid4().hex
        self.history[arn].append({'Id':op_id,'Type':{'CreateService':'CREATE_SERVICE','UpdateService':'UPDATE_SERVICE','DeleteService':'DELETE_SERVICE'}[operation],'Status':'SUCCEEDED','StartedAt':now,'EndedAt':now,'UpdatedAt':now})
        return self.ok(operation,{'Service':copy.deepcopy(service),'OperationId':op_id})


class ServerlessLifecycleEngine(JsonEngine):
    """Missing Serverless lifecycle operations against the base's shared state."""
    name='atmem-opensearch-serverless-lifecycle'
    service='aoss'
    reference='https://docs.aws.amazon.com/opensearch-service/latest/ServerlessAPIReference/API_DeleteSecurityPolicy.html'
    operations=['CreateCollection','DeleteSecurityPolicy']
    targets={'OpenSearchServerless.'+op:'operate' for op in operations}

    def __init__(self, backends):
        self.backends=backends
        self.regions=set()
        self.tokens={}

    def inventory(self):
        found=[]
        for region in self.regions:
            backend=self.backends(region)
            found.extend(f'aoss:{region}:collection:{c.id}' for c in backend.collections.values())
            found.extend(f'aoss:{region}:policy:{p.type}:{p.name}' for p in backend.security_policies.values())
        return found

    def operate(self,operation,request,headers):
        import fnmatch
        from moto.opensearchserverless.models import Collection
        scope=re.search(r'Credential=[^/]+/[^/]+/([^/]+)/',headers.get('Authorization',''))
        region=scope[1] if scope else 'us-east-1'
        self.regions.add(region);backend=self.backends(region)
        name=request.get('name')
        if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9-]{2,31}',name):
            return self.error(operation,'ValidationException','Invalid collection/policy name.')
        if operation=='DeleteSecurityPolicy':
            kind=request.get('type')
            if kind not in ('encryption','network'):return self.error(operation,'ValidationException','Invalid policy type.')
            selected=next(((key,p) for key,p in backend.security_policies.items() if p.name==name and p.type==kind),None)
            if not selected:return self.error(operation,'ResourceNotFoundException','Policy does not exist.')
            del backend.security_policies[selected[0]]
            return self.ok(operation,{})
        kind=request.get('type','SEARCH')
        if kind not in ('SEARCH','TIMESERIES','VECTORSEARCH'):return self.error(operation,'ValidationException','Invalid collection type.')
        token=request.get('clientToken')
        fingerprint=json.dumps({k:v for k,v in request.items() if k!='clientToken'},sort_keys=True)
        key=(region,token)
        if token and key in self.tokens:
            old_fingerprint,identity=self.tokens[key]
            if fingerprint!=old_fingerprint:return self.error(operation,'ConflictException','Client token reused with different parameters.')
            if identity in backend.collections:return self.ok(operation,{'createCollectionDetail':backend.collections[identity].to_dict()})
            return self.error(operation,'ConflictException','Client token belongs to a deleted collection.')
        if any(c.name==name for c in backend.collections.values()):return self.error(operation,'ConflictException','Collection name already exists.')
        policies=[p for p in backend.security_policies.values() if p.type=='encryption' and any(fnmatch.fnmatchcase('collection/'+name,r) for r in p.resources)]
        if not policies:return self.error(operation,'ValidationException','No matching encryption policy.')
        # Exact rules outrank wildcard rules. Conflicting equally specific keys are not guessed.
        exact=[p for p in policies if 'collection/'+name in p.resources]
        policies=exact or policies
        keys={(p.policy.get('AWSOwnedKey',False),p.policy.get('KmsARN')) for p in policies}
        if len(keys)!=1:return self.error(operation,'ValidationException','Conflicting encryption policies.')
        own,kms=keys.pop()
        if own == bool(kms):return self.error(operation,'ValidationException','Specify exactly one AWS-owned or customer key.')
        collection=Collection(client_token=token or '',description=request.get('description',''),name=name,
                              standby_replicas=request.get('standbyReplicas','ENABLED'),tags=request.get('tags',[]),type=kind,
                              policy={'KmsARN':kms},region=region,account_id=backend.account_id)
        backend.collections[collection.id]=collection;backend.tag_resource(collection.arn,request.get('tags',[]))
        if token:self.tokens[key]=(fingerprint,collection.id)
        return self.ok(operation,{'createCollectionDetail':collection.to_dict()})


class BedrockGuardrailEngine(JsonEngine):
    """Content-policy configuration lifecycle only, not inference/filter enforcement."""
    name='atmem-bedrock-guardrail'
    service='bedrock'
    reference='https://docs.aws.amazon.com/bedrock/latest/APIReference/API_CreateGuardrail.html'
    operations=['CreateGuardrail','GetGuardrail','UpdateGuardrail','DeleteGuardrail','ListGuardrails','ListTagsForResource','TagResource','UntagResource']

    def __init__(self,account='123456789012'):
        self.account=account;self.items={};self.tags={};self.tokens={}

    def inventory(self):return ['bedrock:guardrail:'+arn for arn in self.items]

    def handle(self,method,path,query,headers,body):
        import copy,uuid
        path=path.rstrip('/')
        if not (path=='/guardrails' or path.startswith('/guardrails/') or path in ('/listTagsForResource','/tagResource','/untagResource')):return None
        scope=re.search(r'Credential=[^/]+/[^/]+/([^/]+)/',headers.get('Authorization',''));region=scope[1] if scope else 'us-east-1'
        try:request=json.loads(body or b'{}')
        except ValueError:return self.error('Guardrail','ValidationException','Invalid JSON')
        if not isinstance(request,dict):return self.error('Guardrail','ValidationException','Request body must be an object.')
        if path in ('/listTagsForResource','/tagResource','/untagResource'):
            arn=request.get('resourceARN');item=self.items.get(arn)
            op=path[1].upper()+path[2:]
            if item is None:return self.error(op,'ResourceNotFoundException','Guardrail not found',404)
            if path=='/listTagsForResource':return self.ok(op,{'tags':[{'key':k,'value':v} for k,v in self.tags[arn].items()]})
            if path=='/tagResource':self.tags[arn].update({t['key']:t['value'] for t in request.get('tags',[])});return self.ok(op,{})
            for key in request.get('tagKeys',[]):self.tags[arn].pop(key,None)
            return self.ok(op,{})
        if path=='/guardrails' and method=='GET':
            return self.ok('ListGuardrails',{'guardrails':[{k:i[k] for k in ('guardrailId','guardrailArn','name','version','createdAt','updatedAt')} for i in self.items.values() if i['guardrailArn'].split(':')[3]==region]})
        identifier=urllib.parse.unquote(path[len('/guardrails/'):]) if path!='/guardrails' else None
        if identifier and '/' in identifier and not identifier.startswith('arn:'):return None
        arn=identifier if identifier and identifier.startswith('arn:') else f'arn:aws:bedrock:{region}:{self.account}:guardrail/{identifier}'
        item=self.items.get(arn)
        if identifier and (item is None or arn.split(':')[3]!=region):return self.error('GetGuardrail','ResourceNotFoundException','Guardrail not found',404)
        version=query.get('guardrailVersion',['DRAFT'])[0]
        if version!='DRAFT':return self.error('GetGuardrail','ResourceNotFoundException','Only DRAFT is implemented.',404)
        if method=='GET' and identifier:return self.ok('GetGuardrail',copy.deepcopy(item))
        if method=='DELETE' and identifier:
            del self.items[arn];self.tags.pop(arn,None);return self.ok('DeleteGuardrail',{})
        operation='CreateGuardrail' if identifier is None else 'UpdateGuardrail'
        if method not in ('POST','PUT'):return None
        allowed={'name','description','blockedInputMessaging','blockedOutputsMessaging','contentPolicyConfig','tags','clientRequestToken'}
        if set(request)-allowed:return self.error(operation,'EmulatorNotImplemented','Only content-policy guardrails are qualified; other policy/KMS/profile members are not implemented.')
        if not all(isinstance(request.get(k),str) and request[k] for k in ('name','blockedInputMessaging','blockedOutputsMessaging')):return self.error(operation,'ValidationException','Name and blocked messages are required.')
        filters=request.get('contentPolicyConfig',{}).get('filtersConfig',[])
        if not filters:return self.error(operation,'ValidationException','Content filters are required.')
        for f in filters:
            if f.get('type') not in ('SEXUAL','VIOLENCE','HATE','INSULTS','MISCONDUCT','PROMPT_ATTACK') or any(f.get(k) not in ('NONE','LOW','MEDIUM','HIGH') for k in ('inputStrength','outputStrength')):
                return self.error(operation,'ValidationException','Invalid content filter type or strength.')
        token=request.get('clientRequestToken');fingerprint=json.dumps({k:v for k,v in request.items() if k!='clientRequestToken'},sort_keys=True)
        if identifier is None and token and (region,token) in self.tokens:
            previous,old=self.tokens[(region,token)]
            if previous!=fingerprint:return self.error(operation,'ConflictException','Client token parameters differ.',409)
            if old not in self.items:return self.error(operation,'ConflictException','Client token belongs to deleted guardrail.',409)
            return self.ok(operation,{k:self.items[old][k] for k in ('guardrailId','guardrailArn','version','createdAt')})
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        if item is None:
            identity=uuid.uuid4().hex[:12];arn=f'arn:aws:bedrock:{region}:{self.account}:guardrail/{identity}'
            item={'guardrailId':identity,'guardrailArn':arn,'version':'DRAFT','createdAt':now}
            self.tags[arn]={t['key']:t['value'] for t in request.get('tags',[])}
        item.update({k:request[k] for k in ('name','description','blockedInputMessaging','blockedOutputsMessaging') if k in request})
        item.update(updatedAt=now,status='READY',contentPolicy={'filters':copy.deepcopy(filters)})
        self.items[arn]=item
        if identifier is None and token:self.tokens[(region,token)]=(fingerprint,arn)
        return self.ok(operation,{k:item[k] for k in ('guardrailId','guardrailArn','version','createdAt','updatedAt')})


class KnowledgeBaseEngine(JsonEngine):
    """VECTOR/OpenSearch registration lifecycle, not retrieval, ingestion or index validation."""
    name='atmem-bedrock-knowledge-base'
    service='bedrock'
    reference='https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_CreateKnowledgeBase.html'
    operations=['CreateKnowledgeBase','GetKnowledgeBase','UpdateKnowledgeBase','DeleteKnowledgeBase','ListKnowledgeBases','ListTagsForResource','TagResource','UntagResource']

    def __init__(self,collections,account='123456789012'):
        self.collections=collections;self.account=account;self.items={};self.tags={};self.tokens={}

    def inventory(self):return ['bedrock:knowledge-base:'+arn for arn in self.items]

    def handle(self,method,path,query,headers,body):
        import copy,uuid
        path=path.rstrip('/')
        if not (path=='/knowledgebases' or path.startswith('/knowledgebases/') or path.startswith('/tags/')):return None
        scope=re.search(r'Credential=[^/]+/[^/]+/([^/]+)/',headers.get('Authorization',''));region=scope[1] if scope else 'us-east-1'
        try:request=json.loads(body or b'{}')
        except ValueError:return self.error('KnowledgeBase','ValidationException','Invalid JSON')
        if not isinstance(request,dict):return self.error('KnowledgeBase','ValidationException','Expected an object.')
        if path.startswith('/tags/'):
            arn=urllib.parse.unquote(path[6:]);item=self.items.get(arn)
            if item is None:return self.error('Tags','ResourceNotFoundException','Knowledge base not found',404)
            if method=='GET':return self.ok('ListTagsForResource',{'tags':copy.deepcopy(self.tags[arn])})
            if method=='POST':self.tags[arn].update(request.get('tags',{}));return self.ok('TagResource',{})
            if method=='DELETE':
                for key in query.get('tagKeys',[]):self.tags[arn].pop(key,None)
                return self.ok('UntagResource',{})
            return None
        if path=='/knowledgebases' and method=='POST':
            return self.ok('ListKnowledgeBases',{'knowledgeBaseSummaries':[{k:i[k] for k in ('knowledgeBaseId','name','status','updatedAt')} for i in self.items.values() if i['knowledgeBaseArn'].split(':')[3]==region]})
        identifier=path[len('/knowledgebases/'):] if path!='/knowledgebases' else None
        if identifier and '/' in identifier:return None
        arn=f'arn:aws:bedrock:{region}:{self.account}:knowledge-base/{identifier}'
        item=self.items.get(arn)
        if identifier and item is None:return self.error('KnowledgeBase','ResourceNotFoundException','Knowledge base not found',404)
        if identifier and method=='GET':return self.ok('GetKnowledgeBase',{'knowledgeBase':copy.deepcopy(item)})
        if identifier and method=='DELETE':
            del self.items[arn];self.tags.pop(arn,None)
            return self.ok('DeleteKnowledgeBase',{'knowledgeBaseId':identifier,'status':'DELETING'})
        if method!='PUT':return None
        operation='UpdateKnowledgeBase' if identifier else 'CreateKnowledgeBase'
        if set(request)-{'name','roleArn','description','knowledgeBaseConfiguration','storageConfiguration','tags','clientToken'}:return self.error(operation,'EmulatorNotImplemented','Unsupported knowledge-base configuration member.')
        config=request.get('knowledgeBaseConfiguration',{});storage=request.get('storageConfiguration',{})
        if config.get('type')!='VECTOR' or storage.get('type')!='OPENSEARCH_SERVERLESS':return self.error(operation,'EmulatorNotImplemented','Only VECTOR/OpenSearch Serverless registration is implemented.')
        vector=config.get('vectorKnowledgeBaseConfiguration',{});target=storage.get('opensearchServerlessConfiguration',{})
        if not request.get('name') or not re.fullmatch(r'arn:aws[\w-]*:iam::\d{12}:role/.+',request.get('roleArn','')) or not vector.get('embeddingModelArn'):
            return self.error(operation,'ValidationException','Name, role ARN and embedding model ARN required.')
        mapping=target.get('fieldMapping',{})
        if not target.get('vectorIndexName') or not all(mapping.get(k) for k in ('vectorField','textField','metadataField')):return self.error(operation,'ValidationException','Index name and complete field mapping required.')
        collection=target.get('collectionArn')
        if not any(c.arn==collection for c in self.collections(region).values()):return self.error(operation,'ValidationException','Referenced collection does not exist in this region.')
        token=request.get('clientToken');fingerprint=json.dumps({k:v for k,v in request.items() if k!='clientToken'},sort_keys=True)
        if not identifier and token and (region,token) in self.tokens:
            old,previous=self.tokens[(region,token)]
            if old!=fingerprint or previous not in self.items:return self.error(operation,'ConflictException','Client token parameters/state differ.',409)
            return self.ok(operation,{'knowledgeBase':copy.deepcopy(self.items[previous])})
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        if item is None:
            identity=uuid.uuid4().hex[:10].upper();arn=f'arn:aws:bedrock:{region}:{self.account}:knowledge-base/{identity}'
            item={'knowledgeBaseId':identity,'knowledgeBaseArn':arn,'createdAt':now};self.tags[arn]=copy.deepcopy(request.get('tags',{}))
        for k in ('name','roleArn','description','knowledgeBaseConfiguration','storageConfiguration'):
            if k in request:item[k]=copy.deepcopy(request[k])
        item.update(status='ACTIVE',updatedAt=now);self.items[arn]=item
        if not identifier and token:self.tokens[(region,token)]=(fingerprint,arn)
        return self.ok(operation,{'knowledgeBase':copy.deepcopy(item)})
