# Changelog

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
