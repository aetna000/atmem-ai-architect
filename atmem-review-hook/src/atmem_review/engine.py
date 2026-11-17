"""Evidence-first review. Unknown policy coverage can never become a clean pass."""
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from jsonschema import Draft202012Validator

from . import __version__
from .policy import parse_policy
from .terraform import UNKNOWN, resources, region, value_at

SCHEMAS = Path(__file__).with_name('schemas')
INPUT = json.loads((SCHEMAS/'review_plan.input.schema.json').read_text())
OUTPUT = json.loads((SCHEMAS/'review_plan.output.schema.json').read_text())
GROUPS = {'aws_db_instance':'database','aws_rds_cluster':'database','aws_dynamodb_table':'database',
          'aws_s3_bucket':'storage','aws_sqs_queue':'queue','aws_lambda_function':'compute',
          'aws_ecs_service':'compute','aws_instance':'compute'}
# Reviewed AWS region geographies: https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html (2026-11-17).
COUNTRIES = {'ap-southeast-2':'AU','ap-southeast-4':'AU','us-east-1':'US','us-east-2':'US','us-west-1':'US','us-west-2':'US',
             'ca-central-1':'CA','ca-west-1':'CA','eu-west-1':'IE','eu-west-2':'GB','eu-west-3':'FR','eu-central-1':'DE',
             'ap-southeast-1':'SG','ap-northeast-1':'JP','ap-northeast-2':'KR','ap-south-1':'IN','sa-east-1':'BR'}
PUBLIC_RULE = 'no security group ingress from 0.0.0.0/0 except to the load balancer on 443'


def validate(value, schema):
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        # Do not stringify validation errors: they embed private input values.
        raise ValueError('Invalid review shape at '+'.'.join(str(p) for p in error.absolute_path))


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode()


