"""Server-authorized billing policy; the browser cannot select prices or grants."""
import copy
import uuid
from datetime import datetime, timezone
from .credits import Conflict, CreditError, units, MAX_UNITS

# Explicit owner decisions from 2026-11-15. One USD is one million ledger units.
USD_MICROS = 1_000_000
DEFAULT_POLICY = {
    'revision': 1,
    'currency': 'usd',
    'welcomeMicros': 5 * USD_MICROS,
    'minimumPurchaseCents': 100,
    'maximumPurchaseCents': 99_999_999,  # Provider integer amount boundary, not a chosen pack price.
    'dailyPlatformBudgetMicros': 0,  # Spending stays off until an administrator sets the launch budget.
    'platformMarkupBasisPoints': 10_000,  # At-cost proposal; visible/editable before launch.
    'platformSpendingEnabled': False,
}
_FIELDS = set(DEFAULT_POLICY) - {'revision', 'currency'}


def validate_policy(value):
    if type(value) is not dict or set(value) != set(DEFAULT_POLICY) or value['currency'] != 'usd':
        raise CreditError('Use the configured USD billing policy')
    if type(value['revision']) is not int or value['revision'] < 1:
        raise CreditError('Invalid billing revision')
    units(value['welcomeMicros']); units(value['dailyPlatformBudgetMicros'])
    for key in ['minimumPurchaseCents', 'maximumPurchaseCents']:
        if type(value[key]) is not int or not 100 <= value[key] <= 99_999_999:
            raise CreditError('Top-ups must start at USD1 or more and fit the payment provider amount boundary')
    if value['maximumPurchaseCents'] < value['minimumPurchaseCents']:
        raise CreditError('Purchase maximum cannot be below its minimum')
    if type(value['platformMarkupBasisPoints']) is not int or not 0 < value['platformMarkupBasisPoints'] <= 100_000:
        raise CreditError('Configure an explicit bounded model-cost multiplier')
    if type(value['platformSpendingEnabled']) is not bool or value['platformSpendingEnabled'] and not value['dailyPlatformBudgetMicros']:
        raise CreditError('A positive daily spending budget is required before enabling platform AI')
    return copy.deepcopy(value)


class BillingConfiguration:
    def __init__(self, store): self.store = store

    def current(self):
        return self.store.transaction(lambda tx: validate_policy(tx.get('settings', 'billing') or copy.deepcopy(DEFAULT_POLICY)))

    def update(self, identity, expected_revision, changes):
        identity.require_admin()
        if type(expected_revision) is not int or type(changes) is not dict or not changes or set(changes) - _FIELDS:
            raise CreditError('Update only supported billing settings with the current revision')
        audit_id = uuid.uuid4().hex
        def apply(tx):
            previous = validate_policy(tx.get('settings', 'billing') or copy.deepcopy(DEFAULT_POLICY))
            if previous['revision'] != expected_revision:
                raise Conflict('Billing settings changed. Reload before saving')
            updated = validate_policy({**previous, **changes, 'revision': previous['revision'] + 1})
            tx.set('settings', 'billing', updated)
            tx.create('audit', audit_id, dict(kind='billing_policy_updated', uid=identity.uid,
                      previous=previous, updated=updated, createdAt=datetime.now(timezone.utc).isoformat()))
            return updated
        return self.store.transaction(apply)

    def purchase_quote(self, amount_cents):
        policy = self.current()
        if type(amount_cents) is not int or not policy['minimumPurchaseCents'] <= amount_cents <= policy['maximumPurchaseCents']:
            raise CreditError('Choose a USD top-up within the configured purchase limits')
        return dict(amountCents=amount_cents, currency='usd', creditMicros=amount_cents * 10_000,
                    policyRevision=policy['revision'])
