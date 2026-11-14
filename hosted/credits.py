"""Transactional credit accounting. Only trusted server services call mutation methods.

Units are integral credit micro-units, not floating currency. Commercial conversion,
welcome grants, pack prices and provider quotes are separately versioned configuration.
A store must provide atomic, retryable transactions across account/operation/receipt
and ledger records; a process-local lock is not a production implementation.
"""
import hashlib
import re
from datetime import datetime, timezone

MAX_UNITS = 2**53 - 1


class CreditError(ValueError): pass
class Conflict(CreditError): pass
class InsufficientCredits(CreditError): pass
class AccountUnavailable(CreditError): pass


def units(value, *, zero=True):
    if type(value) is not int or not (0 if zero else 1) <= value <= MAX_UNITS:
        raise CreditError('Use bounded integer credit units')
    return value


def signed_units(value):
    if type(value) is not int or abs(value) > MAX_UNITS:
        raise CreditError('Credit balance exceeds its bound')
    return value


def identifier(value):
    if type(value) is not str or not 1 <= len(value) <= 128 or any(ord(c) < 32 for c in value):
        raise CreditError('Invalid identifier')
    return value


def digest(value):
    return hashlib.sha256(identifier(value).encode()).hexdigest()


def fingerprint(value):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{64}', value):
        raise CreditError('Use an exact request fingerprint')
    return value


