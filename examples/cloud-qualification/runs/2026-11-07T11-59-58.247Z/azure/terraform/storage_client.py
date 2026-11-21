"""Generated object CRUD adapters. Configure an authenticated provider SDK separately.
Emulator injection is test-only; this file neither discovers credentials nor provisions resources.
"""
def azure_put(container,key,data):
    return container.upload_blob(key,data,overwrite=True)
def azure_get(container,key):
    return container.download_blob(key).readall()
def azure_delete(container,key):
    container.delete_blob(key,delete_snapshots='include')
def gcp_put(bucket,key,data,expected_generation=None):
    blob=bucket.blob(key)
    blob.upload_from_string(data,if_generation_match=expected_generation)
    return blob.generation
def gcp_get(bucket,key,generation=None):
    return bucket.blob(key,generation=generation).download_as_bytes()
def gcp_delete(bucket,key,generation=None):
    bucket.blob(key,generation=generation).delete()
def ibm_put(client,bucket,key,data):
    return client.put_object(Bucket=bucket,Key=key,Body=data)
def ibm_get(client,bucket,key,version=None):
    args={'Bucket':bucket,'Key':key}
    if version:args['VersionId']=version
    result=client.get_object(**args)
    try:return result['Body'].read()
    finally:result['Body'].close()
def ibm_delete(client,bucket,key,version):
    client.delete_object(Bucket=bucket,Key=key,VersionId=version)
