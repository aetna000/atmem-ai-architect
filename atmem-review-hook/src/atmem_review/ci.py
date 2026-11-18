"""Rebuild the review request from current selected files, never a stale pass JSON."""
import argparse
import json
from pathlib import Path
import sys
from .codec import strict_json
from .engine import review_plan
from .adapters import Infracost,OpenRouterSemantic


def main(argv=None):
    parser=argparse.ArgumentParser(description='Fresh local policy gate from current artifact bytes. Exit 1=fail, 2=invalid/missing input.')
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--rules',required=True)
    parser.add_argument('--artifact',action='append',required=True,help='kind:relative-path; repeat for each current artifact')
    parser.add_argument('--terraform-plan')
    parser.add_argument('--strict',action='store_true')
    parser.add_argument('--allow-cost-egress',action='store_true')
    parser.add_argument('--allow-model-egress',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve()
        def selected(name):
            path=(root/name).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():raise ValueError('Selected path escapes project')
            with path.open('rb') as f:raw=f.read(16_000_001)
            if len(raw)>16_000_000:raise ValueError('Selected file exceeds bounds')
            return path.relative_to(root).as_posix(),raw.decode('utf-8')
        path,text=selected(args.rules)
        payload={'workflow':'other','rules':{'path':path,'content':text},'artifacts':[],
                 'options':{'fail_on':'warning' if args.strict else 'error','cost_estimate':'auto' if args.allow_cost_egress else 'off'}}
        for spec in args.artifact:
            kind,name=spec.split(':',1);path,text=selected(name)
            payload['artifacts'].append({'kind':kind,'path':path,'content':text})
        if args.terraform_plan:
            path,text=selected(args.terraform_plan);payload['terraform_plan']={'path':path,'json':strict_json(text)}
        result=review_plan(payload,cost_engine=Infracost() if args.allow_cost_egress else None,semantic_engine=OpenRouterSemantic() if args.allow_model_egress else None)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2))
        return 1 if result['verdict']=='fail' else 0
    except (ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError,OSError,RecursionError):
        print('Review gate rejected missing, invalid or out-of-scope input.',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
