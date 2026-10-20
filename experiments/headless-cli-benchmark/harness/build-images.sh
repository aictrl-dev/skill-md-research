#!/usr/bin/env bash
# Pinned public releases; all installs happen before measurements. No model/API calls.
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
PREFIX=${BENCH_IMAGE_PREFIX:-aictrl-harness-bench}
NODE20_IMAGE=${BENCH_NODE20_IMAGE:-node:20-slim}
NODE22_IMAGE=${BENCH_NODE22_IMAGE:-node:22-slim}
PYTHON_IMAGE=${BENCH_PYTHON_IMAGE:-python:3.14-slim}
mkdir -p "$HERE/results" "$HERE/build"
CTX=$(mktemp -d "$HERE/build/images.XXXXXX")
trap 'rm -rf "$CTX"' EXIT
build() {
  local name=$1; shift
  docker build --progress=plain -t "$PREFIX:$name" "$@" >"$HERE/results/build-$name.log" 2>&1 || {
    tail -60 "$HERE/results/build-$name.log" >&2; return 1;
  }
  echo "built $PREFIX:$name"
}
declare -A NPM=(
  [aictrl-npm]=@aictrl/cli@0.5.1
  [pi-1.3-node22]=@earendil-works/pi-coding-agent@1.3.0
  [codex]=@openai/codex@0.163.0
  [opencode]=opencode-ai@1.19.3
)
TOOLS=${*:-aictrl-npm pi-1.3-node22 codex opencode hermes goose}
build base --build-arg "NODE_IMAGE=$NODE20_IMAGE" -f "$HERE/docker/base.Dockerfile" "$HERE/docker"
build base22 --build-arg NODE_IMAGE=$NODE22_IMAGE -f "$HERE/docker/base.Dockerfile" "$HERE/docker"
build base-python314 --build-arg NODE_IMAGE=$PYTHON_IMAGE -f "$HERE/docker/base.Dockerfile" "$HERE/docker"
for tool in $TOOLS; do
  base=$PREFIX:base
  case "$tool" in
    hermes)
      gh repo clone NousResearch/hermes-agent "$CTX/hermes-checkout" -- --depth 1 --branch v0.22.2 > "$HERE/results/build-hermes-download.log" 2>&1
      test "$(git -C "$CTX/hermes-checkout" rev-parse HEAD)" = d923a5eb487a17c0a68801bba9ef0f56c81040a8
      git -C "$CTX/hermes-checkout" archive --format=tar.gz --prefix=hermes/ HEAD > "$CTX/hermes-source.tar.gz"
      rm -rf "$CTX/hermes-checkout"
      sha256sum "$CTX/hermes-source.tar.gz" > "$HERE/results/build-hermes-source.sha256"
      build hermes --build-arg "BASE=$PREFIX:base-python314" -f "$HERE/docker/hermes.Dockerfile" "$CTX"
      bin=hermes
      ;;
    goose)
      asset=goose-x86_64-unknown-linux-gnu.tar.gz
      gh release view v1.55.0 --repo aaif-goose/goose --json assets,tagName,targetCommitish > "$HERE/results/build-goose-release.json"
      gh release download v1.55.0 --repo aaif-goose/goose --pattern "$asset" --dir "$CTX"
      expected=$(python3 -c 'import json,sys; print(next(x["digest"].split(":")[1] for x in json.load(open(sys.argv[1]))["assets"] if x["name"]==sys.argv[2]))' "$HERE/results/build-goose-release.json" "$asset")
      printf '%s  %s\n' "$expected" "$CTX/$asset" | sha256sum -c -
      tar -xzf "$CTX/$asset" -C "$CTX"
      test -f "$CTX/goose"
      build goose --build-arg "BASE=$base" -f "$HERE/docker/goose.Dockerfile" "$CTX"
      bin=goose
      ;;
    *)
      [[ "$tool" == *node22 ]] && base=$PREFIX:base22
      build "$tool" --build-arg "BASE=$base" --build-arg "PKG=${NPM[$tool]}" -f "$HERE/docker/npm.Dockerfile" "$HERE/docker"
      bin=${tool%%-*}; [[ "$tool" == aictrl-npm ]] && bin=aictrl
      ;;
  esac
  docker run --network none --rm "$PREFIX:$tool" "$bin" --version > "$HERE/results/build-$tool-version.txt" 2>&1 || {
    cat "$HERE/results/build-$tool-version.txt" >&2; exit 1;
  }
  docker run --rm "$PREFIX:$tool" sh -c 'test "$(wc -c < /workspace/big.txt)" = 48000 && test "$(id -u)" = 10001 && test -z "$(ls -A "$HOME")"' || exit 1
  if [[ "$tool" == hermes ]]; then docker run --network none --rm "$PREFIX:hermes" cat /usr/local/share/hermes-pip-freeze.txt > "$HERE/results/build-hermes-pip-freeze.txt"; fi
  echo "ready $tool: $(tr '\n' ' ' < "$HERE/results/build-$tool-version.txt")"