class CreditLedger:
    def __init__(self, store, *, welcome_units, policy_version, clock=None):
        self.store = store
        self.welcome_units = units(welcome_units)
        self.policy = identifier(policy_version)
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def _account(self, tx, uid):
        key = digest(uid)
        account = tx.get('accounts', key)
        if not account or account['uid'] != uid or account.get('deleted'):
            raise AccountUnavailable('Account is unavailable')
        return key, account

    def register(self, uid):
        key = digest(uid)
        def apply(tx):
            previous = tx.get('accounts', key)
            if previous:
                if previous['uid'] != uid or previous.get('deleted'):
                    raise AccountUnavailable('Account is unavailable')
                return previous
            now = self.clock()
            account = dict(uid=uid, available=self.welcome_units, reserved=0, spent=0,
                           policy=self.policy, disabled=False, deleted=False, createdAt=now)
            tx.create('accounts', key, account)
            tx.create('ledger', 'welcome-' + key, dict(uid=uid, kind='welcome', delta=self.welcome_units,
                      policy=self.policy, createdAt=now))
            return account
        return self.store.transaction(apply)

    def account(self, uid):
        return self.store.transaction(lambda tx: self._account(tx, uid)[1])

    def reserve(self, uid, operation, request_sha256, ceiling):
        operation = identifier(operation); request_sha256 = fingerprint(request_sha256)
        ceiling = units(ceiling, zero=False)
        key = self._operation_key(uid, operation)
        def apply(tx):
            account_key, account = self._account(tx, uid)
            previous = tx.get('operations', key)
            if previous:
                if previous['uid'] != uid or previous['requestSha256'] != request_sha256 or previous['ceiling'] != ceiling:
                    raise Conflict('Request identifier was already used for different work')
                return previous
            if account['disabled'] or account['available'] < ceiling:
                raise InsufficientCredits('Insufficient available credits')
            now = self.clock()
            operation_record = dict(uid=uid, operation=operation, requestSha256=request_sha256,
                                    ceiling=ceiling, state='reserved', createdAt=now)
            account.update(available=account['available'] - ceiling, reserved=units(account['reserved'] + ceiling))
            tx.set('accounts', account_key, account)
            tx.create('operations', key, operation_record)
            tx.create('ledger', 'reserve-' + key, dict(uid=uid, kind='reserve', delta=0,
                      reservedDelta=ceiling, operation=operation, createdAt=now))
            return operation_record
        return self.store.transaction(apply)

    @staticmethod
    def _operation_key(uid, operation):
        identifier(uid); identifier(operation)
        return hashlib.sha256((uid + '\0' + operation).encode()).hexdigest()

    def transition(self, uid, operation, target):
        if target not in {'sent', 'uncertain'}:
            raise CreditError('Unrecognized provider transition')
        key = self._operation_key(uid, operation)
        def apply(tx):
            self._account(tx, uid)
            record = tx.get('operations', key)
            if not record or record['uid'] != uid:
                raise Conflict('Operation is unavailable')
            if record['state'] == target:
                return record
            if record['state'] != {'sent': 'reserved', 'uncertain': 'sent'}[target]:
                raise Conflict('Provider transition is not allowed')
            record.update(state=target, updatedAt=self.clock())
            tx.set('operations', key, record)
            return record
        return self.store.transaction(apply)

    def settle(self, uid, operation, used, receipt):
        """Receipt must already be verified by the broker, never supplied by a browser."""
        used = units(used); receipt = identifier(receipt); key = self._operation_key(uid, operation)
        def apply(tx):
            account_key, account = self._account(tx, uid)
            record = tx.get('operations', key)
            if not record or record['uid'] != uid:
                raise Conflict('Operation is unavailable')
            if record['state'] == 'settled':
                if record['used'] != used or record['receipt'] != receipt:
                    raise Conflict('Settlement disagrees with the retained receipt')
                return record
            if record['state'] not in {'sent', 'uncertain'} or used > record['ceiling']:
                raise Conflict('Settlement lacks admitted work or exceeds its reservation')
            receipt_key = digest(receipt)
            binding = tx.get('usage_receipts', receipt_key)
            if binding and (binding['uid'] != uid or binding['operationKey'] != key or binding['used'] != used):
                raise Conflict('Usage receipt is already bound to another operation')
            now = self.clock()
            account.update(available=account['available'] + record['ceiling'] - used,
                           reserved=account['reserved'] - record['ceiling'], spent=units(account['spent'] + used))
            record.update(state='settled', used=used, receipt=receipt, updatedAt=now)
            tx.set('accounts', account_key, account); tx.set('operations', key, record)
            if not binding:
                tx.create('usage_receipts', receipt_key, dict(uid=uid, operationKey=key, used=used, createdAt=now))
            tx.create('ledger', 'settle-' + key, dict(uid=uid, kind='usage', delta=-used,
                      reservedDelta=-record['ceiling'], operation=operation, receipt=receipt, createdAt=now))
            return record
        return self.store.transaction(apply)

    def release_unsent(self, uid, operation):
        key = self._operation_key(uid, operation)
        def apply(tx):
            account_key, account = self._account(tx, uid)
            record = tx.get('operations', key)
            if not record or record['uid'] != uid:
                raise Conflict('Operation is unavailable')
            if record['state'] == 'released':
                return record
            if record['state'] != 'reserved':
                raise Conflict('Sent or uncertain work requires a verified settlement receipt')
            account.update(available=account['available'] + record['ceiling'], reserved=account['reserved'] - record['ceiling'])
            record.update(state='released', updatedAt=self.clock())
            tx.set('accounts', account_key, account); tx.set('operations', key, record)
            tx.create('ledger', 'release-' + key, dict(uid=uid, kind='release', delta=0,
                      reservedDelta=-record['ceiling'], operation=operation, createdAt=self.clock()))
            return record
        return self.store.transaction(apply)

    def grant_purchase(self, uid, payment, amount, verified_fingerprint):
        """Fulfillment supplies the verified paid-pack snapshot, not client metadata."""
        payment = identifier(payment); amount = units(amount, zero=False); verified_fingerprint = fingerprint(verified_fingerprint)
        key = digest(payment)
        def apply(tx):
            account_key, account = self._account(tx, uid)
            previous = tx.get('payments', key)
            if previous:
                if previous['uid'] != uid or previous['units'] != amount or previous['fingerprint'] != verified_fingerprint:
                    raise Conflict('Payment receipt is bound to a different account or pack')
                return previous
            record = dict(uid=uid, payment=payment, units=amount, fingerprint=verified_fingerprint,
                          refundedUnits=0, createdAt=self.clock())
            signed_units(account['available'] + account['reserved'] + amount)
            account['available'] = signed_units(account['available'] + amount)
            tx.set('accounts', account_key, account); tx.create('payments', key, record)
            tx.create('ledger', 'purchase-' + key, dict(uid=uid, kind='purchase', delta=amount,
                      payment=payment, createdAt=self.clock()))
            return record
        return self.store.transaction(apply)

    def refund_purchase(self, payment, cumulative_units, verified_receipt):
        """Trusted payment reconciliation supplies cumulative refunded pack units."""
        key = digest(payment); cumulative_units = units(cumulative_units); verified_receipt = identifier(verified_receipt)
        def apply(tx):
            record = tx.get('payments', key)
            if not record:
                raise Conflict('Payment is not yet reconciled')
            account_key, account = self._account(tx, record['uid'])
            if cumulative_units > record['units']:
                raise Conflict('Refund exceeds the purchased pack')
            if cumulative_units <= record['refundedUnits']:
                return record
            delta = cumulative_units - record['refundedUnits']
            account['available'] = signed_units(account['available'] - delta)  # Retain spent/refunded debt.
            record.update(refundedUnits=cumulative_units, refundReceipt=verified_receipt, updatedAt=self.clock())
            tx.set('accounts', account_key, account); tx.set('payments', key, record)
            tx.create('ledger', 'refund-' + key + '-' + str(cumulative_units), dict(uid=record['uid'],
                      kind='refund', delta=-delta, payment=payment, receipt=verified_receipt, createdAt=self.clock()))
            return record
        return self.store.transaction(apply)
