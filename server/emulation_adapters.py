"""Version-scoped repairs for observed emulator defects, never application bypasses."""
from contextlib import contextmanager

PATCH={'id':'moto-s3-notification-version-id-v1','motoVersion':'5.2.5','reason':'Moto drops versionId from S3 notifications although its exact event key retains version_id.','reference':'https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html','scope':'Add only the exact triggering key version; do not look up current/latest objects or alter generated handlers.'}

@contextmanager
def s3_version_notifications():
    import moto
    from moto.s3 import notifications
    if moto.__version__!=PATCH['motoVersion']:raise RuntimeError('Unqualified Moto version; revalidate adapter before upgrading')
    original=notifications._get_s3_event
    def event_with_version(event_name,bucket,key,notification_id):
        event=original(event_name,bucket,key,notification_id)
        version=getattr(key,'version_id',None)
        if version and version!='null':
            for record in event['Records']:record['s3']['object'].setdefault('versionId',version)
        return event
    notifications._get_s3_event=event_with_version
    try:yield PATCH
    finally:notifications._get_s3_event=original
