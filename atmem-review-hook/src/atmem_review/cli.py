"""Local wrapper: caller chooses files; review_plan itself never reads those paths."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from .engine import review_plan
from .codec import strict_json
from .adapters import Infracost,OpenRouterSemantic


def load(path):
    if path=='-':raw=sys.stdin.buffer.read(16_000_001)
    else:
        with open(path,'rb') as stream:raw=stream.read(16_000_001)
    if len(raw)>16_000_000:raise ValueError('Input exceeds 16 MB; no truncation')
    return strict_json(raw)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only architecture policy review; JSON on stdout, verdict in exit status.')
    parser.add_argument('input',help='Review request JSON file, or - for stdin')
    parser.add_argument('--allow-cost-egress',action='store_true',help='Permit the fixed Infracost JSON adapter and pricing network calls')
    parser.add_argument('--allow-model-egress',action='store_true',help='Permit filtered prose/rules to the explicitly configured OpenRouter model')
    args=parser.parse_args(argv)
    try:
        value=load(args.input)
        result=review_plan(value,cost_engine=Infracost() if args.allow_cost_egress else None,
                           semantic_engine=OpenRouterSemantic() if args.allow_model_egress else None)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2))
        return 1 if result['verdict']=='fail' else 0
    except (ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError,RecursionError,OSError):
        print('Review rejected: invalid, unsupported or unreadable input. No verdict issued.',file=sys.stderr)
        return 2


if __name__=='__main__':sys.exit(main())
