// Trusted build-time provider inventory. No project files, credentials or generated Terraform are executed.
import {CLOUD_PROVIDER_LOCKS} from '../../src/cloud-provider-locks.mjs';
import {mkdir,writeFile,copyFile,readFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
const required={aws:{source:'hashicorp/aws',version:'~> 6.0'},google:{source:'hashicorp/google',version:'~> 7.0'},ibm:{source:'IBM-Cloud/ibm',version:'~> 1.0'},null:{source:'hashicorp/null',version:'~> 3.0'},random:{source:'hashicorp/random',version:'~> 3.0'},archive:{source:'hashicorp/archive',version:'~> 2.0'},time:{source:'hashicorp/time',version:'~> 0.0'}};
for(const lock of Object.values(CLOUD_PROVIDER_LOCKS))for(const match of lock.matchAll(/provider "registry\.terraform\.io\/([^"]+)"\s*\{\s*version\s*=\s*"([^"]+)"/g))required[match[1].split('/').at(-1)]={source:match[1],version:match[2]};
const folder='/opt/architect/provider-preparation',mirror='/opt/architect/provider-mirror';await mkdir(folder,{recursive:true});await mkdir(mirror,{recursive:true});
await writeFile(folder+'/versions.tf.json',JSON.stringify({terraform:{required_providers:required}},null,2)+'\n');
const environment={PATH:process.env.PATH,TF_IN_AUTOMATION:'1',CHECKPOINT_DISABLE:'1',AWS_EC2_METADATA_DISABLED:'true'};
for(const command of [['providers','lock','-platform=linux_amd64'],['providers','mirror','-platform=linux_amd64',mirror]]){
 const result=spawnSync('terraform',['-chdir='+folder,...command],{env:environment,stdio:'inherit',timeout:600000});if(result.status!==0)throw Error('Pinned provider preparation failed');
}
await copyFile(folder+'/.terraform.lock.hcl','/opt/architect/provider-mirror.lock.hcl');
await writeFile('/opt/architect/provider-inventory.json',JSON.stringify({kind:'Build-time official registry provider cache',required,lock:await readFile(folder+'/.terraform.lock.hcl','utf8'),cloudAccountAccess:false},null,2)+'\n');
