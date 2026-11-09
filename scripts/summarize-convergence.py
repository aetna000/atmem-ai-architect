"""Aggregate observed cases without promoting missing or incomplete runs into passes."""
import argparse,collections,importlib.util,json
from pathlib import Path
module_path=Path(__file__).with_name('assess-convergence-package.py')
spec=importlib.util.spec_from_file_location('independent_package_assessor',module_path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def summarize(run):
    run=Path(run).resolve();results=[];services=collections.Counter();errors=collections.Counter()
    for case in sorted(run.glob('*/result.json')):
        row=json.loads(case.read_text());folder=case.parent
        independent=module.assess(folder)
        (folder/'independent-assessment.json').write_text(json.dumps(independent,indent=2)+'\n')
        if row.get('error'):errors[row['error']['type']]+=1
        export=folder/'export-assessment.json'
        if export.exists():
            package=json.loads(export.read_text())
            for resource in package.get('resourcePlan',{}).get('rows',[]):
                if not resource.get('implemented'):services[resource.get('service','unknown')]+=1
        results.append({'case':row['case'],'difficulty':row['difficulty'],'provider':row['provider'],'userExchanges':row['userExchanges'],'questions':row['clarificationQuestions'],'technicalQuestions':row['technicalQuestions'],'repeatedQuestions':row['repeatedQuestions'],'durationSeconds':row['durationSeconds'],'error':row.get('error'),'compilerStaticCandidate':row['package'].get('staticCandidate',False),'independentStaticChecksPassed':independent['staticChecksPassed'],'nearDeploymentQualified':False,'independentFindings':[f['code'] for f in independent['findings']]})
    manifest=json.loads((run/'manifest.json').read_text()) if (run/'manifest.json').exists() else {}
    expected=len(manifest.get('selectedCaseIds') or []) or 28
    report={'version':1,'fullMatrixCases':28,'expectedCases':expected,'completedCases':len(results),'remainingCases':max(0,expected-len(results)),'qualifiedCases':0,'evaluationComplete':len(results)==expected,'fullMatrixComplete':expected==28 and len(results)==28,'cloudOperations':False,'results':results,'missingServiceImplementations':dict(services.most_common()),'errors':dict(errors),'boundary':'Interaction results, emitted artifact integrity and static traceability. No runtime, semantic acceptance, account plan or deployment qualification is implied. The original frozen cases/results are unchanged.'}
    (run/'independent-summary.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');args=p.parse_args();r=summarize(args.run)
    print(json.dumps({k:v for k,v in r.items() if k!='results'},indent=2))
