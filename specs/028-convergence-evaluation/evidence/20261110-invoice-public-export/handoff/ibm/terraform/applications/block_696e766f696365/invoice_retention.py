"""Invoice payload access expires independently of asynchronous physical cleanup."""
from datetime import datetime,timedelta,timezone

def retained(row):
    created=row.get('created_at')
    if isinstance(created,str):
        try:created=datetime.fromisoformat(created)
        except ValueError:return False
    if not isinstance(created,datetime)or created.tzinfo is None:return False
    now=datetime.now(timezone.utc)
    return now-timedelta(days=90)<created<=now+timedelta(minutes=5)

def current(row):
    from durable_workflow import Missing
    if not retained(row):raise Missing('Invoice retention period ended')
    return row
