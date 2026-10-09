# Release-please 마이그레이션 검증 (한국어)

> 🌐 [RELEASE_PLEASE_VALIDATION.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/RELEASE_PLEASE_VALIDATION.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

2026-10-03에 main `7432169960f486040ac6ef23c3e355b9f4bea01e`와, 리뷰를 마친 구현의
다음 스냅샷(정확히 이 커밋)을 대상으로 기록했습니다:

- #655 어댑터: `9952967b12a6b06270710fb4e05a6b91199f7499`.
- #656 설정/워크플로: `8b4dee606d7b556af55dc54a1d93c93d1d5106c7`.

아래에 기록된 검사는 이 불변 리비전에 적용됩니다. PR 번호만으로는 검증 증거가
되지 않습니다. 재실행할 때는 새로 테스트한 SHA를 기록해야 합니다. 이 마이그레이션은
게시된 패키지 버전을 변경하지 않습니다. 별도의 리뷰된 릴리스 PR이 병합될 때까지
저장소는 1.8.0으로 유지됩니다.

## 실행한 검사

- 대상을 좁힌 오프라인 테스트 109개 통과: canonical composer, 라이프사이클 정리(lifecycle
  reconciliation), 릴리스 워크플로 계약, 릴리스 감지, legacy preparer, 요약(summary).
- 변경된 Python 파일에 대해 Ruff check/format과 `git diff --check`가 통과했습니다.
- 설정과 매니페스트를 설치된 release-please 17.6.0 스키마에 대해 검증했습니다.
  업스트림 액션 v5.0.0 SHA
  `45996ed1f6d02564a971a2fa1b5860e934307cf7`가 해당 코어 버전을 포함(번들)하고 있습니다.
- 실제 코어 Python 전략을 합성 커밋과 모킹한 로컬 SCM 읽기로 실행했습니다:
  fix→1.8.1, feat→1.9.0, breaking→2.0.0, docs→1.8.1,
  chore-only→후보 없음, Release-As 재정의→1.9.0.
- 실제로 생성된 feature 출력은
  `test/fixtures/release-please/17.6.0-feature.md`에 저장되어 있습니다. 이 출력을 현재
  main의 큐레이션된 전체 노트에 합쳐(compose) 보았고, 과거 섹션은 바이트 단위까지 그대로 보존되었습니다.
  최초의 생성 파일은 비어 있어야 합니다. 제목만 넣어 둔(비어 있지 않은) 시드 파일을 쓰면
  업스트림의 첫 업데이터가 그 제목을 한 단계 낮춰, 지원되지 않는 추가 제목으로 만들어 버립니다.
- 격리된 합성 1.9.0 후보가 `make release-check VERSION=1.9.0`을 통과했습니다:
  정식 버전/노트 검사, sdist/wheel 빌드와 twine check.
- 새로 만든 독립 가상 환경들에 후보 wheel과 sdist를 설치했습니다. 패키지 임포트와
  배포 메타데이터 모두 1.9.0을 보고했습니다. wheel의 SQLAlchemy 방언 엔트리 포인트가
  존재했습니다. 아무것도 업로드하지 않았습니다.
- 독립적으로 수행한 아키텍처 리뷰와 구현 후 에이전트 리뷰가 범위를 한정한 이 마이그레이션을
  승인했습니다. 승인 대상에는 재생성 동결, 라이프사이클 소유권, 변경하지 않은 게시자(publisher)
  게이트, 미검증이라고 명시한 경로가 포함됩니다.

## 한계

업스트림 전략 실행의 SCM 데이터는 모킹했습니다. 이는 버전을 고정한 실제 코어(pinned core)로
후보를 생성한 것이지, 라이브 GitHub API/봇 PR 리허설이 아닙니다. 릴리스 PR, main 병합, 태그,
GitHub Release, PyPI 업로드, 자격 증명 생성은 일어나지 않았습니다.
라이브 데이터베이스 호환성 매트릭스나 후보 쿡북 실행은 수행하지 않았습니다.
RELEASING.md의 기존 게시자 드라이런 증거는 변경되지 않은 게시자 코드를 다룹니다.
이 증거는 게시된 패키지를 설치하며, 새 후보 산출물의 데이터베이스/쿡북 동작을
증명하지 않습니다. 필수 CI는 최종 헤드에서 통과해야 합니다.

## 핀 고정 코어 시나리오 재현

이 스크립트가 사용하는 정확한 경로에 핀 고정 코어를 설치합니다:

```bash
npm install --prefix /tmp/release-please-tools --ignore-scripts release-please@17.6.0
```

다음 스크립트는 실제 Python 전략과 로컬 파일 기반의 모킹한 SCM 읽기를 사용합니다.
체크아웃 바깥에 저장한 다음 `node <script> <repository-path>`를 실행합니다.
출력 후보는 저장소가 아니라 `/tmp/sa-rp-candidate`에 생성됩니다.

```javascript
const fs=require('fs'),path=require('path');
const upstream='/tmp/release-please-tools/node_modules/release-please/build/src';
require(upstream+'/index.js'); const {Python}=require(upstream+'/strategies/python.js');
const {Manifest}=require(upstream+'/manifest.js');
const {parseConventionalCommits}=require(upstream+'/commit.js');
const {TagName}=require(upstream+'/util/tag-name.js');
const {Version}=require(upstream+'/version.js');
const root=process.argv[2];
const github={repository:{owner:'cubrid-lab',repo:'sqlalchemy-cubrid'},getFileJson:async p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8')),findFilesByFilenameAndRef:async()=>[],getFileContentsOnBranch:async p=>({parsedContent:fs.readFileSync(path.join(root,p),'utf8')})};
(async()=>{
 const manifest=await Manifest.fromManifest(github,'main');
 const released=/^__version__ = "([^"]+)"$/m.exec(fs.readFileSync(path.join(root,'sqlalchemy_cubrid/__init__.py'),'utf8'))[1];
 if(manifest.releasedVersions['.'].toString()!==released||manifest.repositoryConfig['.'].releaseType!=='python')throw new Error('Invalid manifest/config mapping');
 const scenarios=[['fix: correct failure','1.8.1','Fixed'],['feat: new optional API','1.9.0','Added'],['feat!: remove old API\n\nBREAKING CHANGE: remove old API','2.0.0','Added'],['docs: improve instructions','1.8.1','Documentation'],['perf: faster compile','1.8.1','Performance'],['chore: housekeeping',null],['ci: pin action',null],['test: add case',null],['refactor: tidy',null],['fix: explicit override\n\nRelease-As: 1.9.0','1.9.0','Fixed']];
 const allowed=new Set(['Upgrade notes','Added','Changed','Deprecated','Removed','Fixed','Security','Performance','Documentation','CI','Tests','⚠ BREAKING CHANGES']);
 for(const [message,expected,heading] of scenarios){
 const strategy=new Python({...manifest.repositoryConfig['.'],github,targetBranch:'main'});
 const commits=parseConventionalCommits([{sha:'a'.repeat(40),message,files:['sqlalchemy_cubrid/__init__.py']}]);
 const candidate=await strategy.buildReleasePullRequest(commits,{tag:new TagName(Version.parse('1.8.0')),sha:'78bcbc7dbd70d8f2c756b25d3c271977ace42aa5',notes:''});
 const actual=candidate?candidate.version.toString():null;
 if(actual!==expected)throw new Error(`${message}: expected ${expected} got ${actual}`);
 const headings=candidate?[...candidate.body.toString().matchAll(/^### (.+)$/gm)].map(m=>m[1]):[];
 if(candidate&&(!headings.includes(heading)||headings.some(h=>!allowed.has(h))))throw new Error(`${message}: expected ### ${heading}, got ${headings}`);
 console.log(JSON.stringify({message,version:actual,headings}));
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

이 스크립트는 업스트림 매니페스트 로더로 `release-please-config.json`과
`.release-please-manifest.json`을 읽으므로 저장소의 `changelog-sections`가 적용됩니다.
매니페스트 버전이 `sqlalchemy_cubrid/__init__.py`의 `__version__`과 같지 않으면 실패하며,
릴리스 대상 커밋 유형마다 생성되는 `###` 제목을 확인합니다(AGENTS.md "GitHub Release Policy"):
fix→Fixed, feat→Added, docs→Documentation, perf→Performance이고, chore, ci, test,
refactor만으로는 후보가 생기지 않습니다. 빈 파일에서 생성한 기능 후보의
`RELEASE_CHANGELOG.md`가 `test/fixtures/release-please/17.6.0-feature.md` 픽스처입니다
(날짜는 픽스처에 기록된 값).
