// A root-only response from an older helper cannot certify a composed package.
export function moduleValidationCoverage(result,modules=[]){
 if(result?.status!=='passed'||!modules.length)return result;
 const checks=Array.isArray(result.checks)?result.checks:[];
 const missing=[];
 for(const unit of modules)for(const stage of ['init','validate','test']){
  const check=checks.find(c=>c.moduleId===unit.id&&c.modulePath===unit.path&&c.stage===stage&&c.passed===true);
  if(!check||stage==='test'&&(!Number.isSafeInteger(check.testsReported)||check.testsReported<1))missing.push({id:unit.id,path:unit.path,stage});
 }
 return missing.length?{...result,status:'incomplete',reportedStatus:result.status,missingModuleChecks:missing,message:'Root checks do not validate the complete composition: required delivery-unit schema or nonempty mock-test checks are missing.'}:result;
}
