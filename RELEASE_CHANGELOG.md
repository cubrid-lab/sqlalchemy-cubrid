# Changelog

## [1.10.1](https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.10.0...v1.10.1) (2026-10-11)


### Fixed

* **packaging:** cap SQLAlchemy below 2.2 to match the documented support matrix ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/777)) ([715349a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/715349a58f207facfdc43520ead2456f72eddbe4)), closes [#774](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/774)


### Documentation

* **agents:** add support-claim review checklist ([#784](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/784)) ([a8ffc4b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a8ffc4bbd2ae41279f86ca125dfaba242ff2909e))
* **agents:** replace stale performance planning snapshot with pointers ([#757](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/757)) ([f2b838a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f2b838a4e7fc418c63c0343c572bde1c2daf9c54))
* **ci:** clarify SQLAlchemy pre-release canary coverage ([#788](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/788)) ([85817ca](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/85817ca476e05604ba1347d6b99ff525da706489))
* **driver:** clarify CUBRIDdb support and deprecated extras ([#781](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/781)) ([d20a6b2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d20a6b25cba37cc9d9a55aef330600242cd038e6))
* drop the stale nightly full-integration wording ([#792](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/792)) ([b0e95b2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b0e95b27bb46ac90d505897e280f6037d41ea670))
* label the compliance-lane pycubrid pin as the declared floor ([#801](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/801)) ([ea9392e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ea9392e8e5efea626a3777db3fb923ca7200b6ad)), closes [#479](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/479)
* name private vulnerability reporting as the preferred security channel ([#796](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/796)) ([98b746f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/98b746f00fa66268f3334088bca705f3fe786713))
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
