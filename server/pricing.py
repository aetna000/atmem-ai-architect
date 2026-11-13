"""Bounded public AWS price-list lookup, never model-generated price numbers."""
from datetime import datetime, timezone
import json
import re
import urllib.request
from functools import lru_cache
import time


def parse_s3(data, region, url):
    matches=[]
    for sku, product in data.get('products',{}).items():
        attrs=product.get('attributes',{})
        if product.get('productFamily') != 'Storage' or attrs.get('volumeType') != 'Standard' or attrs.get('regionCode') != region or attrs.get('locationType') != 'AWS Region': continue
        for term in data.get('terms',{}).get('OnDemand',{}).get(sku,{}).values():
            for rate in term.get('priceDimensions',{}).values():
                if rate.get('unit')=='GB-Mo' and rate.get('beginRange')=='0' and rate.get('endRange')=='51200':
                    price=float(rate.get('pricePerUnit',{}).get('USD','nan'))
                    if price >= 0 and price < 10:
                        matches.append({'price':price,'currency':'USD','unit':'GB-month','region':region,'service':'Amazon S3 Standard / '+sku,'source':'AWS public Price List','url':url,'date':datetime.now(timezone.utc).date().isoformat(),'publicationDate':data.get('publicationDate'),'description':rate.get('description'),'tierLimit':51200,'coverage':'S3 Standard storage, first 50 TB/month only; excludes requests, transfer, taxes and discounts'})
    if len(matches)!=1: raise ValueError('Could not uniquely identify S3 Standard storage pricing for this region')
    return matches[0]


@lru_cache(maxsize=32)
def _fetch(region, hour):
    url=f'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/{region}/index.json'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AtMem AI Architect/0.2'}),timeout=12) as response:
        raw=response.read(12_000_001)
    if len(raw)>12_000_000: raise ValueError('Price list exceeds the supported size')
    return parse_s3(json.loads(raw),region,url)