def review_plan(payload, *, cost_engine=None, semantic_engine=None, today=None):
    validate(payload, INPUT)
    if len(json_bytes(payload)) > 16_000_000 or len(payload['artifacts']) > 64:
        raise ValueError('Review exceeds 16 MB or 64 artifacts; input was not truncated')
    labels=[payload['rules'].get('path'),payload.get('terraform_plan',{}).get('path'),*[a.get('path') for a in payload['artifacts']]]
    if any(label is not None and (len(label)>2000 or any(ord(c)<32 for c in label)) for label in labels):
        raise ValueError('Citation labels exceed their bounds')
    today = today or datetime.now(timezone.utc).date()
    policy = parse_policy(payload['rules']['content'])
    options = {'fail_on':'error','cost_estimate':'auto','currency':'USD','max_findings':50,**payload.get('options', {})}
    plan = payload.get('terraform_plan', {}).get('json')
    items, complete = resources(plan) if plan is not None else ([], False)
    violations, unverified, risks, fixes = [], [], [], []
    finding_count=0;has_error=False;has_warning=False;omitted_unknowns={};worst_priority=0
    priority={'error':0,'warning':1,'info':2}
    unknown_reasons={}
    if not policy['rules'] and not policy['adrs']:
        unverified.append({'rule_id':'POLICY','reason':'No enforceable rules were configured.'})
    if len([r for group,r in policy['rules'] if group=='budget'])>1:
        raise ValueError('One review supports one explicit environment budget')
    paths=[a['path'] for a in payload['artifacts'] if a.get('path')]
    if len(paths)!=len(set(paths)):raise ValueError('Artifact citation paths must be unique')
    path = payload['rules'].get('path', 'architecture.md')
    plan_path = payload.get('terraform_plan', {}).get('path', 'terraform-plan.json')
    def unknown(rule, reason):
        record={'rule_id':rule['id'], 'reason':reason}
        seen=unknown_reasons.setdefault(rule['id'],set())
        if reason in seen:return
        if len(seen)<3:
            seen.add(reason);unverified.append(record)
        else:omitted_unknowns[rule['id']]=omitted_unknowns.get(rule['id'],0)+1
    def evidence(item, attribute, value):
        if len(json_bytes(value))>4096:raise ValueError('Evidence value exceeds the scalar/detail bound')
        return {'source':'terraform_plan','path':plan_path,'resource_address':item['address'],'attribute':attribute,'value':value}
    def add(rule, title, ev, explanation, target=None, change=None):
        nonlocal finding_count,has_error,has_warning,worst_priority
        severity=rule.get('severity','error');exception_id=None
        addresses={e.get('resource_address') for e in ev if e.get('resource_address')}
        for ex in policy['exceptions']:
            if (ex['rule_id']==rule['id'] and date.fromisoformat(str(ex['expires']))>=today and
                ('resource_addresses' not in ex or addresses and addresses<=set(ex['resource_addresses']))):
                severity='warning' if severity=='error' else severity;exception_id=ex['id'];break
        finding_count+=1;has_error=has_error or severity=='error';has_warning=has_warning or severity=='warning'
        record={'rule_id':rule['id'],'severity':severity,'title':title,'evidence':ev,'explanation':explanation,'exception_id':exception_id}
        fix={'rule_id':rule['id'],'target':target,'change':change} if target and change else None
        limit=options['max_findings']
        if len(violations)<limit:
            violations.append(record);fixes.append(fix);worst_priority=max(worst_priority,priority[severity])
        elif priority[severity]<worst_priority:
            worst=max(range(len(violations)),key=lambda i:priority[violations[i]['severity']])
            violations[worst]=record;fixes[worst]=fix
            worst_priority=max(priority[v['severity']] for v in violations)
    for ex in policy['exceptions']:
        if date.fromisoformat(str(ex['expires']))<today:
            risks.append({'id':'expired_exception','severity':'warning','description':'Exception '+ex['id']+' expired; it grants no waiver.','related_rule_ids':[ex['rule_id']]})
    cost = {'status':'skipped','reason':'cost_estimate_off' if options['cost_estimate']=='off' else 'no_terraform_plan'}
    if plan is not None and options['cost_estimate']!='off':
        if cost_engine is None:cost={'status':'skipped','reason':'engine_unavailable'}
        else:
            try:cost=cost_engine(plan,options['currency'])
            except Exception:cost={'status':'error','reason':'engine_failed'}
        try:
            validate({'schema_version':'1.0','verdict':'warn','summary':'Cost validation','violations':[],'cost':cost,'risks':[],
                  'suggested_fixes':[],'unverified':[],'reviewer':{'name':'atmem-review','version':__version__}},OUTPUT)
            json_bytes(cost)
        except (ValueError,TypeError):cost={'status':'error','reason':'invalid_cost_output'}
    for group, rule in policy['rules']:
        ident=rule['id']
        if group=='budget':
            maximum=rule.get('monthly_max')
            if type(maximum) not in {int,float} or not math.isfinite(maximum) or maximum<=0 or not re.fullmatch('[A-Z]{3}',str(rule.get('currency',''))):
                raise ValueError('Budget requires a positive monthly_max and ISO currency')
            if cost.get('status')!='estimated' or type(cost.get('monthly_total')) not in {int,float} or cost['monthly_total']<0:
                unknown(rule,'Monthly cost is unavailable; missing pricing is not zero.');continue
            if cost.get('currency')!=rule['currency']:
                unknown(rule,'Cost and budget currencies differ; no exchange rate was assumed.');continue
            if not complete:unknown(rule,'Only changes were supplied; unchanged-resource environment cost is not established.')
            environment=rule.get('environment')
            # A single supplied plan is one environment; no automatic fleet aggregation.
            if environment:
                risks.append({'id':'budget_scope','severity':'info','description':'Budget '+ident+' assumes the supplied complete plan is the entire '+environment+' environment.','related_rule_ids':[ident]})
            total=cost['monthly_total'];cost.update(budget_monthly=maximum,over_budget=total>maximum)
            threshold=rule.get('warn_at_percent',80)
            if type(threshold) not in {int,float} or not math.isfinite(threshold) or not 0<threshold<=100:raise ValueError('Invalid budget warning threshold')
            if total>maximum or total>=maximum*threshold/100:
                selected=rule if total>maximum else {**rule,'severity':'warning'}
                add(selected,'Monthly estimate exceeds budget' if total>maximum else 'Monthly estimate approaches budget',
                    [{'source':'cost_engine','attribute':'monthly_total','value':total}],
                    f'Estimate {total} {rule["currency"]}; budget {maximum} {rule["currency"]}.',plan_path,'Reduce the priced resources or obtain an explicit budget exception.')
            continue
        if plan is None:
            unknown(rule,'No Terraform plan supplied; infrastructure properties are unverified.');continue
        if not complete:unknown(rule,'Desired-state inventory is incomplete or deferred; only supplied known resources were checked.')
        if group=='regions':
            allowed=rule.get('allowed')
            if not isinstance(allowed,list) or not allowed or any(not isinstance(x,str) for x in allowed):raise ValueError('Regions require a nonempty allowed list')
            for item in items:
                actual, attr=region(item,plan)
                if actual is UNKNOWN or not isinstance(actual,str) or len(actual)>128:unknown(rule,'Region unresolved for '+item['address']);continue
                if actual not in allowed:add(rule,'Unapproved region',[evidence(item,attr,actual)],'The resolved region is outside the policy allowlist.',item['address'],'Use an approved region and regenerate the plan.')
        elif group=='services':
            forbidden=rule.get('forbidden',[]);approved=rule.get('approved',{})
            if not isinstance(forbidden,list) or not isinstance(approved,dict) or any(not isinstance(v,list) for v in approved.values()):raise ValueError('Invalid service allowlist')
            if not forbidden and not approved:unknown(rule,'No service constraints were configured.')
            for item in items:
                resource=item['type'];category=GROUPS.get(resource)
                if resource in forbidden or category in approved and resource not in approved[category]:
                    add(rule,'Unapproved service',[evidence(item,'type',resource)],'Resource type conflicts with the explicit service policy.',item['address'],'Select an approved service or record an accepted exception.')
                elif approved and category is None:unknown(rule,'Service category is not mapped for '+resource+'; no allowlist inference was made.')
        elif group=='network':
            check=rule.get('check')
            if isinstance(check,dict) and set(check)=={'resource','attribute','must_equal'}:
                if type(check['must_equal']) not in {bool,int,float,str,type(None)}:raise ValueError('Attribute predicates require scalar expected values')
                for item in items:
                    if item['type']!=check['resource']:continue
                    actual=value_at(item['values'],item['unknown'],check['attribute'])
                    if actual is UNKNOWN or isinstance(actual,(dict,list)) or isinstance(actual,str) and len(actual)>4096:unknown(rule,check['attribute']+' is computed, unsupported or absent for '+item['address']);continue
                    if type(actual)!=type(check['must_equal']) or actual!=check['must_equal']:
                        add(rule,'Network attribute violates policy',[evidence(item,check['attribute'],actual)],rule.get('rule','Explicit attribute predicate failed.'),item['address'],'Set '+check['attribute']+' to the required value and regenerate the plan.')
            elif rule.get('rule','').lower().rstrip('.')==PUBLIC_RULE and check is None or isinstance(check,dict) and check=={'kind':'public_ingress'}:
                _ingress(items,plan,rule,add,unknown,evidence)
            else:unknown(rule,'Free-form network rule has no supported machine predicate.')
        elif group=='data_residency':
            allowed=rule.get('must_stay_in');classes=rule.get('data_classes');applies=rule.get('applies_to')
            if not all(isinstance(x,list) and x for x in [allowed,classes,applies]):raise ValueError('Residency requires countries, data classes and resource categories')
            categories={'database':'databases','storage':'object_storage'}
            for item in items:
                category=categories.get(GROUPS.get(item['type']))
                if category not in applies:continue
                tags=value_at(item['values'],item['unknown'],'tags')
                declared=tags.get('atmem:data_classes') if isinstance(tags,dict) else None
                if not isinstance(declared,str):unknown(rule,'Data classification is not established for '+item['address']);continue
                if not set(declared.split(','))&set(classes):continue
                actual,attr=region(item,plan);country=COUNTRIES.get(actual) if isinstance(actual,str) else None
                if country is None:unknown(rule,'No qualified region-to-country mapping for '+item['address']);continue
                if country not in allowed:add(rule,'Data residency conflict',[evidence(item,attr,actual)],'Tagged data class resolves outside the allowed countries.',item['address'],'Select an approved data location; separately review replication and backups.')
            if set(applies)-{'databases','object_storage'}:unknown(rule,'Backup/log/residency topology requires additional qualified resource adapters.')
        elif group=='uptime':
            # Redundancy is inspectable. An uptime percentage is never measured by a plan.
            unknown(rule,'An uptime target cannot be established from configuration; operational/SLO evidence is required.')
            if rule.get('requires')=='No single-AZ stateful component unless an exception is recorded':
                for item in items:
                    if item['type']!='aws_db_instance':continue
                    multi=value_at(item['values'],item['unknown'],'multi_az')
                    if multi is False:add(rule,'Single-AZ stateful database',[evidence(item,'multi_az',False)],'The required database redundancy is absent.',item['address'],'Enable multi-AZ or record a scoped expiring exception.')
    if policy['adrs']:
        for ident in policy['adrs']:unknown({'id':ident},'ADR semantic consistency has not been verified by a cited model review.')
    if semantic_engine:
        _semantic(payload,policy,semantic_engine,add,unknown,unverified)
    if cost.get('status')=='error':risks.append({'id':'cost_engine_error','severity':'warning','description':'Cost estimation failed; no price was invented.'})
    for ident,count in omitted_unknowns.items():unverified.append({'rule_id':ident,'reason':f'{count} additional unknown cases; representative reasons shown above.'})
    failed=has_error
    warned=has_warning or bool(unverified) or finding_count>options['max_findings'] or any(r['severity']=='warning' for r in risks)
    verdict='fail' if failed or options['fail_on']=='warning' and warned else 'warn' if warned else 'pass'
    total=finding_count;limit=options['max_findings']
    if total>limit:risks.append({'id':'findings_limited','severity':'warning','description':f'{total} findings detected; {limit} returned. Verdict covers all findings; raise max_findings for more.'})
    result={'schema_version':'1.0','verdict':verdict,'summary':f'{verdict.upper()}: {total} policy findings; {len(unverified)} unverified checks. Supplied artifacts only; no deployment verification.',
            'rules_file':{'path':path,'sha256':hashlib.sha256(payload['rules']['content'].encode()).hexdigest(),'rule_count':len(policy['rules']),'adr_count':len(policy['adrs'])},
            'violations':sorted(violations,key=lambda v:{'error':0,'warning':1,'info':2}[v['severity']])[:limit],'cost':cost,'risks':risks,
            'suggested_fixes':[f for f in fixes if f][:limit],'unverified':unverified,'reviewer':{'name':'atmem-review','version':__version__,'reviewed_at':datetime.now(timezone.utc).isoformat(),'input_sha256':hashlib.sha256(json_bytes(payload)).hexdigest()}}
    validate(result,OUTPUT)
    json_bytes(result)  # Reject NaN/infinite adapter values before returning a verdict.
    return result


