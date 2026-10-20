#!/usr/bin/env bash
# Build only published aictrl 0.5.4 against the frozen six-way campaign's matching base.
set -euo pipefail
BENCH=$(cd "$(dirname "$0")/.." && pwd)
IMAGEBASE=aictrl-harness-bench:base
IMAGE=aictrl-harness-bench:aictrl-npm-0.5.4
OUT=$BENCH/results/build-aictrl-0.5.4
expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["aictrl-npm"]["matchingBaseId"])' "$BENCH/results/build-images.json")
actual=$(docker image inspect -f '{{.Id}}' "$IMAGEBASE")
[[ "$actual" == "$expected" ]] || { echo 'Frozen matching base image ID mismatch' >&2; exit 1; }
npm view @aictrl/cli@0.5.4 --json > "$OUT-npm.json"
npm view @aictrl/cli-linux-x64-baseline@0.5.4 --json > "$OUT-linux-x64-baseline-npm.json"
npm view @aictrl/cli-linux-x64-baseline-musl@0.5.4 --json > "$OUT-linux-x64-baseline-musl-npm.json"
docker build --progress=plain --build-arg "BASE=$IMAGEBASE" --build-arg PKG=@aictrl/cli@0.5.4 -t "$IMAGE" -f "$BENCH/docker/npm.Dockerfile" "$BENCH/docker" > "$OUT.log" 2>&1
python3 - "$BENCH" "$IMAGEBASE" "$IMAGE" <<'PY'
import datetime,hashlib,json,os,pathlib,subprocess,sys
bench,base,image=sys.argv[1:]; stem=bench+'/results/build-aictrl-0.5.4'
def out(*args): return subprocess.check_output(args,text=True).strip()
def run(image,*args): return out('docker','run','--rm','--network','none',image,*args)
def inspect(image): return json.loads(out('docker','image','inspect',image))[0]
old=json.load(open(bench+'/results/build-images.json'))['aictrl-npm'];b=inspect(base);i=inspect(image)
assert b['Id']==old['matchingBaseId'],'Frozen matching base image ID changed'
frozen=json.load(open(bench+'/results/build-images.json'))
frozenids={name:inspect(row['tag'])['Id'] for name,row in frozen.items()}
assert all(frozenids[name]==row['imageId'] for name,row in frozen.items()),'Frozen contender image ID changed'
fixturejs='''const fs=require('fs'),crypto=require('crypto');const paths=['notes.txt','big.txt',...Array.from({length:3},(_,i)=>`notes-${i}.txt`),...Array.from({length:50},(_,i)=>`big-${i}.txt`)];console.log(JSON.stringify({uid:process.getuid(),homeEntries:fs.readdirSync(process.env.HOME),fixtures:Object.fromEntries(paths.map(p=>{const b=fs.readFileSync('/workspace/'+p);return[p,{bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')}]}))}));'''
a=json.loads(run(image,'node','-e',fixturejs));expected=json.loads(run(base,'node','-e',fixturejs))
assert a==expected,'Fixture or initial user/HOME differs from frozen matching base'
assert a['uid']==10001 and a['homeEntries']==[]
assert len(a['fixtures'])==55
for name,f in a['fixtures'].items(): assert f['bytes']==(340 if name.startswith('notes') else 48000)
platformjs='''const fs=require('fs'),root='/usr/local/lib/node_modules/@aictrl/cli',p=JSON.parse(fs.readFileSync(root+'/package.json'));const scope=root+'/node_modules/@aictrl';console.log(JSON.stringify({main:{name:p.name,version:p.version},platformPackages:fs.readdirSync(scope).map(n=>{const path=scope+'/'+n,j=JSON.parse(fs.readFileSync(path+'/package.json')),binaryPath=path+'/bin/aictrl';return {name:j.name,version:j.version,os:j.os??null,cpu:j.cpu??null,libc:j.libc??null,path,binaryPath,binaryBytes:fs.statSync(binaryPath).size}})}));'''
p=json.loads(run(image,'node','-e',platformjs));assert p['main']['version']=='0.5.4'
assert [x['name'] for x in p['platformPackages']]==['@aictrl/cli-linux-x64-baseline'],'Expected npm libc filtering to retain only glibc package'
assert p['platformPackages'][0]['libc']==['glibc']
for pkg in p['platformPackages']:
 assert pkg['version']=='0.5.4'
 pkg['installedBytes']=int(run(image,'du','-sb',pkg['path']).split()[0])
 pkg['binarySha256']=run(image,'sha256sum',pkg['binaryPath']).split()[0]
installed=int(run(image,'du','-sb','/usr/local/lib/node_modules/@aictrl/cli').split()[0])
wrapper=run(image,'aictrl','--version');native=run(image,'/usr/local/lib/node_modules/@aictrl/cli/node_modules/@aictrl/cli-linux-x64-baseline/bin/aictrl','--version')
assert wrapper=='0.5.4' and native=='0.5.4'
helptext=run(image,'aictrl','--help');assert 'aictrl' in helptext
pathlib.Path(stem+'-version.txt').write_text('npm wrapper: '+wrapper+'\nnative glibc baseline: '+native+'\n')
pathlib.Path(stem+'-help-smoke.txt').write_text(helptext+'\n')
published=json.load(open(stem+'-npm.json'))
record={'capturedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tag':image,'imageId':i['Id'],'matchingBase':base,'matchingBaseId':b['Id'],'matchingBaseBytes':b['Size'],'totalImageBytes':i['Size'],'imageDeltaBytes':i['Size']-b['Size'],'imageDeltaMiB':(i['Size']-b['Size'])/1048576,'installedTotalBytes':installed,'installedPathsBytes':{'/usr/local/lib/node_modules/@aictrl/cli':installed},'executionEngine':'bundled Bun native binary, npm Node launcher','containerNodeVersion':run(image,'node','--version'),'containerNpmVersion':run(image,'npm','--version'),'runtime':run(image,'node','--version'),'toolVersion':wrapper,'frozenImageIdsUnchanged':frozenids,'npmWrapperVersion':wrapper,'nativeGlibcBaselineVersion':native,'publishedPackage':{k:published.get(k) for k in ['name','version','dist','optionalDependencies']},'installedPackages':p,'fixtureContract':a,'networkNoneSmokePassed':True,'frozenMetadataSha256':hashlib.sha256(pathlib.Path(bench+'/results/build-images.json').read_bytes()).hexdigest(),'npmDockerfileSha256':hashlib.sha256(pathlib.Path(bench+'/docker/npm.Dockerfile').read_bytes()).hexdigest(),'filesystemFreeBytes':os.statvfs(bench).f_bavail*os.statvfs(bench).f_frsize}
json.dump(record,open(stem+'.json','w'),indent=2)
print(json.dumps({k:record[k] for k in ['tag','imageId','totalImageBytes','imageDeltaMiB','installedTotalBytes','npmWrapperVersion','nativeGlibcBaselineVersion','filesystemFreeBytes']},indent=2))
PY