done
# Equal-payload indexed fixtures avoid path-keyed duplicate-read guards.
for fixturetool in base base22 base-python314 aictrl-npm pi-1.3-node22 codex opencode hermes goose; do
  tag=$PREFIX:$fixturetool
  if ! docker image inspect "$tag" >/dev/null 2>&1; then echo "fixture layer: $tag not requested/built"; continue; fi
  if docker run --network none --rm "$tag" test -f /workspace/big-49.txt; then continue; fi
  docker build --progress=plain --build-arg "BASE=$tag" -t "$tag" -f "$HERE/docker/fixtures.Dockerfile" "$HERE/docker" > "$HERE/results/build-fixtures-$fixturetool.log" 2>&1 || { tail -40 "$HERE/results/build-fixtures-$fixturetool.log" >&2; exit 1; }
  echo "indexed fixtures ready $fixturetool"
done
# Record safe provenance and footprint metadata (no environment values/credentials).
python3 - "$HERE" "$PREFIX" <<'PY'
import datetime,json,os,platform,re,subprocess,sys
root,prefix=sys.argv[1:]
def out(*args): return subprocess.check_output(args,text=True).strip()
def inspect(tag): return json.loads(out('docker','image','inspect',tag))[0]
def run(tag,cmd): return out('docker','run','--rm',tag,'sh','-c',cmd)
def upstream(name,log):
 m=re.search(r'FROM ([^\s]+@sha256:[a-f0-9]+)',open(root+'/results/build-'+log+'.log').read())
 return m.group(1) if m else inspect(name)['RepoDigests'][0]
rows={}
paths={'aictrl-npm':['/usr/local/lib/node_modules/@aictrl/cli'],'pi-1.3-node22':['/usr/local/lib/node_modules/@earendil-works/pi-coding-agent'],'codex':['/usr/local/lib/node_modules/@openai/codex'],'opencode':['/usr/local/lib/node_modules/opencode-ai'],'hermes':['/opt/hermes','/opt/hermes-venv'],'goose':['/usr/local/bin/goose']}
bases={'pi-1.3-node22':'base22','hermes':'base-python314'}
for name,p in paths.items():
 tag=prefix+':'+name
 try: i=inspect(tag)
 except subprocess.CalledProcessError: continue
 base=prefix+':'+bases.get(name,'base');b=inspect(base)
 sizes={x:int(run(tag,'du -sb '+x).split()[0]) for x in p}
 runtime='python --version' if name=='hermes' else 'node --version'
 engines={'aictrl-npm':'bundled Bun native binary, npm Node launcher','opencode':'bundled Bun native binary, npm Node launcher','codex':'native Codex binary, npm Node launcher','pi-1.3-node22':'Node.js','hermes':'CPython','goose':'native GNU/Linux CLI; shared-base Node is not its engine'}
 rows[name]={'tag':tag,'imageId':i['Id'],'imageRepoDigests':i['RepoDigests'],'matchingBase':base,'matchingBaseId':b['Id'],'totalImageBytes':i['Size'],'matchingBaseBytes':b['Size'],'imageDeltaBytes':i['Size']-b['Size'],'imageDeltaMiB':(i['Size']-b['Size'])/1048576,'installedPathsBytes':sizes,'installedTotalBytes':sum(sizes.values()),'runtime':run(tag,runtime),'executionEngine':engines[name],'toolVersion':open(root+'/results/build-'+name+'-version.txt').read().strip(),'fixtureBytes':48000,'fixtureContract':{'shortBytes':340,'longBytes':48000,'shortDistinctPaths':3,'longDistinctPaths':50,'identicalPayloadCopies':True},'homeInitiallyEmpty':True,'userId':10001}
 if name=='hermes': rows[name]['sourceCommit']='d923a5eb487a17c0a68801bba9ef0f56c81040a8';rows[name]['installProfile']='core only, no extras; source retained'
 if name=='goose':rows[name]['release']='v1.55.0';rows[name]['nativeLibraries']=run(tag,'cat /usr/local/share/goose-ldd.txt');rows[name]['installProfile']='native GNU release; Node20 matching base plus libxcb1 libdbus-1-3 libssl3'
 if name=='aictrl-npm':rows[name]['optionalPlatformPackages']=run(tag,'for x in /usr/local/lib/node_modules/@aictrl/cli/node_modules/@aictrl/*; do du -sb "$x"; done')
json.dump(rows,open(root+'/results/build-images.json','w'),indent=2)
d=json.loads(out('docker','info','--format','{{json .}}'));cpu=json.loads(out('lscpu','-J'))['lscpu'];cpu={x['field'].rstrip(':'):x['data'] for x in cpu}
json.dump({'capturedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hostKernel':platform.release(),'hostArchitecture':platform.machine(),'cpu':{k:cpu.get(k) for k in ['Model name','CPU(s)','Socket(s)','Core(s) per socket','Thread(s) per core']},'docker':{k:d.get(k) for k in ['ServerVersion','OperatingSystem','Architecture','KernelVersion','CgroupDriver','CgroupVersion','NCPU','MemTotal','Driver']},'filesystemFreeBytes':os.statvfs(root).f_bavail*os.statvfs(root).f_frsize,'upstreamImages':{name:upstream(name,log) for name,log in [('node:20-slim','base'),('node:22-slim','base22'),('python:3.14-slim','base-python314')]}},open(root+'/results/build-host.json','w'),indent=2)
PY
