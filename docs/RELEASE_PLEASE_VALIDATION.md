# Release-please migration validation

Recorded 2026-10-03 against main `7432169960f486040ac6ef23c3e355b9f4bea01e`
and these exact reviewed implementation snapshots:

- #655 adapters: `9952967b12a6b06270710fb4e05a6b91199f7499`.
- #656 configuration/workflows: `8b4dee606d7b556af55dc54a1d93c93d1d5106c7`.

The recorded checks below apply to those immutable revisions; PR numbers alone
are not validation evidence. Reruns must record their new tested SHAs. The migration changes no
published package version: the repository remains 1.8.0 until a separate
reviewed release PR is merged.

## Executed checks

- 109 focused offline tests passed: canonical composer, lifecycle reconciliation,
  release workflow contracts, release detection, legacy preparer and summary.
- Ruff check/format and `git diff --check` passed for changed Python files.
- Configuration and manifest validated against installed release-please 17.6.0
  schemas. Upstream action v5.0.0 SHA
  `45996ed1f6d02564a971a2fa1b5860e934307cf7` bundles that core version.
- Actual core Python strategy executed with synthetic commits and mocked local
  SCM reads: fix→1.8.1, feat→1.9.0, breaking→2.0.0, docs→1.8.1,
  chore-only→no candidate, Release-As override→1.9.0.
- Actual generated feature output is captured in
  `test/fixtures/release-please/17.6.0-feature.md`. It composed against current
  main's full curated notes, preserving historical sections byte for byte.
  The initial generated file must be empty: a nonempty heading-only seed is
  demoted into an unsupported extra heading by the upstream first updater.
- Isolated synthetic 1.9.0 candidate passed `make release-check VERSION=1.9.0`:
  canonical version/notes checks, sdist/wheel build and twine check.
- Fresh independent virtual environments installed the candidate wheel and
  sdist; package import and distribution metadata both reported 1.9.0. The
  wheel's SQLAlchemy dialect entry point was present. Nothing was uploaded.
- Independent architecture and postimplementation agent reviews approved the
  bounded migration, including regeneration freeze, lifecycle ownership,
  unchanged publisher gates and explicit unverified paths.

## Limits

SCM data in upstream strategy execution was mocked. This is real pinned-core
candidate generation, not a live GitHub API/bot PR rehearsal. No release PR,
main merge, tag, GitHub Release, PyPI upload or credential creation occurred.
No live database compatibility matrix or candidate cookbook run was executed.
Existing publisher dry-run evidence in RELEASING.md covers unchanged publisher
code; it installs a published package and does not prove the fresh candidate
artifact's database/cookbook behavior. Required CI must pass at the final heads.

## Reproduce the pinned-core scenarios

Install the pinned core at the exact path used by this script:

```bash
npm install --prefix /tmp/release-please-tools --ignore-scripts release-please@17.6.0
```

The following script uses the real Python strategy and local file-backed mocked SCM reads.
Save it outside the checkout, then run `node <script> <repository-path>`.
Its output candidate lives in `/tmp/sa-rp-candidate`, not in the repository.

```javascript
const fs=require('fs'),path=require('path');
const upstream='/tmp/release-please-tools/node_modules/release-please/build/src';
require(upstream+'/index.js'); const {Python}=require(upstream+'/strategies/python.js');
const {parseConventionalCommits}=require(upstream+'/commit.js');
const {TagName}=require(upstream+'/util/tag-name.js');
const {Version}=require(upstream+'/version.js');
const root=process.argv[2];
const github={repository:{owner:'cubrid-lab',repo:'sqlalchemy-cubrid'},findFilesByFilenameAndRef:async()=>[],getFileContentsOnBranch:async p=>({parsedContent:fs.readFileSync(path.join(root,p),'utf8')})};
(async()=>{
 const scenarios=[['fix: correct failure','1.8.1'],['feat: new optional API','1.9.0'],['feat!: remove old API\n\nBREAKING CHANGE: remove old API','2.0.0'],['docs: improve instructions','1.8.1'],['chore: housekeeping',null],['fix: explicit override\n\nRelease-As: 1.9.0','1.9.0']];
 for(const [message,expected] of scenarios){
 const strategy=new Python({github,targetBranch:'main',component:'sqlalchemy-cubrid',packageName:'sqlalchemy-cubrid',includeComponentInTag:false,changelogPath:'RELEASE_CHANGELOG.md'});
 const commits=parseConventionalCommits([{sha:'a'.repeat(40),message,files:['sqlalchemy_cubrid/__init__.py']}]);
 const candidate=await strategy.buildReleasePullRequest(commits,{tag:new TagName(Version.parse('1.8.0')),sha:'78bcbc7dbd70d8f2c756b25d3c271977ace42aa5',notes:''});
 const actual=candidate?candidate.version.toString():null;
 if(actual!==expected)throw new Error(`${message}: expected ${expected} got ${actual}`);
 console.log(JSON.stringify({message,version:actual}));
 if(candidate&&message.startsWith('feat:')){
 const out='/tmp/sa-rp-candidate';fs.mkdirSync(out,{recursive:true});
 for(const update of candidate.updates){
 const file=path.join(root,update.path); if(!fs.existsSync(file)&&!update.createIfMissing) continue;
 const content=update.updater.updateContent(fs.existsSync(file)?fs.readFileSync(file,'utf8'):undefined);
 fs.mkdirSync(path.dirname(path.join(out,update.path)),{recursive:true}); fs.writeFileSync(path.join(out,update.path),content);
 console.log('updated '+update.path);
 }
 }
 }
})().catch(err=>{console.error(err);process.exit(1)});
```
