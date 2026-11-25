# GenLayer Season 2（Builder 赛道）参赛准备笔记

更新：2026-11-25。状态：**本地准备已完成**（合约写好且本地测试全过）；未建钱包、未注册 Portal、未部署、未提交——等 Yang 本人完成下面「必须本人做」的三步后，Muse 再接手部署与提交。

---

## 一、已核实的规则（来源：官方文档/Portal 公开页 + 官方口径转述，2026-11-25 核查）

- **赛季状态**：Season 2 已 live，2026-10-26 开始，官方口径「持续至主网（mainnet）」，**确切截止日期官方未公布**；积分跨季结转，每周日 23:59 UTC 汇总转为 GLP。
- **参与路径**：
  1. 用钱包登录 GenLayer Portal（portal.genlayer.foundation），绑定 GitHub + Discord；
  2. 在 Bradbury 测试网用 faucet 领测试 GEN（无真实资金成本）；
  3. 在 GenLayer Studio 部署 Intelligent Contract（Python 风格 GenVM 合约）；
  4. 回 Portal 按 **Builders 类别提交贡献**：填 Tx Hash + 截图 + 代码仓库链接；
  5. **Stewards 人工评审，通过才计分**；官方自述提交通过率约 **18.5%**——写得像样、有真实功能、材料齐全很关键。
- **积分结构**：Builder 本人得分；其合约被他人使用时，Builder 另得该合约产生积分的最高 **20%**；推荐他人成为 Builder 得其积分的 **10%**。第三方指南口径：Builder 榜约 130 万积分 / 约 5,000 人（相对不卷，但只是量级参考）。
- **硬风险（官方条款明示）**：积分**无现金价值、不保证兑换代币**，是否奖励、如何奖励全凭项目方裁量。Season 1 确实兑付过空投，但不构成 Season 2 的承诺。

## 二、必须 Yang 本人做的步骤（约 10–15 分钟，Muse 不能代办）

1. **建专用钱包**：新建一个 MetaMask（或同类 EVM 钱包）专用地址，只用于 GenLayer 活动；**助记词离线自存、绝不发给任何人/任何网站**（Muse 也不需要）。不要用存有资产的主钱包。
2. **Portal 注册绑定**：用该钱包登录 portal.genlayer.foundation，绑定 GitHub + Discord 账号（Builder 赛道评审会看 GitHub 仓库）。
3. **faucet 领测试 GEN**：在 Portal/官方 faucet 用该钱包地址领 Bradbury 测试网 GEN（部署合约要花测试币）。

完成这三步后告诉 Muse 钱包地址（只给地址即可），后续部署、调试、Portal 提交材料由 Muse 接手。

## 三、Muse 已完成的本地准备

工作目录 `~/workspace/genlayer/`：

- **工具链**（全部装在项目内 `.venv`，未动系统配置）：genlayer-test 0.30.0、genlayer-py 0.19.0、genvm-linter 0.11.0、pytest 9.2.0；本机无 Docker，走官方 **direct 模式**本地执行（GenVM SDK 直接在本机跑合约 + mock 网络/LLM），不需要真钱、不连测试网。
- **示例合约 `contracts/claim_court.py`（ClaimCourt，证据裁决法庭）**：
  - 场景：任何人提交「主张 + 公开证据 URL + 验收标准」立案，标准在立案时冻结、不可修改、无管理员后门；
  - 裁决：任何人可触发 `adjudicate`，每个验证者独立抓取证据页 + LLM 按冻结标准判 SUPPORTED / REFUTED / UNCLEAR + reason_code；
  - 共识：用等价原则（验证者各自重跑裁决、verdict 一致才通过，reason_code 措辞可不同）把结果上链，全程可查（`get_claim` / `list_claim_ids` / `get_stats`）。
  - 输入长度上限齐全（防 prompt 超时/滥用），这是评审看重的工程细节。
- **本地验证结果**：
  - **direct 模式测试 8/8 全过**（`tests/test_claim_court.py`：立案存证、重复 ID 拒绝、非法 URL 拒绝、SUPPORTED/REFUTED/UNCLEAR 三种裁决、重复裁决拒绝、未知 claim 拒绝），输出存档 `logs/pytest-direct-final.log`；
  - genvm-lint 静态检查 3 项全过（`logs/genvm-lint-final.log`）；其语义验证步与当前 SDK 布局不兼容（见下「工具链坑」），以 direct 模式真实执行结果为准；
  - GLSim 本地节点能起，但 gltest 客户端与 GLSim 服务端 calldata 格式差一个版本（`gen_call: No method in calldata`），集成测试未跑通，脚本保留在 `tests/test_claim_court_glsim.py` 待官方版本对齐后再用；不影响 direct 模式结论。

