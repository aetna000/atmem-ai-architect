"""Scoped operator-attested policy review. Never fabricates a provider approval API."""
import base64
from datetime import datetime,timezone
import json
import re
from structured_output import _object
from structured_http import PolicyUnverified

def verify_policy_review(encoded,expected,now=None):
    try:
        review=json.loads(base64.b64decode(encoded,validate=True),object_pairs_hook=_object)
        if any(review.get(key)!=value for key,value in expected.items()):raise PolicyUnverified()
        if not isinstance(review.get('approvedBy'),str) or not review['approvedBy'].strip():raise PolicyUnverified()
        if not re.fullmatch(r'[0-9a-f]{64}',review.get('evidenceSha256','')) or review['evidenceSha256']=='0'*64:raise PolicyUnverified()
        expiry=datetime.fromisoformat(review['expiresAt']);now=now or datetime.now(timezone.utc)
        if expiry.tzinfo is None or not 0<(expiry-now).total_seconds()<=31*86400:raise PolicyUnverified()
        return review
    except Exception:raise PolicyUnverified() from None