def _ingress(items,plan,rule,add,unknown,evidence):
    lb_groups=set()
    for item in items:
        if item['type'] in {'aws_lb','aws_alb'}:
            groups=value_at(item['values'],item['unknown'],'security_groups')
            if isinstance(groups,list):lb_groups.update(x for x in groups if isinstance(x,str))
    for item in items:
        groups=[]
        if item['type']=='aws_security_group':
            ingress=item['values'].get('ingress')
            mask=item['unknown'].get('ingress',False) if isinstance(item['unknown'],dict) else item['unknown']
            if not isinstance(ingress,list) or mask is True:
                unknown(rule,'Ingress unresolved for '+item['address']);continue
            for i,g in enumerate(ingress):
                if not isinstance(g,dict):unknown(rule,'Unsupported ingress entry for '+item['address']);continue
                entry_mask=mask[i] if isinstance(mask,list) and i<len(mask) else mask if isinstance(mask,dict) else False
                groups.append((g,item['values'].get('id'),'ingress.'+str(i),entry_mask))
        elif item['type']=='aws_security_group_rule':
            kind=value_at(item['values'],item['unknown'],'type')
            if kind is UNKNOWN:unknown(rule,'Rule direction unresolved for '+item['address']);continue
            if kind!='ingress':continue
            groups=[(item['values'],item['values'].get('security_group_id'),'cidr_blocks',item['unknown'])]
        elif item['type']=='aws_vpc_security_group_ingress_rule':
            groups=[(item['values'],item['values'].get('security_group_id'),'cidr_ipv4',item['unknown'])]
        for values,identity,attribute,mask in groups:
            relevant=['cidr_blocks','ipv6_cidr_blocks','cidr_ipv4','cidr_ipv6','from_port','to_port','protocol','ip_protocol']
            if mask is True or isinstance(mask,dict) and any(_has_unknown(mask.get(k,False)) for k in relevant):
                unknown(rule,'Ingress has computed attributes for '+item['address']);continue
            cidrs=values.get('cidr_blocks',[])+values.get('ipv6_cidr_blocks',[])
            cidrs += [values.get('cidr_ipv4'),values.get('cidr_ipv6')]
            if not any(isinstance(c,str) for c in cidrs):
                if not values.get('self') and not isinstance(values.get('source_security_group_id',values.get('referenced_security_group_id')),str):
                    unknown(rule,'Ingress source is unresolved for '+item['address'])
                continue
            if not any(c in {'0.0.0.0/0','::/0'} for c in cidrs if isinstance(c,str)):continue
            start,end=values.get('from_port'),values.get('to_port')
            protocol=values.get('protocol',values.get('ip_protocol'))
            if protocol is None or protocol in {'tcp','6'} and (start is None or end is None):
                unknown(rule,'Public ingress ports/protocol unresolved for '+item['address']);continue
            if start==end==443 and protocol in {'tcp','6'}:
                if identity in lb_groups:continue
                unknown(rule,'Public 443 ingress lacks proven load-balancer association for '+item['address']);continue
            prefix=attribute+'.' if attribute.startswith('ingress.') else ''
            cited=[]
            for key in ['cidr_blocks','ipv6_cidr_blocks']:
                for index,cidr in enumerate(values.get(key,[])):
                    if cidr in {'0.0.0.0/0','::/0'}:cited.append(evidence(item,prefix+key+'.'+str(index),cidr))
            for key in ['cidr_ipv4','cidr_ipv6']:
                if values.get(key) in {'0.0.0.0/0','::/0'}:cited.append(evidence(item,prefix+key,values[key]))
            for key in ['from_port','to_port','protocol','ip_protocol']:
                if key in values:cited.append(evidence(item,prefix+key,values[key]))
            add(rule,'Public ingress outside the load-balancer exception',cited[:6],
                'World-open ingress is permitted only for a proven load balancer on TCP 443.',item['address'],'Restrict ingress to approved private sources or prove the load-balancer 443 exception.')