def aws_s3(region):
    if not re.fullmatch(r'[a-z]{2}-(?:gov-)?[a-z]+-\d',region):
        raise ValueError('Select an explicit AWS region such as ap-southeast-2 before fetching pricing')
    return dict(_fetch(region,int(time.time()//3600)))

PROVIDER_PAGES = {
 'aws':'https://aws.amazon.com/s3/pricing/',
 'azure':'https://azure.microsoft.com/pricing/details/storage/blobs/',
 'gcp':'https://cloud.google.com/storage/pricing',
 'ibm':'https://www.ibm.com/products/cloud-object-storage/pricing',
}

@lru_cache(maxsize=32)
def _azure_storage(region,hour):
    from urllib.parse import urlencode
    if not re.fullmatch(r'[a-z0-9]{3,40}',region):raise ValueError('Select an Azure region code')
    query="serviceName eq 'Storage' and armRegionName eq '"+region+"' and meterName eq 'Hot LRS Data Stored' and priceType eq 'Consumption' and productName eq 'Blob Storage'"
    url='https://prices.azure.com/api/retail/prices?'+urlencode({'$filter':query})
    with urllib.request.urlopen(url,timeout=12) as response:data=json.loads(response.read(2_000_000))
    matches=[r for r in data.get('Items',[]) if r.get('armRegionName')==region and r.get('productName')=='Blob Storage' and r.get('meterName')=='Hot LRS Data Stored' and r.get('tierMinimumUnits')==0 and r.get('currencyCode')=='USD' and r.get('unitOfMeasure')=='1 GB/Month']
    if len(matches)!=1:raise ValueError('No unique matching Azure meter')
    r=matches[0]
    return {'available':True,'provider':'azure','price':r['retailPrice'],'currency':'USD','unit':'GB-month','region':region,'service':'Azure Blob Storage Hot LRS / '+r['skuId'],'source':'Azure Retail Prices API','url':url,'date':datetime.now(timezone.utc).date().isoformat(),'tierLimit':51200,'coverage':'Hot LRS base storage tier only; operations, transfer, redundancy alternatives, taxes and discounts excluded'}


def storage_quote(provider,region):
    if provider not in PROVIDER_PAGES:raise ValueError('Choose AWS, Azure, Google Cloud or IBM')
    if provider=='aws':return {**aws_s3(region),'provider':'aws','available':True}
    if provider=='azure':return dict(_azure_storage(region,int(time.time()//3600)))
    if provider=='gcp':
        if region=='us-central1':
            try:return dict(_google_storage_public(region,int(time.time()//3600)))
            except (ValueError,OSError):pass
        import os
        key=os.getenv('GOOGLE_CLOUD_BILLING_API_KEY')
        if key and re.fullmatch(r'[a-z]+-[a-z]+\d',region):
            # Official catalogue; caller supplies the standard API key in server environment only.
            url='https://cloudbilling.googleapis.com/v1/services/95FF-2EF5-5EA1/skus?currencyCode=USD'
            request=urllib.request.Request(url,headers={'X-Goog-Api-Key':key})
            with urllib.request.urlopen(request,timeout=12) as response:data=json.loads(response.read(8_000_000))
            candidates=[]
            for sku in data.get('skus',[]):
                description=sku.get('description','')
                if region not in sku.get('serviceRegions',[]) or 'Standard Storage' not in description or 'Dual' in description or 'Multi' in description:continue
                for info in sku.get('pricingInfo',[])[:1]:
                    expression=info.get('pricingExpression',{})
                    if expression.get('usageUnit')!='GiBy.mo':continue
                    rates=expression.get('tieredRates',[])
                    if len(rates)!=1 or rates[0].get('startUsageAmount',0)!=0:continue
                    price=rates[0]['unitPrice'];value=float(price.get('units',0))+float(price.get('nanos',0))/1e9
                    candidates.append({'available':True,'provider':'gcp','price':value,'currency':'USD','unit':'GiB-month','region':region,'service':'Google Cloud Storage Standard / '+sku['skuId'],'source':'Google Cloud Billing Catalog','url':'https://cloud.google.com/skus/?currency=USD','date':datetime.now(timezone.utc).date().isoformat(),'coverage':'Standard storage only; operations, replication and transfer excluded'})
            if len(candidates)==1:return candidates[0]
        return {'available':False,'provider':'gcp','region':region,'sourceUrl':PROVIDER_PAGES[provider],'reason':f'Storage pricing for {region or "the selected region"} could not be verified. Recalculate or enter a sourced rate.','nextQuestion':'Which Google Cloud region and storage class should we price?'}
    return {'available':False,'provider':'ibm','region':region,'sourceUrl':PROVIDER_PAGES[provider],'reason':'IBM pricing depends on region, storage class and plan. No verified regional quote is configured; no AWS or invented rate is substituted.','nextQuestion':'Which IBM region and storage class or existing IBM quote should we use?'}


def parse_lambda(data,region,url,architecture='x86_64'):
    """Regional on-demand base meters; never apply account-specific free tiers."""
    suffix='-ARM' if architecture=='arm64' else ''
    expected={'requests':('AWS-Lambda-Requests'+suffix,'Request'),
              'compute':('AWS-Lambda-Duration'+suffix,'Lambda-GB-Second')}
    meters={}
    for name,(group,unit)in expected.items():
        matches=[]
        for sku,product in data.get('products',{}).items():
            attrs=product.get('attributes',{})
            if attrs.get('regionCode')!=region or attrs.get('group')!=group:continue
            for term in data.get('terms',{}).get('OnDemand',{}).get(sku,{}).values():
                for rate in term.get('priceDimensions',{}).values():
                    if rate.get('unit')!=unit or rate.get('beginRange')!='0':continue
                    value=float(rate.get('pricePerUnit',{}).get('USD','nan'))
                    if not 0<value<1:continue
                    end=rate.get('endRange')
                    matches.append({'price':value,'unit':unit,'service':'AWS Lambda / '+sku,
                                    'tierLimit':None if end=='Inf'else float(end)})
        if len(matches)!=1:raise ValueError('Could not uniquely verify the regional Lambda meter')
        meters[name]=matches[0]
    return {'available':True,'provider':'aws','region':region,'architecture':architecture,
            'currency':'USD','source':'AWS public Price List','url':url,
            'date':datetime.now(timezone.utc).date().isoformat(),'publicationDate':data.get('publicationDate'),
            'meters':meters,'coverage':'On-demand requests and base compute only. Free tiers, logs, transfer, public gateway charges, provisioned concurrency, taxes and discounts are not included.'}


@lru_cache(maxsize=32)
def _lambda(region,architecture,hour):
    url=f'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSLambda/current/{region}/index.json'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AtMem AI Architect/0.2'}),timeout=12)as response:raw=response.read(12_000_001)
    if len(raw)>12_000_000:raise ValueError('Price list exceeds the supported size')
    return parse_lambda(json.loads(raw),region,url,architecture)


def lambda_quote(region,architecture='x86_64'):
    if not re.fullmatch(r'[a-z]{2}-(?:gov-)?[a-z]+-\d',region)or architecture not in {'x86_64','arm64'}:
        raise ValueError('Select an explicit AWS region and Lambda architecture')
    return dict(_lambda(region,architecture,int(time.time()//3600)))


def _public_rows(html):
    from html.parser import HTMLParser
    class Rows(HTMLParser):
        def __init__(self):
            super().__init__();self.rows=[];self.row=None;self.cell=None
        def handle_starttag(self,tag,attrs):
            if tag=='tr':self.row=[]
            if tag in {'td','th'} and self.row is not None:self.cell=[]
        def handle_data(self,data):
            if self.cell is not None:self.cell.append(data)
        def handle_endtag(self,tag):
            if tag in {'td','th'} and self.cell is not None:
                self.row.append(' '.join(' '.join(self.cell).split()));self.cell=None
            if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
    parser=Rows();parser.feed(html);return parser.rows


def parse_google_public(html,service,url):
    import hashlib
    if service=='cloud-run':
        marker='Services (Requests-based billing)'
        if marker not in html:raise ValueError('Cloud Run request-based pricing section is missing')
        html=html[html.index(marker):]
        expected={'cpu':'CPU (per vCPU-second)','memory':'Memory (per GiB-second)','requests':'Requests (per 1,000,000)'}
        units={'cpu':'vCPU-seconds','memory':'GiB-seconds','requests':'million requests'}
    elif service=='cloud-sql':
        if 'Iowa (us-central1)' not in html or 'Enterprise Edition - N4' not in html:
            raise ValueError('Cloud SQL reference region or edition is missing')
        marker='Enterprise Edition - N4';html=html[html.index(marker):]
        expected={'cpu':'vCPUs','memory':'Memory'};units={'cpu':'vCPU-hours','memory':'GiB-hours'}
    else:raise ValueError('Unsupported Google pricing service')
    meters={}
    for row in _public_rows(html):
        if not row:continue
        for key,label in expected.items():
            if key in meters or row[0]!=label:continue
            value=next((re.search(r'\$([0-9]+(?:\.[0-9]+)?)',cell)for cell in row[1:]if '$' in cell),None)
            if value:
                price=float(value.group(1))
                if not 0<price<10:raise ValueError('Unexpected Google public price')
                meters[key]={'price':price,'unit':units[key]}
        if len(meters)==len(expected):break
    if len(meters)!=len(expected):raise ValueError('Google public pricing meters could not be verified')
    return {'available':True,'provider':'gcp','service':service,'region':'us-central1','currency':'USD',
            'source':'Google Cloud public pricing','url':url,'date':datetime.now(timezone.utc).date().isoformat(),
            'sourceSha256':hashlib.sha256(html.encode()).hexdigest(),'meters':meters,
            'coverage':'US reference on-demand rates. Excludes free tiers, commitments, taxes, networking, backups, storage, external APIs and payment fees.'}


@lru_cache(maxsize=8)
def _google_public(service,hour):
    path={'cloud-run':'run','cloud-sql':'sql'}.get(service)
    if not path:raise ValueError('Unsupported Google pricing service')
    url=f'https://cloud.google.com/{path}/pricing'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AtMem Architect pricing'}),timeout=15)as response:raw=response.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError('Google price page exceeds its size bound')
    return parse_google_public(raw.decode('utf-8'),service,url)


def google_public_quote(service,region,planning_reference=False):
    if region!='us-central1' and not (planning_reference and (not region or re.search('select|unknown|tbd',region,re.I))):
        raise ValueError('This public quote supports Iowa only; the selected region is preserved.')
    return {**_google_public(service,int(time.time()//3600)),'planningReference':region!='us-central1'}


def parse_google_storage_public(html, region, url):
    """Read an explicitly selected single-region public table, never a region list match."""
    import hashlib
    from html.parser import HTMLParser
    if region != 'us-central1':
        raise ValueError('The public default storage table verifies Iowa only.')
    marker = 'id="data-storage"'
    if marker not in html:
        raise ValueError('Google data storage section is missing.')
    section = html[html.index(marker):]
    # Stop before dual-region rates. Region options alone do not verify selected pricing.
    boundary = re.search(r'<(?:p|h[1-6])[^>]*>\s*(?:<b>)?Dual-region(?:</b>)?\s*</', section)
    if not boundary:
        raise ValueError('The single-region storage boundary is missing.')
    section = section[:boundary.start()]
    class Selected(HTMLParser):
        def __init__(self):super().__init__();self.regions=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if a.get('role')=='option' and a.get('aria-selected')=='true':self.regions.append(a.get('data-value'))
    selected=Selected();selected.feed(section)
    if selected.regions != ['Iowa (us-central1)']:
        raise ValueError('The selected public storage region is not Iowa.')
    table = re.search(r'<table\b[^>]*>.*?</table>', section, re.S)
    rows = _public_rows(table.group(0)) if table else []
    if len(rows)!=2 or rows[0].count('Standard storage')!=1:
        raise ValueError('The Standard storage table could not be verified.')
    index=rows[0].index('Standard storage')
    if index>=len(rows[1]):raise ValueError('The storage price is missing.')
    cell=rows[1][index]
    rate=re.fullmatch(r'\$([0-9]+(?:\.[0-9]+)?) / 1 gibibyte hour(?:, per 1 month / account)?',cell)
    if not rate or not 0<float(rate.group(1))<1:raise ValueError('Unexpected Google storage rate or unit.')
    hourly=float(rate.group(1))
    return {'available':True,'provider':'gcp','price':hourly*730,'currency':'USD',
            'unit':'GiB-month','region':region,'service':'Cloud Storage Standard / single-region',
            'source':'Google Cloud public pricing','url':url,
            'date':datetime.now(timezone.utc).date().isoformat(),
            'sourceSha256':hashlib.sha256(section.encode()).hexdigest(),
            'hourlyPrice':hourly,'hoursPerMonth':730,
            'coverage':'Single-region Standard storage; 730-hour planning month. Operations, replication, transfer, taxes and discounts excluded.'}


@lru_cache(maxsize=32)
def _google_storage_public(region,hour):
    url='https://cloud.google.com/storage/pricing'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AtMem Architect pricing'}),timeout=12) as response:
        raw=response.read(8_000_001)
    if len(raw)>8_000_000:raise ValueError('Google storage page exceeds its size bound.')
    return parse_google_storage_public(raw.decode('utf-8'),region,url)
