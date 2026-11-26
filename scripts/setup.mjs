import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {root} from '../src/settings.mjs';
const start=performance.now(), runtime=path.join(root,'.runtime'), deps=path.join(runtime,'deps');
function run(bin,args,cwd=root){const r=spawnSync(bin,args,{cwd,encoding:'utf8',timeout:300000,maxBuffer:8000000,env:{...process.env,GIT_TERMINAL_PROMPT:'0'}});if(r.error||r.status!==0)throw Error(`${bin} ${args[0]} failed: ${r.error?.message||r.stderr.slice(-2000)}`);return r.stdout.trim();}
if(!['darwin','linux'].includes(process.platform))throw Error('Use macOS, Linux, or WSL.');
const [major,minor,patch]=process.versions.node.split('.').map(Number);
if(major!==26||minor<12||(minor===12&&patch<1))throw Error('Node 26.12.1 or later 26.x required.');
run('python3',['-c','import sys; assert sys.version_info >= (3,10)']);
function directory(p,create=false){
 const entry=fs.lstatSync(p,{throwIfNoEntry:false});
 if(entry&&!entry.isDirectory())throw Error('Expected a plain setup directory');
 if(!entry&&create)fs.mkdirSync(p,{mode:0o700});
 return !!entry;
}
for(const p of [runtime,deps])directory(p,true);
const guard=path.join(runtime,'setup.lock');fs.mkdirSync(guard);
try {
 const lock=JSON.parse(fs.readFileSync(path.join(root,'sources.lock.json')));
 for(const [name,s] of Object.entries(lock.repositories)){
  if(!/^[a-z0-9-]+$/.test(name)||s.url!==`https://github.com/kujolang/${name}.git`||!/^[a-f0-9]{40}$/.test(s.commit))throw Error('Invalid source pin');
  const dest=path.join(deps,name);
  if(!directory(dest)){
   const stage=fs.mkdtempSync(path.join(deps,'.install-'));
   try{
    run('git',['init','-q',stage]);
    run('git',['remote','add','origin',s.url],stage);
    run('git',['-c','credential.helper=','fetch','--depth=1','origin',s.commit],stage);
    const fetched=run('git',['rev-parse','FETCH_HEAD'],stage);
    if(fetched!==s.commit)throw Error(`${name} fetch differs from its pin`);
    run('git',['checkout','--detach',fetched],stage);
    fs.renameSync(stage,dest);
   }finally{if(fs.existsSync(stage))fs.rmSync(stage,{recursive:true,force:true});}
  }
  if(run('git',['rev-parse','--show-toplevel'],dest)!==dest||run('git',['rev-parse','HEAD'],dest)!==s.commit||run('git',['status','--porcelain','--untracked-files=all'],dest))throw Error(`${name} differs from its pin or has local edits; preserve and move it aside before setup.`);
  console.log(`${name}: verified`);
 }
 const binary=createRequire(import.meta.url)('@kujolang/kujo-runtime').resolveKujoBinary();
 for(const dir of ['kujo','kujo/target','kujo/target/release'])directory(path.join(deps,dir),true);
 const target=path.join(deps,'kujo/target/release/kujo');
 if(!fs.lstatSync(target,{throwIfNoEntry:false}))fs.symlinkSync(binary,target);
 if(fs.realpathSync(target)!==fs.realpathSync(binary))throw Error('Unexpected Kujo runtime link');
 run('python3',['src/factory.py','doctor']);
 const receipt=path.join(guard,'receipt.json');
 fs.writeFileSync(receipt,JSON.stringify({ok:true,durationMs:Math.round(performance.now()-start),finishedAt:new Date().toISOString(),sources:lock.repositories,providerCalls:0},null,2)+'\n',{flag:'wx',mode:0o600});
 try{fs.renameSync(receipt,path.join(runtime,'setup-receipt.json'));}
 finally{if(fs.existsSync(receipt))fs.unlinkSync(receipt);}
 console.log('Ready for local work. Run npm run login before live model calls.');
}finally{fs.rmdirSync(guard);}