def _has_unknown(value):
    return value is True or isinstance(value,dict) and any(_has_unknown(v) for v in value.values()) or isinstance(value,list) and any(_has_unknown(v) for v in value)


def _semantic(payload,policy,engine,add,unknown,unverified):
    try:
        findings=engine(payload)
        if not isinstance(findings,dict) or set(findings)-{'violations','verified_adrs'}:raise ValueError('Invalid semantic result')
        known={r['id']:r for _,r in policy['rules']};known.update({a:{'id':a,'severity':'error'} for a in policy['adrs']})
        for finding in findings.get('violations',[]):
            if set(finding)!={'rule_id','title','path','line_start','line_end','excerpt','explanation'} or finding['rule_id'] not in known:raise ValueError('Invalid semantic finding')
            artifact=next((a for a in payload['artifacts'] if a.get('path')==finding['path']),None)
            if artifact is None:raise ValueError('Unknown citation source')
            start,end=finding['line_start'],finding['line_end']
            if type(start)!=int or type(end)!=int or not 1<=start<=end<=len(artifact['content'].splitlines()):raise ValueError('Invalid citation range')
            quoted='\n'.join(artifact['content'].splitlines()[start-1:end])
            if quoted!=finding['excerpt'] or len(quoted)>500:raise ValueError('Invented or oversized citation')
        verified=findings.get('verified_adrs',[])
        if not isinstance(verified,list) or any(a not in policy['adrs'] for a in verified):raise ValueError('Unknown ADR verification')
        # All findings validated before any output is accepted. Model cannot erase
        # deterministic resource uncertainty or existing violations.
        for f in findings.get('violations',[]):
            add(known[f['rule_id']],f['title'],[{'source':'artifact','path':f['path'],'line_start':f['line_start'],'line_end':f['line_end'],'excerpt':f['excerpt']}],f['explanation'])
        # A model's "verified" declaration is advisory, never proof of an ADR.
        for a in verified:unknown({'id':a},'Model reported consistency; runtime/account facts remain unverified.')
    except Exception:
        for ident in policy['adrs'] or ['SEMANTIC-REVIEW']:unknown({'id':ident},'Semantic reviewer unavailable or returned invalid evidence; no finding was invented.')
