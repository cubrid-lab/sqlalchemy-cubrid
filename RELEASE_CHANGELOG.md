# Changelog

## [1.12.3](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.12.2...v1.12.3) (2026-11-13)


### Fixed

* capture driver and URL scheme in bug reports ([6c190e5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6c190e5550be775273c54e34ffbb06c9e8b44261)), closes [#1079](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1079)
* check CUBRIDdb connections without ping() using SELECT 1 ([#1305](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1305)) ([8d8fcab](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8d8fcaba6ddbeda123f57f38e1b0f0403b263ced)), closes [#1304](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1304)
* **compiler:** render LIMIT integers inline for CUBRIDdb older than 11.3 ([#1300](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1300)) ([5e3f10f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5e3f10f2bcd73859b31d4bdb68faedd4331d5bbc))
* **dialect:** name the CUBRIDdb 9.3 limitations in the first-connect warning ([#1307](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1307)) ([b89b774](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b89b774aced7c8ba6b773c2a82d9b4df215a9d02)), closes [#1142](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1142)
* explain CUBRIDdb import setup without excluding supported drivers ([#1150](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1150)) ([38170c2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/38170c280a8b4ce8085e24c3deba14f1573fd539))
* publish curated v1.12.2 release notes with verified contributor credits ([#1158](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1158)) ([5d054c9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5d054c970524e8a93e652d7a07468cc6cb8d3263))
* **release:** list each change once when curated and generated notes overlap ([#1317](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1317)) ([69b39fa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/69b39fa8ba46f032d86d333e7a6d8b495a64f4f0))
* treat a NULL LAST_INSERT_ID() as no generated key ([#1303](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1303)) ([1fb81a7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1fb81a76ffa5b17f1536ffada9c9801009c029a5)), closes [#1302](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1302)
* **types:** return BIGINT results as int with CUBRIDdb older than 11.3 ([#1301](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1301)) ([b22a011](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b22a011fe35d97a085ff2bacbeb96688c00937f4))
* **types:** return correct Boolean values for untyped results with CUBRIDdb older than 11.3 ([#1321](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1321)) ([858d3b2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/858d3b25f99958a3bcb51ede92ac02e72a042f0c)), closes [#1143](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1143)
* **types:** revise the ignored type argument retirement warning ([c6cd853](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c6cd853109f24d06ceaf7cd5cadbf9c5f234d622)), closes [#892](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/892)
* verify published release body with a fresh GitHub API read ([a41616d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a41616df4407d1545871969a4e2c17ce38ed8a8f))
* verify published release notes after synchronization ([#1175](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1175)) ([a41616d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a41616df4407d1545871969a4e2c17ce38ed8a8f))


### Changed

* restore release notes merged without review approval ([#1185](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1185)) ([ce3d338](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ce3d338420e3bc011a692b7459c66fecb7390fd4))


### Documentation

* add a release-note credit review checklist ([#1337](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1337)) ([bf324f2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/bf324f2eacab1d34b32f71e41b7f62654f938401)), closes [#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)
* add clear release summaries across 14 historical versions ([#1177](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1177)) ([7dd2e3a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7dd2e3acd0d4095577a9af51e16c571b4fb095c4))
* add concise reader summaries to 14 published historical releases ([7dd2e3a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7dd2e3acd0d4095577a9af51e16c571b4fb095c4))
* add concrete user-facing highlights to v1.7.0 and v1.7.1 ([80e4026](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/80e4026a667fc506aa64c01b292c579daa6edae4))
* add reader-focused introductions to seven oversized historical releases ([1a4087c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1a4087c738c0df87cc81d53e490649e5b1dc34b0))
* add support links to the documentation Help menu ([#1297](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1297)) ([f199380](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f1993803d700c2f2cda2ae97d61223935a6b7df3))
* add the omitted v1.12.1 test contribution ([#1203](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1203)) ([2957cb7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2957cb7b633583d11679bd33d3507b86bce4af2b))
* add the omitted v1.12.2 test contributions ([#1204](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1204)) ([80b002b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/80b002b5917f84c2609593b285a6fb1148b22570))
* add troubleshooting and questions to issue chooser ([9f5ea30](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9f5ea30de76c91762d2dd5ee65e8d2760818780d)), closes [#1077](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1077)
* add Windows virtual environment setup to Lesson 1 ([cf75832](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/cf75832e1069ea60968cdfef92d16fa9fbc734d8)), closes [#1087](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1087)
* align CUBRIDdb troubleshooting with supported installation paths ([#1205](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1205)) ([57c4ff5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/57c4ff50b69896438d7da9957ed2b4b19b335b43))
* align translated driver guidance and guard the Korean support matrix ([#1309](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1309)) ([d2f67d1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d2f67d16b6ff392e26844cf2b62d4d433259d798)), closes [#1148](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1148)
* apply valid Copilot review corrections to release note layout ([11a5179](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/11a51797d82d85f3c94ed9bb6aec00957c3685b7))
* attribute v1.12.0 release changes to verified PR author ([4219029](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4219029ff27b00a10277e77d34eaac58a2d366eb))
* audit historical releases and guard retrospective synchronization ([#1156](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1156)) ([8d637ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8d637ee008187af9b24e7182e17edba64c92debd))
* clarify issue handoff and work states ([35c1c8c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/35c1c8cddd10785e1d4389b630492b3d174fa4d0))
* clarify local issue and PR evidence ownership ([#1166](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1166)) ([aaf8b19](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aaf8b1974383688d5be4da8822689110d4364a4f))
* clarify sqlalchemy-cubrid local issue and PR evidence ([aaf8b19](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aaf8b1974383688d5be4da8822689110d4364a4f))
* clarify when scoped type ignores are acceptable ([f8f37fb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f8f37fbe05825244fec3e0470b6e8191d09ea64e)), closes [#1101](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1101)
* complete historical release comparison links without rewriting original notes ([#1167](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1167)) ([250ae53](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/250ae53129b2201342f7640d6d8deb8336859bd2))
* complete human author credits in the v1.2.0 to v1.7.1 release notes ([#1335](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1335)) ([980eb7a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/980eb7a2ada3b38a8c488d437715c7ef29cbbb80)), closes [#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)
* complete human author credits in the v1.8.0 release notes ([#1334](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1334)) ([27b8c90](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/27b8c9004608cf7c827a228a06f55b46996214df)), closes [#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)
* complete human author credits in the v1.9.0 release notes ([#1333](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1333)) ([2c802d4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2c802d47edb3910fdf49d9a2be2547efc24a9f84)), closes [#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)
* complete missing comparison links across published historical releases ([250ae53](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/250ae53129b2201342f7640d6d8deb8336859bd2))
* consolidate v1.12.1 release notes into reader-focused changes ([4e26ebe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4e26ebee313aa92d68c7119cb5b3a73b4e9e9eee))
* **contributing:** add lifecycle guidance for temporary scripts and repair tools ([1876263](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1876263d6efe35bc60325b13fea206fad5c3d228)), closes [#1183](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1183)
* **contributing:** describe the lifecycle of temporary scripts and repair tools ([#1316](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1316)) ([1876263](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1876263d6efe35bc60325b13fea206fad5c3d228))
* correct CUBRID 10.2 feature support guidance ([34a4952](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/34a4952530ebfac1a638edd470f6629267baa0d1)), closes [#1082](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1082)
* correct factual errors in historical release notes ([#1340](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1340)) ([fb3d28c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb3d28c047c99081527d2e325c5460d79a7a4f7a)), closes [#1338](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1338)
* correct headings and historical facts in older release notes ([#1184](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1184)) ([ccb8adf](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ccb8adf383a5d04bdd0fea65e2c2565fae277373))
* correct live CI claims in translated READMEs ([10a31cc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/10a31cc662ca6d62d34cf38dc9a72c5da114642b)), closes [#1075](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1075)
* correct release note layout flagged by Copilot ([#1180](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1180)) ([11a5179](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/11a51797d82d85f3c94ed9bb6aec00957c3685b7))
* correct the PyPI 1.2.2 yank statement in the v1.2.2 notes ([#1187](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1187)) ([4b6a867](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4b6a8672cb1bb76b033da7421b4eae1cb979d150))
* correct the PyPI 1.2.2 yank statement in the v1.2.3 notes ([#1186](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1186)) ([f4876ad](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f4876ad51b1cee83abea3e65580f720bce01581d))
* credit human authors in the v0.7.1 to v1.4.1 release notes ([#1330](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1330)) ([51c7d47](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/51c7d478119c9c44f572be90b40cdc8aaa8e1c53))
* credit human authors in the v0.7.1–v1.4.1 release notes ([51c7d47](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/51c7d478119c9c44f572be90b40cdc8aaa8e1c53)), closes [#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)
* credit human PR author of v1.2.2 Alembic fixes ([98ce55e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/98ce55e83ce2cb2356ba9bf95c9671a1d5a29624))
* credit the v1.11.0 external contributor ([#1199](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1199)) ([578cc62](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/578cc6232899a4a219627c3c0e5f2fcba7908e2b))
* credit the v1.11.6 contributor ([#1202](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1202)) ([b88795a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b88795a4bff77adc10dabd14ad4eab7293a93a52))
* credit v1.11.5 contributors and add omitted test changes ([#1201](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1201)) ([f6b0f39](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f6b0f397ae67e6f273fcb62078eaa7d615b3ae97))
* credit v1.8.0 contributors and add omitted merged changes ([#1198](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1198)) ([24926e3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24926e3c56978e73c294e337f6527090600f45be))
* credit verified human author in v1.11.7 notes ([#1224](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1224)) ([da75b8f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/da75b8f2601765047db2e9bf39b33888dbfb4c5a))
* credit verified human author of v1.11.7 documentation change ([da75b8f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/da75b8f2601765047db2e9bf39b33888dbfb4c5a))
* credit verified human author of v1.5.1 fixes ([856b6c8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/856b6c854c20f63cc2f145368e4b412cb5b02270))
* credit verified human contributors, not AI agents, in release notes ([#1214](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1214)) ([1e58bb1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1e58bb194bf73e8e26242641000e1851cbe442bb))
* credit verified human PR author for v1.2.1 fixes and tests ([3ec0adb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3ec0adb05d600e217655dacecb3f5a6bd5b73cee))
* credit verified v1.12.1 human PR authors ([b115781](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b11578178805109bee2f06764d572ba6a191c113))
* credit verified v1.2.2 Alembic fixes author ([#1228](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1228)) ([98ce55e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/98ce55e83ce2cb2356ba9bf95c9671a1d5a29624))
* credit verified v1.4.3 contributions ([#1283](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1283)) ([9ab3a32](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9ab3a32de13fde14b869f8089eb4f5385753c002))
* credit verified v1.5.0 feature and test authors ([fdf2cb4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fdf2cb40fd3929ff6db2edb075db5c6445333ea5))
* curate v1.12.1 release notes and synchronize published body ([#1168](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1168)) ([e29c85f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e29c85faf73d0a437a5d987c9a53eaf6215b870b))
* define flexible 1.x dialect API compatibility policy ([7457b3f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7457b3fdce388dd4005da901bd4bb35f63f32eb0)), closes [#892](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/892)
* define issue handoff and development states ([#1326](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1326)) ([35c1c8c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/35c1c8cddd10785e1d4389b630492b3d174fa4d0))
* describe what the dialect now handles for the PyPI CUBRIDdb 9.3 driver ([#1328](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1328)) ([d146583](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d1465830f6a8cc3b53917cc377753ca4e4b5a554))
* **dialect:** document dialect options, MERGE builder and string type arguments ([#1315](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1315)) ([46da694](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/46da6943c76517f597f365eb2003df8a7a8fc792)), closes [#1292](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1292)
* distinguish database server and Python driver version identifiers ([#1149](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1149)) ([133c944](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/133c94481c5247c0046bc1a2315575e92d4c856a))
* drop duplicated release-please bullets from the v1.12.0 notes ([#1194](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1194)) ([3837b49](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3837b49d8e3c034d6925430b77ee95ed69bb0be8))
* explain Apple silicon options for the CUBRID lab ([7c6e1e6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c6e1e69ba3485104ba8f372d788a92df77a3517)), closes [#1088](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1088)
* explain missing greenlet errors for async engines ([bbf029e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/bbf029e9c7015830760acb280a2ede58e4776311)), closes [#1084](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1084)
* explain the CUBRIDdb 9.3 double-close SystemError and why the dialect keeps closing ([#1331](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1331)) ([055ce53](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/055ce53d2bd347ab6f7eab46226a9624f4500add)), closes [#1320](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1320)
* fix broker readiness and quickstart troubleshooting ([5886ff7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5886ff74c8b357123f1551c3b3a056f78b1e74e1)), closes [#1080](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1080)
* fix Markdown layout across published release notes ([#1229](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1229)) ([a1656bc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a1656bc07fe2f634b6ec16094d31b7be142800ad))
* fix published site links to repository files ([136fbc8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/136fbc816571aec01a9d394c7a6b12db5cb61187)), closes [#1076](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1076)
* fold duplicated release-please bullets in the v1.11.5 notes ([#1216](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1216)) ([864fab3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/864fab3312e39897f672ec8ed8826a3f2510d37d))
* fold duplicated release-please bullets in the v1.9.0 notes ([#1215](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1215)) ([9fbbc80](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9fbbc80778a0f7c678fc57a0fde3899ce85f6e0d))
* give users a consistent support and questions path ([abbaca4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/abbaca4182087b64f45f083c8fda3a096f58ebf2)), closes [#1078](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1078)
* guide translated users to their first CUBRID connection ([b0b06d0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b0b06d043f5b7a863e6ec450aa3e48edc018eba5)), closes [#1074](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1074)
* highlight user-visible changes in v1.7.0 and v1.7.1 ([#1178](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1178)) ([80e4026](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/80e4026a667fc506aa64c01b292c579daa6edae4))
* improve published release note spacing and reader summaries ([385d942](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/385d94267b9c5255891d0da9065f3628d5708a7a))
* introduce reader-focused summaries for seven lengthy releases ([#1173](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1173)) ([1a4087c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1a4087c738c0df87cc81d53e490649e5b1dc34b0))
* keep both CUBRIDdb driver lines in the support policy ([#1298](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1298)) ([b01b30e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b01b30e110986ad948fd8e6978ea58bce27f6cfd))
* keep SQLAlchemy dialect contribution rules in this repository ([#1286](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1286)) ([ee51192](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee511920a055b6182b4112cf5c92177e73b6d553))
* label the 1.8.0 PRD as a historical snapshot ([7dc5c9f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7dc5c9f7fa43aaa52f34ef441b8b36f3905f0a9d)), closes [#1096](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1096)
* make published release notes easier to read ([#1246](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1246)) ([385d942](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/385d94267b9c5255891d0da9065f3628d5708a7a))
* make PyPI README links and demo render correctly ([97a855c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/97a855cc89a743440de3e0c13327eb5f437161b7)), closes [#1097](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1097)
* make the v1.10.0 release notes easier to scan ([#1348](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1348)) ([74b60ea](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/74b60ea80a1f90329a47ba30821363f22cc392e0)), closes [#1256](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1256)
* make the v1.11.0 release notes easier to scan ([#1345](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1345)) ([2a1c467](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2a1c467bbfb775452022835bd863df992351d721)), closes [#1253](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1253)
* make the v1.11.5 release notes easier to scan ([#1341](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1341)) ([86f56f7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/86f56f7f9d8ff529c4adb6294b29f01b1bde430d))
* make the v1.7.0 release notes easier to scan ([#1347](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1347)) ([3468135](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3468135fe08ca820588a0abec09d9eeeaf94e920)), closes [#1255](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1255)
* make the v1.7.1 release notes easier to scan ([#1346](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1346)) ([c005bb9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c005bb914db17e3c9e129ebd873cb2536c75e6ac)), closes [#1254](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1254)
* make the v1.8.0 upgrade and SQL changes easier to read ([#1342](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1342)) ([f2b931f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f2b931f8ceaf8bacd23e2ced719e027ea793d2ac)), closes [#1252](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1252)
* make v1.12.1 release notes concise and user-focused ([#1174](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1174)) ([4e26ebe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4e26ebee313aa92d68c7119cb5b3a73b4e9e9eee))
* mark the revised compatibility policy in the v1.0.0 notes ([#1188](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1188)) ([0b16bf7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0b16bf729f569f41b6554d26e605d0bb3fef74bb))
* match pycubrid import and authentication error messages ([#1137](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1137)) ([4c6160f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4c6160f8206a756ac0c2326ed84c294c899f7d6a))
* merge the v1.7.1 documentation sections and credit the contributor ([#1197](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1197)) ([6307bcb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6307bcb56ee7de898cc3dbce3e3a452a5cd0feac))
* move the curated 1.12.3 notes into Unreleased ([#1219](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1219)) ([0f4f331](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0f4f331bc90f83e75335e546cbda126b6849a612))
* order the v1.6.0 notes sections by policy ([#1193](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1193)) ([aa440be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aa440be0eaca59e2aa7301a6193209260d43b51e))
* order the v1.7.0 notes sections and credit verified contributors ([#1196](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1196)) ([d79ed67](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d79ed6712795da8f819acd7f425a76e432da8d79))
* point the connection guide to the version terminology section ([#1312](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1312)) ([0241a92](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0241a92f5ff9573ab9f0ecd6c8bf856842eadb88))
* prepare accurate notes for nine historical draft releases ([#1231](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1231)) ([8f9d57c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8f9d57cb3ef9ffecf678f1b1db77968152bb95e9))
* **release:** attribute six v1.9.0 additions to verified contributors ([#1244](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1244)) ([af55847](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/af55847107cb9a80703739b3d9ae34aa637b5b19))
* **release:** attribute v1.11.0 CI and test improvements ([#1241](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1241)) ([6569a42](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6569a421dc8a66b124a5c91b670a5e5fcde93984))
* **release:** clarify and credit v1.12.0 release notes ([#1233](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1233)) ([7b66526](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7b66526b4c16c212a476784df7500ce881c83b9d))
* **release:** clarify v0.1.0 draft upgrade and feature notes ([#1266](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1266)) ([fb6b0f3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb6b0f348c30bf1216d21ffb41b5820be360d61e))
* **release:** clarify v0.2.0 SQL features and documentation ([#1267](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1267)) ([24eed61](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24eed61b7be2b7da242cd45adc7f14daa724d86f))
* **release:** clarify v0.3.0 Alembic and testing changes ([#1268](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1268)) ([dfb3d02](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dfb3d027fe2693df0c2567c4bcadada22f381ae1))
* **release:** clarify v0.6.0 migration support and historical driver limits ([#1273](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1273)) ([ee941ce](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee941cee57bf59fe388a6b1db252e9516f418fab))
* **release:** clarify v1.10.0 license inventory and compatibility notes ([#1259](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1259)) ([050b441](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/050b4412d1ae75b2479e16af3e5ba1ac5db87ccb))
* **release:** clarify v1.11.5 documentation and validation notes ([#1275](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1275)) ([fa2980c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fa2980c6242ba0513318b6a86d61af282ed26044))
* **release:** clarify v1.5.0 compatibility and benchmark notes ([#1258](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1258)) ([ef7e13b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ef7e13b194356c5c0c984b8faee43488f1884bf3))
* **release:** clarify v1.7.0 connection and literal safety notes ([#1262](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1262)) ([c4a74d9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c4a74d9aea57ec0785c37e3f4ba672cba37b6be1))
* **release:** clarify v1.7.0 driver canaries and async setup ([#1280](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1280)) ([fc8089e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fc8089e642fecf7c869cc5bbbfd79070c51e1649))
* **release:** clarify v1.7.1 application and cross-version tests ([#1279](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1279)) ([31069e0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/31069e009e2a7f744d29902cdfc361c3a89f5471))
* **release:** clarify v1.7.1 reflection fixes and test coverage ([#1261](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1261)) ([a9003ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a9003ee8362615c6b061719cf89779bb71d2707c))
* **release:** clarify v1.8.0 autocommit and reflection behavior ([#1263](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1263)) ([5dc314f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dc314f0a1546ff9a9ddedfe0352a041663de004))
* **release:** clarify v1.8.0 compliance and mutation test notes ([#1277](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1277)) ([811a396](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/811a396f96978c051bb457a2eeb69b36298a1568))
* **release:** clarify v1.9.0 driver tests and integration setup ([#1264](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1264)) ([5dd50e8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dd50e8774aa52d622f5fae2d1ee7843f69d54ea))
* **release:** clarify v1.9.0 integration cleanup and failures ([#1276](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1276)) ([f9ba6e0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f9ba6e05a933a6cec3709247e571530fbae859a9))
* **release:** complete v1.11.5 change and upgrade credits ([#1238](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1238)) ([20bacd8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/20bacd8efe48db356c149a6994a046ed1c3bddb4))
* **release:** correct v1.12.1 release notes ([#1232](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1232)) ([ee0f96e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee0f96ed50ea764c67034d661664b0a3bd7f630e))
* **release:** credit and link v1.9.0 added changes ([af55847](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/af55847107cb9a80703739b3d9ae34aa637b5b19))
* **release:** credit the verified v1.4.2 ping contribution ([#1282](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1282)) ([2d5c7d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2d5c7d6990a86955926247e3cbfc8a57e62d2f26))
* **release:** credit v1.11.0 CI and test changes ([6569a42](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6569a421dc8a66b124a5c91b670a5e5fcde93984))
* **release:** credit v1.11.0 upgrade and behavior changes ([19a07be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/19a07beabac8b7f3d7b505c89dfed5a5dc75356a))
* **release:** credit v1.11.0 upgrade and package changes ([#1240](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1240)) ([19a07be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/19a07beabac8b7f3d7b505c89dfed5a5dc75356a))
* **release:** credit v1.11.5 CI and tests with source PRs ([b011986](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b011986852b688512a2c63fb09697e3ad8e9299d))
* **release:** credit v1.11.5 documentation and remove duplicate entry ([50dc7ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/50dc7ee7796b73369ca98fcf11882ebdf4590107))
* **release:** credit verified human changes in v1.4.2 ([2d5c7d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2d5c7d6990a86955926247e3cbfc8a57e62d2f26))
* **release:** credit verified v1.11.5 dialect fixes ([#1235](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1235)) ([58f754b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/58f754b8a9fbad362c93cbfadca1bf659252a780))
* **release:** deduplicate v1.10.0 and credit verified changes ([eff375f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/eff375fd51ef4b5d986f316b5eda8c9d1267a6c0))
* **release:** document v0.5.0 SQL features and historical limits ([#1272](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1272)) ([7d6b234](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7d6b234b291dfa9947365ee8f5a0f4a0b7be414c))
* **release:** finish v1.11.5 change credits and historical references ([20bacd8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/20bacd8efe48db356c149a6994a046ed1c3bddb4))
* **release:** freeze release candidates only when their review starts ([#1295](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1295)) ([ee52eb5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee52eb5215b8242f2380871d72f95c4099e8da41))
* **release:** improve v1.11.0 user-facing notes ([a2c7701](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a2c770103c1b38d914e12080e19ac8aa2a3cbcc5))
* **release:** keep standard sections and concise contributor credits ([#1250](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1250)) ([5fbcb4b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5fbcb4bb6c564298cf187f7eac34950a969393b9))
* **release:** make historical draft v0.2.0 reader-friendly ([24eed61](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24eed61b7be2b7da242cd45adc7f14daa724d86f))
* **release:** make historical draft v0.3.0 reader-friendly ([dfb3d02](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dfb3d027fe2693df0c2567c4bcadada22f381ae1))
* **release:** make historical draft v0.3.2 reader-friendly ([845d086](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/845d08655dfd7a7afe0dfa5eca347eaa5bfcde6a))
* **release:** make historical draft v0.4.0 reader-friendly ([7fc6997](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7fc6997903350938a3f351e555a832feb8571ffd))
* **release:** make historical draft v0.5.0 reader-friendly ([7d6b234](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7d6b234b291dfa9947365ee8f5a0f4a0b7be414c))
* **release:** make historical draft v0.7.0 reader-friendly ([d1ceba0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d1ceba0bba6716bb307b49be44cd222f4398ccc4))
* **release:** make v0.7.0 pycubrid draft concise and traceable ([#1274](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1274)) ([d1ceba0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d1ceba0bba6716bb307b49be44cd222f4398ccc4))
* **release:** make v1.7.1 detailed notes easier to read ([a9003ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a9003ee8362615c6b061719cf89779bb71d2707c))
* **release:** make v1.8.0 detailed notes easier to read ([5dc314f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dc314f0a1546ff9a9ddedfe0352a041663de004))
* **release:** make v1.9.0 detailed notes easier to read ([5dd50e8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dd50e8774aa52d622f5fae2d1ee7843f69d54ea))
* **release:** organize v0.3.1 draft documentation and cleanup ([#1269](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1269)) ([94f2c89](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/94f2c89adbb5c5d2e67a461a477a133b58ad52b1))
* **release:** organize v0.3.2 draft documentation changes ([#1270](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1270)) ([845d086](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/845d08655dfd7a7afe0dfa5eca347eaa5bfcde6a))
* **release:** reconcile and credit v1.12.0 changes ([7b66526](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7b66526b4c16c212a476784df7500ce881c83b9d))
* **release:** remove duplicate v1.10.0 entries and verify credits ([#1242](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1242)) ([eff375f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/eff375fd51ef4b5d986f316b5eda8c9d1267a6c0))
* **release:** restore omitted v1.10.0 CI and dependency updates ([c0d0afa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c0d0afa24bb323c6ebc44a7b1f54b1e6894578a4))
* **release:** restore omitted v1.11.6 CI change ([#1234](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1234)) ([e496ce2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e496ce244ffa9ba994afb9fccf4cd78c8dca1b58))
* **release:** restore omitted v1.11.6 release automation change ([e496ce2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e496ce244ffa9ba994afb9fccf4cd78c8dca1b58))
* **release:** restore v1.10.0 CI changes missing from the notes ([#1243](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1243)) ([c0d0afa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c0d0afa24bb323c6ebc44a7b1f54b1e6894578a4))
* **release:** separate v0.4.0 connection changes from CI coverage ([#1271](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1271)) ([7fc6997](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7fc6997903350938a3f351e555a832feb8571ffd))
* **release:** shorten v1.11.0 tooling notes while preserving upgrade guidance ([#1260](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1260)) ([a2c7701](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a2c770103c1b38d914e12080e19ac8aa2a3cbcc5))
* **release:** shorten v1.11.5 upgrade notes and key fixes ([#1249](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1249)) ([87a2f10](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/87a2f1033d452af12daf4a549cac4306066dde5b))
* **release:** simplify v1.10.0 historical notes ([1dfbd59](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1dfbd59d2e4d82748d030ae82b0d4b03feddd33a))
* **release:** simplify v1.10.0 license and localization notes ([#1281](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1281)) ([1dfbd59](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1dfbd59d2e4d82748d030ae82b0d4b03feddd33a))
* **release:** simplify v1.11.0 support and CI notes ([#1278](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1278)) ([aad9a42](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aad9a42f301da3bb7867f7bfcee8f312fa006c22))
* **release:** simplify v1.11.5 internal tooling notes ([#1265](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1265)) ([5b2d5d3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5b2d5d3a4f646b7b8f5d522ebcf03f9c737a3dca))
* **release:** verify v1.11.0 documentation attribution ([#1239](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1239)) ([ee6b6a4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee6b6a49b9a873dcc06722843bd4c7749e1343ae))
* **release:** verify v1.11.5 CI and test contributor credits ([#1237](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1237)) ([b011986](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b011986852b688512a2c63fb09697e3ad8e9299d))
* **release:** verify v1.11.5 documentation credits and remove duplicate ([#1236](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1236)) ([50dc7ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/50dc7ee7796b73369ca98fcf11882ebdf4590107))
* **release:** verify v1.9.0 change and workflow author credits ([#1245](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1245)) ([2590136](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2590136967663a10c00332842f2c8f192c9b1c12))
* remove contest deadline from Korean README sync guidance ([#1160](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1160)) ([06744db](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/06744dbaf9925cd908d6afef6df9e49a49667ac6))
* remove obsolete organization roadmap and board references ([#1284](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1284)) ([ab8c6d7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ab8c6d7f4eda1ff727c026ed026ea22ee332146c))
* remove the abandoned Sphinx documentation scaffold ([#1138](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1138)) ([9c2fdcb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9c2fdcbfd2373da3371f29096a5cd08a5e70eaa7))
* remove unsupported CUBRID-Python install advice ([e74b96e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e74b96e9039216c3e7bec66edc5760f201240740)), closes [#1083](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1083)
* replace v1.11.6 and v1.11.7 commit dumps with release summaries ([#1170](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1170)) ([9d5b8f0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9d5b8f0c3fec70101a58cf28a10667e8cd3a3bcc))
* restore published v1.2.0 details missing from the changelog ([#1209](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1209)) ([ef778d5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ef778d511ac69fe6ea7f82147ff0a1292a208ab5))
* restore published v1.6.0 PR references and test results ([#1210](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1210)) ([e060875](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e060875c0591eecac58f97442cf38e198f65944a))
* restore the v0.8.0 support boundary and date the pycubrid pin ([#1207](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1207)) ([bea6cef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/bea6cef39330ffe86c9f8e5f44a5e4dd782c95b0))
* restore the v1.1.0 async dialect requirements ([#1208](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1208)) ([b176bf6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b176bf6371ae77d5ecb446b51767085202f59b6b))
* restore v1.2.1 human contributor credits ([#1227](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1227)) ([3ec0adb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3ec0adb05d600e217655dacecb3f5a6bd5b73cee))
* restore v1.5.0 human contributor credits ([#1226](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1226)) ([fdf2cb4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fdf2cb40fd3929ff6db2edb075db5c6445333ea5))
* restore v1.5.1 human contributor credits ([#1225](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1225)) ([856b6c8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/856b6c854c20f63cc2f145368e4b412cb5b02270))
* restore verified human author credits in v1.12.0 notes ([#1223](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1223)) ([4219029](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4219029ff27b00a10277e77d34eaac58a2d366eb))
* restore verified human author credits in v1.12.1 notes ([#1221](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1221)) ([b115781](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b11578178805109bee2f06764d572ba6a191c113))
* restore verified v0.7.1 performance and package notes ([#1211](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1211)) ([a0f608b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a0f608bd7bb835611d7863a1638b0a73bf0e9e10))
* rewrite three historical release notes with clear upgrade guidance ([6890392](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6890392c56db038e7fd594b07fdb726c70c537d7))
* rewrite v1.4.1, v1.4.2 and v1.5.1 release notes ([#1176](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1176)) ([6890392](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6890392c56db038e7fd594b07fdb726c70c537d7))
* rewrite v1.7.0–v1.11.5 release notes around user-visible changes ([#1179](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1179)) ([06ce186](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/06ce1864a7f95ceb9683e71171b93662b03cfb27))
* shorten the v1.9.0 release notes without losing compatibility details ([#1343](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1343)) ([ee1a9ef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee1a9ef9a89ed484534ec35e93cf119ba3ab99ef))
* show both CUBRIDdb installation options in the README and guides ([#1308](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1308)) ([b36e0d3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b36e0d3b734644e03e9b371f837ee09bc924b830)), closes [#1147](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1147)
* standardize release notes and verified contributor credits ([#1152](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1152)) ([ed3c78f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed3c78f1a50c7b9d4f0691fe81b3a181bd89f32c))
* standardize v1.10.0 note headings and credit verified contributors ([#1195](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1195)) ([2fbc165](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2fbc16557b0fb3d780793627986a197299a1d436))
* standardize v1.9.0 note headings and credit verified contributors ([#1200](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1200)) ([478e80c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/478e80cbb90a5b046ebbad96b37e67b400965e53))
* synchronize four verified historical GitHub Releases safely ([#1161](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1161)) ([46f91a2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/46f91a2b1f764998863bf9e7ad6e914706c0c2e2))
* tidy the v1.11.0 notes without changing user-facing entries ([#1213](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1213)) ([3ce6c2e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3ce6c2e75a3ee1639bc46225473c465ba96b8191))
* track issue work without project boards ([c80d6e4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c80d6e47bb0e420a72166d46927617f3adeba3c9))
* use issues and pull requests without project boards ([#1327](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1327)) ([c80d6e4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c80d6e47bb0e420a72166d46927617f3adeba3c9))
* use pycubrid URLs in translated connection examples ([59dd870](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/59dd8708d274225a003a6d0be91d682d46c7f19a)), closes [#1073](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1073)
* use standard section headings in the v1.2.1 notes ([#1189](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1189)) ([f8bac96](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f8bac960a54955401f6f700480c8b99ed2fd5b6f))
* use standard section headings in the v1.3.0 notes ([#1190](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1190)) ([c70aa2c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c70aa2cd6de871592d7ed883f38562bcf5fb12e1))
* use standard section headings in the v1.4.0 notes ([#1191](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1191)) ([0c5fa90](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0c5fa90f9d2e3256132e5682dcb6e586285bc0a9))
* use standard section headings in the v1.5.0 notes ([#1192](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1192)) ([280fa6c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/280fa6c2ca43b4b8364f283de380c3b58f370737))

## [1.12.2](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.12.1...v1.12.2) (2026-11-05)


### Documentation

* adopt the organization rule for self-explanatory comments ([#1103](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1103)) ([dd7f2b8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dd7f2b86642b439ebc29fa303e0e02ed1e52d8cb))
* adopt type-only issue titles and evidence-based triage ([#1060](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1060)) ([8b59020](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8b590207ccedb4b0b3b305c970b7673de27de06c))
* define the names the FAQ and troubleshooting snippets use ([#1105](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1105)) ([51d8232](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/51d8232d8c5f12a2a8591a73aa019b542d1c2cb2))
* point agents at the organization rule for self-explanatory comments ([dd7f2b8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dd7f2b86642b439ebc29fa303e0e02ed1e52d8cb))
* **readme:** repin the brand icon to the transparent role marks ([#1090](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1090)) ([b19b1f7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b19b1f777be6171a08adfbbf4065d9be2fb96a42))
* **samples:** fix the async sample's install line and Docker hint ([#1092](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1092)) ([0dcdb5f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0dcdb5fdf026702d822a92659f56d9372f939804))
* use the Python yellow from the brand tokens in the site theme ([#1093](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1093)) ([02556d2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/02556d2fd579111f8cd330af896bd8af58261364))

## [1.12.1](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.12.0...v1.12.1) (2026-10-27)


### Documentation

* **readme:** repin the brand icon to the 2026-10-25 brand revision ([#1051](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1051)) ([7159590](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/715959028dcab9915eaab7478dca2228bc0345a5))
* **readme:** repin the brand icon to the cube redesign ([#1055](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1055)) ([f166be7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f166be7df70599af34bd353110075f9b092ee327))
* **readme:** repin the brand icon to the emblem-aligned keyline ([#1064](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1064)) ([c5fd64d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c5fd64d8d64ff8d31edd4db292ebb47dd8c6f250))
* **readme:** repin the brand icon to the shared white marks ([#1067](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1067)) ([e1ae6a4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e1ae6a4d1bc1d91bbb7028b07d344499b6997179))
* require human-readable agent communication ([#1056](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1056)) ([74afeb3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/74afeb36fe5cba4503b2b860dafdd0b19903af7b))

## [1.12.0](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.7...v1.12.0) (2026-10-25)


### Added

* **make:** run the live integration lane in make verify ([#1045](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1045)) ([4d168ea](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4d168eaf4b382841fe4880ba25db3f103319636d))
* **make:** write a verification summary under test-results/verify ([#1047](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1047)) ([ac596a5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ac596a54429da7c60a023de3a6bd9967216053c8))

## [1.11.7](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.6...v1.11.7) (2026-10-25)


### Documentation

* **agents:** remove agent-specific footer from commit example ([b51b29f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b51b29fa793d12d4ec54d9ef65adb3c43cd2ae5f))
* **agents:** remove tool-specific commit footer ([#1043](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1043)) ([b51b29f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b51b29fa793d12d4ec54d9ef65adb3c43cd2ae5f))

## [1.11.6](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.5...v1.11.6) (2026-10-24)


### Documentation

* **development:** fix stale pytest node ([#1034](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1034)) ([003dca4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/003dca4d9bf79aeb1d67814c5fa8e92824216405)), closes [#1033](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1033)

## [1.11.5](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.4...v1.11.5) (2026-10-24)


### CI

* **release:** restart release preparation after the abandoned 1.11.4 ([#1037](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1037)) ([3184d9b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3184d9b462bae6e2dd50d187e33abf83f44e5775)), closes [#1011](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1011)

## [1.11.4](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.3...v1.11.4) (2026-10-24)


### Documentation

* **agents:** require repository-local issue authoring checks ([#1012](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1012)) ([7a15ad7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a15ad76d2fb0e98e8026f0fae9c1324463db781))
* **architecture:** show Broker, CAS and CCI in the end-to-end driver communication flow ([#1016](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1016)) ([f8a9aa5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f8a9aa5d133835ce60455725259756550d50be64))
* **contributing:** fix single-test pytest node example ([c04a380](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c04a380f4b9a512fa8ecb892324fe6b59fde31b7)), closes [#881](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/881)
* enforce repository-local issue drafting ([7a15ad7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a15ad76d2fb0e98e8026f0fae9c1324463db781))
* **triage:** clarify PR overlap and execution precedence ([1d082cc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1d082ccccb2010b2ab6db474eaeca770431a6b7e)), closes [#1023](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1023)


### CI

* **release:** verify against the current cookbook and restart after the abandoned 1.11.3 ([#1007](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1007)) ([72bf7be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/72bf7be9fa0ab27454401b21972a080edd796d13))

## [1.11.3](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.2...v1.11.3) (2026-10-21)


### CI

* **release:** start release preparation after the abandoned 1.11.2 ([#1006](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1006)) ([b1a2dfe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b1a2dfe825c983a2114025b8cbaa82ff4da6c09d))

## [1.11.2](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.1...v1.11.2) (2026-10-21)


### Fixed

* **agent-review:** do not count empty reply-only Copilot records as review rounds ([#936](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/936)) ([adb141e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/adb141ee26d27e0466b1772496ccbbdff06556ff)), closes [#933](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/933)
* **compiler:** group a boolean expression used as a CASE THEN or ELSE value ([#985](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/985)) ([ffaf797](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ffaf797b0a6231190619fbd25ddb9c435c263c39)), closes [#982](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/982)
* **compiler:** group a boolean simple-case value operand ([#988](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/988)) ([1c738f7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1c738f745ce54e2d331344d4fc33496fdbf6205f))
* **compiler:** group boolean CAST and function arguments anywhere, and window items ([#972](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/972)) ([4042813](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/404281336d23086919d358dde3821e34fcef3483))
* **compiler:** group boolean expressions inside a CAST, a function or ORDER BY ([#969](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/969)) ([d6f22da](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d6f22da698fa0e1f02bd52088dc43cb311985e05))
* **compiler:** group EXISTS and AND/OR used as a SELECT-list item ([#967](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/967)) ([07f9de7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/07f9de7fd7a71f2695f41df97ab946c55f767a78)), closes [#966](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/966)
* **compiler:** keep the ORDER BY of aggregate_order_by() ([#994](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/994)) ([a95cd80](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a95cd80e91c927baf7f4294dc105d393377d31c4))
* **disconnect:** respect pycubrid error_source for overlapping CAS and server codes ([#938](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/938)) ([2f36731](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2f367311d4c5b321d61e9d93100b23d2f8008837)), closes [#916](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/916)
* **docs:** close four parser gaps in the deterministic documentation check ([#922](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/922)) ([3584728](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3584728aa90e6258b8c1db531c168b32e44677b7))
* **docs:** close the parser cases left by the second docs-check review ([#928](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/928)) ([245ef30](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/245ef30d389d3dddf7c75302ceb826bc5c2b4c29))
* **docs:** follow the configured site slugifier and toc id rules in the docs-check parser ([#958](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/958)) ([8a70c48](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8a70c48de815270652cb0a5dd7d982746d1fed72)), closes [#957](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/957)
* **docs:** port the shell substitution and quote fixes from pycubrid to the docs check ([#935](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/935)) ([0be57b5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0be57b5b6dc6c26e2f3665a8b9e5189e331163d5))
* **docs:** report issue-number lines in block quotes inside list items ([#930](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/930)) ([b2860a2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b2860a24e5c58de01fb1900d79e54747f5581d07))
* **docs:** sync the docs-check shell scanner with pycubrid ([#960](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/960)) ([047100a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/047100acdfee034cfdd6a17ae5bb60ce899e5c06)), closes [#959](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/959)
* **json:** reject boolean JSON path indices instead of rendering invalid array paths ([#917](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/917)) ([7744dd6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7744dd62e2477b25d2a904f115f3a8cce75f5f18))
* **scripts:** dispose reflection probe engine on every exit path ([#977](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/977)) ([1303262](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/13032624148045302d0edcdfe245a28ce4c20f01))
* **test:** keep the CUBRID 11.4 Docker test database in a named volume ([#1001](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1001)) ([85ec642](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/85ec6427c7f10e0b082ff3371680f54385dbcbfa)), closes [#1000](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1000)
* **test:** register the Docker test database for a stable host ([#998](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/998)) ([24759a9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24759a92444c98d920787ac31c9ba35d0695465c))
* **transactions:** retain pending isolation restoration after a failed begin retry ([#947](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/947)) ([2080f8b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2080f8bc71d48ce1e321d79d88429b52cced712c)), closes [#937](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/937)


### Documentation

* **agents:** name a maintainer's review as the standalone-agent alternative to Copilot ([#927](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/927)) ([6b3793a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6b3793a9dfc0d41f3ae975a246e1f54d2a22a328)), closes [#926](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/926)
* **async:** document the Python 3.15 limit of garbage-collected connection cleanup ([#909](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/909)) ([a0ec6a6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a0ec6a67043281262c1db6d499b2d2f1c9fc273f))
* **async:** make README quickstart examples runnable as standalone Python scripts ([#944](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/944)) ([09d07bf](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/09d07bffe8bd69f7d08e7bec8f6c470e1e8b8ae6))
* **contributing:** clarify good-first-issue access for human contributors ([#913](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/913)) ([7a2512f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a2512f4694ee5129081ad87a449cae8bb3d4a88))
* correct the documented boolean expression positions ([#986](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/986)) ([7c7958b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c7958be8e82fa49dd3fb56591ad5a5108e16e30))
* describe CAS error -4 as an interrupted statement ([#939](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/939)) ([2551c79](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2551c791676bf5bbdc374a118007dc023d2588bc))
* **onboarding:** lead with one synchronous SQLAlchemy path for CUBRID beginners ([#942](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/942)) ([a3d4916](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a3d49164b532d2485138da1ab647ecc8a856214c))
* **quickstart:** remove the lab container's anonymous volume with docker rm -f -v ([#949](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/949)) ([53d250a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/53d250ad18d04068ce66da7d429e9546480c6a94)), closes [#948](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/948)
* **site:** keep wrapped lines that start with an issue number from rendering as headings ([#924](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/924)) ([b9b4ff5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b9b4ff5b2c36d547a10dee0c83d803c56bc7f5b3))
* state the boolean expressions that still fail on CUBRID ([#971](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/971)) ([6dc4728](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6dc4728c7742917e551d64a39971ef1c366d5c57)), closes [#968](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/968)
* **structure:** finish the first-connection course with lessons 3 to 5 ([#956](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/956)) ([a472087](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a472087cb1e9b956b7aa1b0c338794b2f91e2480))
* **structure:** organize the site navigation by reader question ([#954](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/954)) ([a5c42a4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a5c42a4287a9f0a6930b11ddc84614dbacc780f8)), closes [#943](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/943)
* **structure:** split the first two first-connection lessons into their own pages ([#955](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/955)) ([6a85659](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6a8565987ebde18e367b2e60fffd5f21a2aade17))
* **types:** correct the namespace of reflected timezone types ([#973](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/973)) ([9480036](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9480036c1a184d6227c93562c67452ded57cfbc8)), closes [#882](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/882)
* **versioning:** identify development docs and distinguish candidate, abandoned and published versions ([#951](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/951)) ([7a0ba84](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a0ba84861786c4abae476bfbd67ab0b88fb0f7b))

## [1.11.1](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.11.0...v1.11.1) (2026-10-14)


### Fixed

* **alembic:** emit CUBRID-compatible SQL for nullability, dropped defaults and comments in alter_column ([#877](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/877)) ([45fe81a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/45fe81a8321076a484e1800b53d2f682ab49e484))
* **alembic:** render CUBRID collection member types with the dialect module prefix ([#884](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/884)) ([f3b00da](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f3b00daa8e9762320a7931360530c63e849dc8e4))
* **async:** support terminating garbage-collected async connections ([#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/894)) ([fb11bbc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb11bbca0ccae5d14e52d50f2647d55295280072))
* **compiler:** escape rendered literals for the server's actual backslash mode ([#874](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/874)) ([8969586](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8969586e1b52f96d9d2a72612dbf63316bad14c7)), closes [#863](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/863)
* **compiler:** forward compile options through CAST, ON DUPLICATE KEY UPDATE and collection members ([#875](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/875)) ([b3cc17b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b3cc17b070f46a99e23a35eca422cb157ca570cc))
* **compiler:** make on_duplicate_key_update() cacheable ([#893](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/893)) ([39361db](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/39361db81aa519c3216977bc3be9e086f4b907ce))
* **compiler:** reject foreign MERGE Column keys with colliding target names ([#895](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/895)) ([1a2379d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1a2379d1ed0610dde7ba0fa5225a7c658e367ff5)), closes [#847](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/847)
* **compiler:** render a CTE after INSERT INTO for insert from a CTE select ([#899](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/899)) ([a14b31a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a14b31aa6f8ed702cfebb93b2ed5b4e6ab289d64)), closes [#897](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/897)
* **compiler:** render Select.fetch() as LIMIT ([#880](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/880)) ([5edda8b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5edda8b09b6f90c60269da484b7afed80dc20c8a)), closes [#867](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/867)
* **dialect:** handle colons in reflected names, type classes in collections and join linting ([#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/891)) ([97c44ce](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/97c44cebb50e613ba6fcd88a5fec9492622084bd))
* **reflection:** fail closed on missing unique-index catalog reconciliation ([#896](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/896)) ([034eb34](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/034eb34bd98393af077a68f13c830ed3353da30c))
* **reflection:** limit has_table and table listings to the current owner on CUBRID 11.2 and later ([#876](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/876)) ([5a33ba8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5a33ba8bb43feb6f749bd7d511d13504bed91329))
* **reflection:** reflect expression, descending, filtered and prefix indexes ([#885](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/885)) ([64258de](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/64258de9e3e2ffc17d16388e40bcf772e95ef3b5))
* **reflection:** reflect string server defaults as quoted literals ([#878](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/878)) ([14eeafa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/14eeafa79fe2bbcdbb85973626faedcf0e8a8481))
* **types:** escape JSON path keys with JSON string syntax ([#879](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/879)) ([ade2741](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ade2741e264376806c916b0dbc31c8e8bf0a8539)), closes [#866](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/866)


### Documentation

* **agents:** correct stale entry points, integration commands and doc map in AGENTS.md ([#846](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/846)) ([340a587](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/340a587ae1cfe6f98123669f25555948f84255cd))
* **brand:** show the centered repository icon in the README and docs site ([#900](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/900)) ([db5ccdd](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/db5ccdd83787b3489cf61ed2f3b5fe641e171ca7)), closes [#886](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/886)
* **i18n:** update the Python requirement in the German README ([#837](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/837)) ([fcdb443](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fcdb443891cef3a2109e9f419b5ba374434401b9)), closes [#698](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/698)
* **i18n:** update the Python requirement in the Hindi README ([#839](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/839)) ([3f79d2d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f79d2db34694417f31b46f0573f2038d6c2a0ee)), closes [#699](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/699)
* **i18n:** update the Python requirement in the Russian README ([#840](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/840)) ([793b6ef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/793b6ef8d6a5b7a764b8589bef6d77b90da84fbf)), closes [#700](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/700)
* **roadmap:** move shipped 1.10.0 and 1.11.0 plans to completed history ([#844](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/844)) ([3d9dd99](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3d9dd99a33e79770d431172de8cb3de9950960c0))
* **types:** mark CUBRID BLOB/CLOB value reads as partial in the feature table ([#842](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/842)) ([a570ea4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a570ea4d3aa7f222553a925677e0b324b8b39cde))

## [1.11.0](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.10.0...v1.11.0) (2026-10-12)


### Added

* **python:** declare Python 3.15 support ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/807)) ([92d79eb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/92d79eb051bf07076a8572c01e5b61a7056b831e))


### Fixed

* **packaging:** cap SQLAlchemy below 2.2 to match the documented support matrix ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/777)) ([715349a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/715349a58f207facfdc43520ead2456f72eddbe4)), closes [#774](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/774)


### Documentation

* **agents:** add support-claim review checklist ([#784](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/784)) ([a8ffc4b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a8ffc4bbd2ae41279f86ca125dfaba242ff2909e))
* **agents:** replace stale performance planning snapshot with pointers ([#757](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/757)) ([f2b838a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f2b838a4e7fc418c63c0343c572bde1c2daf9c54))
* **ci:** clarify SQLAlchemy pre-release canary coverage ([#788](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/788)) ([85817ca](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/85817ca476e05604ba1347d6b99ff525da706489))
* correct the older closing-guard CHANGELOG notes ([#819](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/819)) ([a508694](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a508694d34ec8f66243c3a97f5f46adaf5c991bc))
* **driver:** clarify CUBRIDdb support and deprecated extras ([#781](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/781)) ([d20a6b2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d20a6b25cba37cc9d9a55aef330600242cd038e6))
* drop the stale nightly full-integration wording ([#792](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/792)) ([b0e95b2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b0e95b27bb46ac90d505897e280f6037d41ea670))
* **i18n:** update the Python requirement in the Chinese README ([#825](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/825)) ([6430aad](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6430aad77013ce353245258192371477ed70ddc1))
* label the compliance-lane pycubrid pin as the declared floor ([#801](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/801)) ([ea9392e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ea9392e8e5efea626a3777db3fb923ca7200b6ad)), closes [#479](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/479)
* name private vulnerability reporting as the preferred security channel ([#796](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/796)) ([98b746f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/98b746f00fa66268f3334088bca705f3fe786713))
* **python:** state the Python 3.11+ requirement in connection, driver and PRD docs ([#803](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/803)) ([8a6fb60](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8a6fb60c77dfc1c8c2db144328d37bc5ae420cf9))
* **release:** record live release-please evidence and candidate regeneration ([#817](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/817)) ([27134e0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/27134e081f2e7285f563e0fde54f301339ebb5a1))
* remove stale test_dml.py and unguarded counts from PRD/DEVELOPMENT ([#759](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/759)) ([c59c7db](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c59c7db92fc49769abeb832f1dce47fe48ca78f7))
* **review:** distinguish agent review routes and dispositions ([#802](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/802)) ([24743d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24743d604461fc681b84ecfadc0e4ec46b2c2668))
* **support:** distinguish current guarantees from historical evidence ([#783](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/783)) ([92307cf](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/92307cfcb856103827a488d5f4bf8895c02c192d))
* **types:** identify pycubrid 1.9.0 collection binding ([#782](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/782)) ([81fc4ff](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/81fc4ff7744d5a200c2077183c601125e21f09f0))

## [1.10.0](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.9.0...v1.10.0) (2026-10-08)


### Features

* **python:** require Python 3.11 or later ([#703](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/703)) ([f764d27](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f764d27d2f20ece8b2f914b61c5dc1776313b04e)), closes [#686](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/686)


### Documentation

* **agents:** align contributor ownership and good-first-issue guardrails ([#739](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/739)) ([41153c4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/41153c4d3d88cb7ce3beaf488ca508e40ab570ab)), closes [#733](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/733)
* **i18n:** add a Korean contribution guide ([#713](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/713)) ([fcc94b4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fcc94b47d764b7fffdc327da701c99a1d7054b60)), closes [#708](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/708)
* **i18n:** add the Korean documentation home page ([#712](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/712)) ([2966d51](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2966d5128c938f2ed32c8f173e226f2190bafa63)), closes [#707](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/707)
* **i18n:** correct Korean sections that fell behind the English wording ([#720](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/720)) ([7578501](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/75785012c55e95181b0144b08a669cc43bdaa411)), closes [#719](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/719)
* **i18n:** synchronize the Korean SUPPORT_MATRIX and FEATURE_SUPPORT and translate CI_POLICY in full ([#711](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/711)) ([6c3c7c8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6c3c7c88b3ab3ea3fc718daa23671074f6e10350)), closes [#706](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/706)
* **i18n:** translate SA_COMPAT, PRD and RELEASE_PLEASE_VALIDATION into Korean ([#714](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/714)) ([ff2dbdb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ff2dbdb1813c452ab93b4380b9bc1ce932cb92d4)), closes [#709](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/709)
* **licenses:** reproducible license inventory by install scope ([#755](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/755)) ([2c0390d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2c0390d41fef1891d0cc80b73c0eacdf2b70362a))
* **llms:** update the Python requirement in the canonical index ([#740](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/740)) ([c67f6af](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c67f6af859f71d203c76a8fac3e678f907918f7f)), closes [#702](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/702) [#685](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/685)
* **python:** state Python 3.11 or later in the README and quickstart ([#731](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/731)) ([4ee946d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4ee946dc8ab236bfe6ce0ae17e5358c52efd1b27)), closes [#695](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/695)
* **python:** update contributor and CI docs for Python 3.11 ([#718](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/718)) ([f31ff01](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f31ff0158821aabf6b4cd77bcaeeeedb2a5936ca)), closes [#696](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/696)
* **site:** generate heading anchors that match the links in the documents ([#722](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/722)) ([9c31e6a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9c31e6ad7b194d40046b5bde3b079f3da5aa96e4)), closes [#721](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/721)
* state one SQLAlchemy range on the documentation home page ([#717](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/717)) ([56d606f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/56d606fe62c0575463ea691311515bd3720d3094)), closes [#716](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/716)

## [1.9.0](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.8.0...v1.9.0) (2026-10-04)


### Features

* **types:** bind SET, MULTISET and SEQUENCE values through pycubrid typed collections ([#623](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/623)) ([f7abe8e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f7abe8e4fb907f8a18f0e917d322458bf1186176))


### Bug Fixes

* address disconnect-code audit follow-ups ([#578](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/578)) ([#582](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/582)) ([761f6cb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/761f6cb5b6bf8afc6cc867106ce671145f711ad8))
* **alembic:** count actual DDL calls in the safety checker ([#587](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/587)) ([99255be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/99255befeb9533bb890b5caf57e93cb7d22c0065)), closes [#447](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/447)
* **alembic:** require matching columns for a foreign key name match ([#668](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/668)) ([147d201](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/147d201abd618d51144afec67f77e6454bf41a3c)), closes [#624](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/624)
* **alembic:** treat CUBRID's reflected RESTRICT as the default referential action ([#622](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/622)) ([91a90ad](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/91a90adb3c9a36921edc105b038989970267215b))
* **ci:** isolate scheduled runs and publish the CI policy ([5eb6c26](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5eb6c26403c360d19237bbad5fbaecf3258f75dd))
* **ci:** synchronize the shared docs-reason empty-caption correction ([#649](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/649)) ([7432169](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7432169960f486040ac6ef23c3e355b9f4bea01e))
* clean up Docker when integration tests fail ([#508](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/508)) ([a4dcd75](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a4dcd75ddb4cc9e199d6b5d286d504e9842ca8c0))
* coerce catalog COUNT(*) in has_table()/has_index() ([#583](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/583)) ([#584](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/584)) ([b68e757](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b68e7574dc6a30a2b39401263665598eed2a8ced))
* **compiler:** emit REPLACE without rewriting INSERT INTO text inside prefixes, literals and comments ([#600](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/600)) ([d5c4f60](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d5c4f60c990c72cb12583ac8c453fc7087f1f05c))
* **compiler:** reject nonpositive explicit type lengths ([#662](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/662)) ([8b53e18](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8b53e1800e0022338c5234e4ac7c6fb2c9e9bd9f))
* **dialect:** classify pycubrid's malformed-reply error as a disconnect ([#681](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/681)) ([b8c00a7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b8c00a756e35e481dfce160221902a3b12fff948))
* **dialect:** forward URL query options such as charset and connect_timeout to pycubrid ([#599](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/599)) ([258cf00](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/258cf00d4961e2e65ca04b360df49372e4d58575))
* **dialect:** ignore disconnect phrases in server error text ([#676](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/676)) ([fb4eccd](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb4eccde05cb2f62ce365c27b083526ad93c6488))
* **dialect:** stop treating arbitrary numeric message prefixes as disconnect codes ([#620](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/620)) ([8562fc3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8562fc3e46e4be9f7b91fbe2ce0814f461a46a9d))
* **dialect:** treat an asyncio timeout cause as a disconnect ([#672](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/672)) ([caa3fbe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/caa3fbeec4d63f831192e967129acf98b9af5eea)), closes [#624](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/624)
* **dialect:** warn when CUBRIDdb is older than the tested 11.3 line ([#588](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/588)) ([4dbfe43](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4dbfe43bb551258bd9ce477d0578b855934b7e0d)), closes [#585](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/585)
* do not coerce BIT(length=0) to BIT(1) ([#478](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/478)) ([181f1f2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/181f1f261d64e652ae6149dbbc527bc07039a8fa))
* drop non-disconnect codes from the CUBRIDdb disconnect code table ([#577](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/577)) ([d77e006](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d77e006e967e5c3401e7b096d40402b43a29f6f2))
* invalidate pooled connections on CUBRID -111/-199/-224/-677 ([#571](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/571)) ([8aad4d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8aad4d64a86d2a3d2524431a66e985b127326642))
* isolate make integration cleanup ownership and handle termination signals ([#574](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/574)) ([6354821](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6354821c7ae26816f0cfb4cc19e0d8dc16938739))
* make integration waits for CUBRID, defaults to pycubrid and runs in CI ([#581](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/581)) ([600482b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/600482bd2e256ede7df06b7506217db21b5a17bd))
* **reflection:** accept whitespace in numeric type parameters ([#626](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/626)) ([11be5c9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/11be5c90fe2771668aa7e9730d446fdd299c8b07)), closes [#615](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/615) [#609](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/609)
* **reflection:** avoid fabricating ENUM and collection domains ([#635](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/635)) ([dd74cdb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dd74cdb292ee8733862e662647985b744b8504c9)), closes [#631](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/631)
* **reflection:** avoid false-empty constraints after DDL lookup failures ([09014a1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/09014a14938712a346b9e4cc02181e8510dcafa7))
* **reflection:** do not translate native -493 syntax errors into NoSuchTableError ([#454](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/454)) ([#455](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/455)) ([a581fa7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a581fa7aab3b5acfabfb6422cc37f4fe88a49cf4))
* **reflection:** keep the DDL fallback when the server version is unknown ([#675](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/675)) ([cc4aa9a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/cc4aa9a4727e997fa7d5c19c51588786b0ac3fa2)), closes [#624](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/624)
* reject explicit zero CHAR/NCHAR length ([#477](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/477)) ([2a792a2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2a792a2b9358b178df2512d5b0492de011d3c452))


### Performance Improvements

* **alembic:** register CubridImpl through the alembic.plugins entry point ([#616](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/616)) ([acfb626](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/acfb6262c20413e73fed54cae969f5f6923c4f04))
* **reflection:** avoid redundant DDL fallback for verified empty unique catalogs ([#629](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/629)) ([8f18ab5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8f18ab5e942e6552688410069b7fb5e66e577d80)), closes [#610](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/610)


### Documentation

* add MP4 demo tape + QUICKSTART video embed ([#346](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/346)) ([ed4893b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed4893b2945d06bfd811278b105466c09b212889))
* **alembic:** document Alembic import log lines on dialect load ([#561](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/561)) ([#562](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/562)) ([b96447e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b96447e9e11cb0781b43147460bba2e0e23edcd1))
* **compat:** clarify SQLAlchemy 2.1 support and canary ([#506](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/506)) ([40a7c05](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/40a7c053040cadd38182645b42cbc8cc8dc9d9a5))
* **contributing:** keep issue specifications current and assign owners ([#650](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/650)) ([7414fdb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7414fdbf6c513758b2f5590e55bcf7f3e361d68f))
* correct llms.txt capabilities and single-source the two indexes ([#579](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/579)) ([a30ab0c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a30ab0c90ae71407e3497e0529748ec7fd9a6d33))
* **demo:** prepare ORM and Alembic recording; defer MP4 embed ([#374](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/374)) ([ed4893b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed4893b2945d06bfd811278b105466c09b212889))
* derive Sphinx release from package version ([#499](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/499)) ([3f5c4f5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f5c4f5135bd3cc7f209905edc794419aa442e09))
* **development:** avoid duplicate installs of dev dependencies ([#663](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/663)) ([9ef691b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9ef691b8e0a85b8227ee81e7d64de721e1a162f8))
* make Quick Start use the recommended pycubrid driver ([#516](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/516)) ([20f0b23](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/20f0b23d2d992522e455c1eb587cd116bac9eb0e))
* mention repository and full offline test lanes ([#647](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/647)) ([e4b90f0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e4b90f050324154a23306a8b8b88ec05f2a28423))
* pin cookbook smoke-test fallback to the exact release ([#576](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/576)) ([ad47e3b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ad47e3bac6484d5dda4c8faa5b5736c58a363f21))
* **python:** announce Python 3.10 support retirement ([#665](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/665)) ([4221b25](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4221b252fabf2aa67b6d1c02cab531fa02ba1597))
* **reflection:** state when another owner's class reaches the DDL fallback ([#673](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/673)) ([7c676fa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c676fafe3bafcc7e85772328d22362cfae023ea))
* refresh current support claims and remove stale test statistics ([#643](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/643)) ([dd9bb4e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dd9bb4e8af6298ca686fcadac7b3379f89a16f5f))
* **release:** document release-please review and recovery ([#657](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/657)) ([a01c338](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a01c3385ed4d8f4327c6dae55c13b386cc07cdef))
* **types:** record the tested non-DBA ENUM reflection limitation ([#677](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/677)) ([112fde7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/112fde7d934b15a099ba9a044acc6429dd170e5d))
