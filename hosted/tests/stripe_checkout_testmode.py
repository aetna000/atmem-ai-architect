"""Operator-invoked Stripe TEST-only acceptance harness, never unittest discovery.

Requires an explicitly approved Stripe CLI account and local Firestore emulator.
Starts a loopback webhook receiver and Stripe CLI forwarding. Creates one unpaid
test Checkout; the operator/browser completes it using Stripe's test card. Never
loads or uses live-mode credentials. Ctrl-C stops only processes started here.
"""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
import tomllib
import uuid

from google.cloud import firestore
import uvicorn
from hosted.api import create_app, Services
from hosted.auth import FirebaseIdentity
from hosted.configuration import BillingConfiguration
from hosted.credits import CreditLedger
from hosted.firestore_store import FirestoreTransactions
from hosted.payments import CheckoutOrders, StripeCheckout


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--account',required=True)
    parser.add_argument('--state-file',required=True)
    parser.add_argument('--port',type=int,default=8898)
    parser.add_argument('--icon-file')
    args=parser.parse_args()
    if os.environ.get('FIRESTORE_EMULATOR_HOST') != '127.0.0.1:8897':
        raise SystemExit('This harness requires its explicit local Firestore emulator on 127.0.0.1:8897')
    cli=tomllib.loads((Path.home()/'.config/stripe/config.toml').read_text())['default']
    if cli.get('account_id') != args.account: raise SystemExit('Stripe CLI account differs from the approved test account')
    key=cli['test_mode_api_key']
    if not key.startswith('sk_test_'): raise SystemExit('Only a Stripe test secret key is accepted')
    fd,log_path=tempfile.mkstemp(prefix='architect-stripe-listener-',suffix='.log')
    os.chmod(log_path,0o600)
    listener=None;server=None;client=None
    try:
        with os.fdopen(fd,'w') as log:
            listener=subprocess.Popen(['stripe','listen','--events','checkout.session.completed,checkout.session.async_payment_succeeded,charge.refunded',
                '--forward-to',f'http://127.0.0.1:{args.port}/api/ai-architect/stripe/webhook'],stdout=log,stderr=log)
            deadline=time.monotonic()+30;secret=None
            while time.monotonic()<deadline:
                match=re.search(r'whsec_[A-Za-z0-9]+',Path(log_path).read_text())
                if match: secret=match.group();break
                if listener.poll() is not None:raise RuntimeError('Stripe CLI listener failed; inspect its private log locally')
                time.sleep(.25)
            if not secret:raise RuntimeError('Stripe CLI listener did not become ready')
            provider=StripeCheckout(key,secret,live=False,
                                    icon={'type':'file','file':args.icon_file} if args.icon_file else None)
            client=firestore.Client(project='demo-architect-hosted')
            namespace='stripe_'+uuid.uuid4().hex[:16]
            store=FirestoreTransactions(client,namespace=namespace)
            ledger=CreditLedger(store,welcome_units=5_000_000,policy_version='stripe-test-only')
            uid='test-'+uuid.uuid4().hex;ledger.register(uid)
            orders=CheckoutOrders(store,ledger,BillingConfiguration(store),provider,
                                   return_url='https://atmem.ai/ai-architect/workspace/account/')
            # Real Firebase verifier, no unsigned-token fixture or public auth bypass.
            # Only signature-authenticated Stripe notifications are used by this test.
            app=create_app(Services(store,FirebaseIdentity('atmemai'),orders))
            server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_level='warning',access_log=False))
            thread=threading.Thread(target=server.run,daemon=True);thread.start()
            deadline=time.monotonic()+10
            while not server.started and time.monotonic()<deadline:time.sleep(.1)
            if not server.started:raise RuntimeError('Local webhook receiver did not start')
            order=orders.create(uid,'checkout-test',137)
            state=dict(account=args.account,live=False,namespace=namespace,uid=uid,orderId=order['id'],
                       checkoutUrl=order['url'],initialBalanceMicros=5_000_000,amountCents=137,
                       verification='awaiting_test_payment',webhookPort=args.port)
            target=Path(args.state_file)
            with target.open('w') as output:os.chmod(target,0o600);json.dump(state,output,indent=2)
            print(json.dumps({'testCheckoutCreated':True,'stateFile':str(target),'live':False}),flush=True)
            deadline=time.monotonic()+900
            while time.monotonic()<deadline:
                if ledger.account(uid)['available']==6_370_000:break
                time.sleep(1)
            else:raise RuntimeError('Test checkout was not fulfilled before timeout')
            sid=store.transaction(lambda tx:tx.get('orders',order['id']))['sessionId']
            orders.fulfill(sid);orders.fulfill(sid)
            if ledger.account(uid)['available']!=6_370_000:raise RuntimeError('Duplicate fulfillment changed the balance')
            paid=provider.retrieve(sid);payment=paid['payment_intent']['id']
            refund=provider.client.v1.refunds.create({'payment_intent':payment,'amount':37},
                      options={'idempotency_key':'architect-test-refund-'+order['id']}).to_dict()
            if refund.get('livemode') is True:raise RuntimeError('Unexpected live refund response')
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                if ledger.account(uid)['available']==6_000_000:break
                time.sleep(1)
            else:raise RuntimeError('Verified refund webhook did not reconcile')
            orders.fulfill(sid)
            if ledger.account(uid)['available']!=6_000_000:raise RuntimeError('Refund replay changed the balance')
            state.update(verification='passed',finalBalanceMicros=6_000_000,
                evidence=['Real Stripe test-mode Checkout completed','Real signed payment webhook credited exactly USD1.37',
                          'Repeated fulfillment did not mint credits','Real USD0.37 test refund webhook reduced balance once'],
                sessionId=sid,paymentIntent=payment)
            target.write_text(json.dumps(state,indent=2)+'\n')
            print(json.dumps({'verification':'passed','testMode':True,'paymentWebhook':True,'refundWebhook':True}),flush=True)
    finally:
        if server:server.should_exit=True
        if listener and listener.poll() is None:
            listener.send_signal(signal.SIGINT)
            try:listener.wait(timeout=5)
            except subprocess.TimeoutExpired:listener.terminate()
        if client:client.close()
        # The private CLI log includes its signing secret. It is not an artifact.
        Path(log_path).unlink(missing_ok=True)


if __name__=='__main__': main()
