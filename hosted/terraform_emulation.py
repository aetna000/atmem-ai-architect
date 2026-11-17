"""Trusted controller for the same Terraform lifecycle inside a networkless container."""
import fcntl,hashlib,io,json,os,tempfile,zipfile
from pathlib import Path
from server.local_validation import DockerValidationWorker,ValidationSpec


def run_isolated(files, *, image, endpoint, progress=None):
    from server.terraform_emulation_routes import unavailable
    lock_path=Path(tempfile.gettempdir())/'atmem-terraform-emulation.lock'
    descriptor=os.open(lock_path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return unavailable('Another emulation is running. Retry shortly.',status='blocked')
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,content in files.items():archive.writestr(name,content)
        raw=stream.getvalue()
        spec=ValidationSpec('terraform-apply-emulation',image,
            ('/opt/architect/emulator/bin/python','-I','/opt/architect/hosted/deploy/emulate-terraform.py'),
            bootstrap_python='/opt/architect/emulator/bin/python',timeout_seconds=1500,
            isolation_profile='terraform-emulation-v1',executable_scratch=True)
        result=DockerValidationWorker(endpoint,max_output_bytes=4500000).run(raw,hashlib.sha256(raw).hexdigest(),spec,progress=progress)
        lines=[line[len('ATMEM_EMULATION_REPORT:'):] for line in result['output'].splitlines() if line.startswith('ATMEM_EMULATION_REPORT:')]
        if result.get('reason') or len(lines)!=1:
            return unavailable('Isolated emulation stopped without a complete report. No pass was recorded.',status='failed',sandbox={k:result.get(k) for k in ('imageId','status','reason','exitCode')})
        report=json.loads(lines[0])
        if report.get('status')=='passed' and result['status']!='passed':
            return unavailable('Container execution did not confirm the report. No pass was recorded.',status='failed')
        report['sandbox']={k:result[k] for k in ('imageId','platform','isolationProfile','durationSeconds','status')}
        return report
    finally:os.close(descriptor)