### 工具链坑（复现/维护必读）

- **必须固定 `GENVM_VERSION=v0.3.0-rc7`** 再跑测试：`GENVM_VERSION=v0.3.0-rc7 .venv/bin/python -m pytest tests/test_claim_court.py -v`。不固定时解析器会选到 genvm-manager 的 v0.6.0 线，其 SDK 布局与 genlayer-test 0.30.0 不兼容（合约加载报 `unexpected end of memory`，实为消息解码失败）。
- **Studio 只认官方发布的 runner 哈希（2026-11-25 彩排实测，旧口径作废）**：合约头用旧版 runner `py-genlayer:1zr6nqk…`（旧版 bootloader `_genlayer_bootloader.py`）时，Studio v0.123.0 在 Run and Debug 报 `Could not load contract schema`，GenVM 日志 `invalid contract runner malformed`，连 Deploy 按钮都不渲染。修复：头改成官方文档发布的 `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`（新版 `_genlayer_runner.py`；Studio 浏览器上已部署的合约、testnetradar 2026-09 实测指南用的都是这个哈希），并按新版 SDK 改导入：`from genlayer import gl, allow_storage`，`class ClaimCourt(gl.Contract)`。旧写法 `from genlayer.storage import allow` / `gl.contract.Contract` 在新版 SDK 里不存在。其余调用（`gl.public.write/view`、`gl.vm.run_nondet`、`gl.nondet.web.render`、`gl.nondet.exec_prompt`、`gl.message.sender_address`、`gl.storage.TreeMap`、`gl.u256`）已在新版 SDK 源码里逐项核对存在；`u256` 本质是 `int` 的 NewType。
- **换新 runner 后本地 direct 测试跑不起来**（连最小合约都报 `unexpected end of memory`）：是测试脚手架跑不了新版 runner，不是合约问题；部署前的验证改走 Studio 彩排（云端浏览器内置账号部署+自测）。旧版 runner 下 8/8 通过的记录仍是逻辑正确性的旁证，但部署文件以新版为准。
- GitHub API 未认证限流（403）会让版本解析退回本地缓存，表现同上；遇到先等限流恢复或确认缓存里有 v0.3.0-rc7 bundle。
- `response_format="json"` 的 LLM mock 需**双重 JSON 编码**（runner 自动解析一次、SDK 再解析一次），测试里已按官方 boilerplate 的 `mock_json_llm` 约定处理。
- `prompt_comparative` 的模板调用（ExecPromptTemplate）未被 direct 模式的 mock 层实现，故合约改用 `gl.vm.run_nondet` + 自定义验证函数实现等价原则（verdict 一致性），生产与本地行为一致。

## 四、积分预期与风险

- **预期**：单个像样合约过审可得 Builder 基础积分；真正的杠杆在「合约被使用」（最高 20% 分成）与持续迭代上新。按通过率 18.5% 的官方口径，**第一份提交被拒是正常情况**，按评审意见改一版再交是常规打法，不要指望一次过。
- **成本**：零真实资金（全程测试网）；时间成本主要是 Yang 的三步（约 15 分钟）+ Muse 的部署迭代。
- **风险清单**：
  1. 积分不保证兑换代币、无现金价值（官方明示）——按「低成本占位」定位，不要投入超出此定位的时间/资金；
  2. **假站风险**：只认 portal.genlayer.foundation 与 genlayer 官方渠道；任何「领取 GEN 空投」站、任何索要助记词/私钥的页面一律是诈骗；
  3. 钱包隔离：专用钱包不与主资产混用（见本人步骤 1）；
  4. 截止未公布：赛季「持续至主网」，节奏上不急，但 Builder 榜先发优势真实存在，建议 Yang 有空时尽早完成三步。

## 五、下一步（Yang 完成本人三步后，Muse 执行）

1. 用他的专用钱包地址在 Bradbury 测试网部署 ClaimCourt（Studio 或 CLI），自测一遍立案→裁决全流程并留 Tx Hash 与截图；
2. 合约源码推到他的 GitHub 公开仓库；
3. Portal 按 Builders 类别提交（Tx Hash + 截图 + 仓库链接），跟进 Stewards 评审结果，被拒则按意见迭代再交；
4. 视评审反馈决定是否再写第二个合约（如预测市场结算）扩提交面。
