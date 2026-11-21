// Only computed upstream identities/IDs are supplied. Never override the web-app
// configuration under test: its cross-field and ID validation must actually run.
export function azurePlanMocks({subscription,tenant,resourceGroup,addresses,entra=false}){
 const rg='/subscriptions/'+subscription+'/resourceGroups/'+resourceGroup;
 const guid=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
 let text=`mock_provider "azurerm" {\n override_during = plan\n mock_data "azurerm_client_config" { defaults = { subscription_id = "${subscription}", tenant_id = "${tenant}" } }\n}\n`;
 if(entra)text+='mock_provider "azuread" { override_during = plan }\n';
 const override=(target,values)=>{text+='override_resource {\n override_during = plan\n target = '+target+'\n values = '+JSON.stringify(values)+'\n}\n';};
 addresses.forEach((n,i)=>{
  const seed=100+i*10;
  override('azurerm_user_assigned_identity.'+n,{id:rg+'/providers/Microsoft.ManagedIdentity/userAssignedIdentities/mock-runtime-'+i,client_id:guid(seed),principal_id:guid(seed+1)});
  override('azurerm_service_plan.'+n,{id:rg+'/providers/Microsoft.Web/serverFarms/mock-plan-'+i});
  override('azurerm_cognitive_account.'+n,{id:rg+'/providers/Microsoft.CognitiveServices/accounts/mock-ai-'+i,endpoint:'https://mock-ai-'+i+'.openai.azure.com/'});
  if(entra){
   override('azuread_application_registration.'+n,{id:'/applications/'+guid(seed+2),client_id:guid(seed+3)});
   override('azuread_application_registration.'+n+'_spa',{id:'/applications/'+guid(seed+4),client_id:guid(seed+5)});
   override('azuread_service_principal.'+n,{object_id:guid(seed+6)});
  }else{
   const storage=rg+'/providers/Microsoft.Storage/storageAccounts/mockstorage'+i;
   override('azurerm_storage_account.'+n,{id:storage});
   override('azurerm_storage_container.'+n,{id:storage+'/blobServices/default/containers/public-catalog'});
  }
 });
 return text;
}
