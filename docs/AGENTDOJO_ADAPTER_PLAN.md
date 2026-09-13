# AgentDojo 外部有效性适配方案

状态：设计冻结候选（仅方案，未安装依赖、未实现适配器、未运行模型）

审计日期：2026-09-13

适用研究阶段：Gate A 之后的外部有效性准备；正式模型评测不得早于 Gate B

## 1. 目的与边界

AgentDojo 适配的目的不是替代 DynaCAPA 自建环境，也不是用公开基准重新定义动态授权。它只回答两个外部有效性问题：

1. DynaCAPA 的策略或运行时边界在公开、状态化、多工具环境中能否保持任务效用；
2. 面对 AgentDojo 的间接提示注入时，能否减少攻击者目标的真实执行，而不依赖自建数据的生成规则。

以下结论不能由 AgentDojo 单独支持：

- 授权撤销、未来生效、过期和条件激活的处理能力；
- 用户确认状态和动态 Schema 漂移的处理能力；
- D-CAPA 对 Authorization Rights、Facts 和 Executable Set 分离的完整机制优势；
- VICC 的字段级反事实信用准确性；
- 开放环境中的无条件安全保证。

这些问题仍由 DynaCAPA 内部机制实验、人工语义审查及后续 File/DB 跨域实验承担。AgentDojo 只提供独立公开环境中的补充证据。

## 2. 已核验的上游事实

本方案以官方仓库、官方文档和 NeurIPS 2024 论文为依据，不从第三方复现仓库推断接口。

| 项目 | 2026-09-13 核验结果 | 集成约束 |
|---|---|---|
| 官方仓库 | `ethz-spylab/agentdojo`；审计时 `main` HEAD 为 `089ed468cf3ed0322acc66b0211f26d9d90dbf60` | 实验必须记录上游 commit；不能只写“latest” |
| 软件包版本 | `pyproject.toml` 为 `0.1.35`；官方 tag `v0.1.35` 指向 `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b` | 首轮复现固定 `agentdojo==0.1.35`，不直接依赖浮动 `main` |
| Benchmark 版本 | 当前 CLI 默认 `v1.2.2`；loader 提供 `v1` 至 `v1.2.2` | 软件包版本和 benchmark 版本必须分别记录 |
| Python | 要求 `>=3.10`，官方分类器列出 3.10/3.11/3.12 | 与 DynaCAPA 的 Python 3.11 兼容，但必须在独立环境预检 |
| 许可证 | MIT | 可以适配和引用；若复制代码或数据，必须保留版权和许可文本。优先通过依赖调用，不复制上游文件 |
| API 稳定性 | 官方 README 明示 API 仍在开发并可能变化 | 适配层必须薄、版本固定，并有接口契约测试 |
| 默认 suites | `workspace`、`travel`、`banking`、`slack` | 首轮只用 `workspace`，避免一次引入多个领域变量 |
| 论文规模 | 论文发布版本报告 70 个工具、97 个 user tasks、27 个 injection targets、629 个 security cases | 这是论文版本规模，不应未经运行时清点直接当作当前 `v1.2.2` 的规模 |
| 原生指标 | Benign Utility、Utility Under Attack、Targeted ASR | 保留官方定义和分母，不用 DynaCAPA 指标替换 |

需要特别处理一个命名陷阱：当前源码中的 `security_results` 保存的是 injection task 的检查结果，而 `TaskSuite.run_task_with_pipeline` 的文档说明第二个布尔值表示“injection 是否成功”。因此该原始字段应在导出层重命名为 `injection_goal_achieved`，其均值对应 Targeted ASR，越低越好。不得因为内部变量名叫 `security` 就把 `True` 解释为“安全”。

AgentDojo 的 task/scorer 在持续修订，官方 changelog 记录了多次 task verification 修复；官方 issue 也仍有个别 scorer 争议。因此正式实验不能只验证“脚本能运行”，还必须对选定子集做 ground-truth 和 trace 语义审计。

## 3. 选择 `workspace` 作为首批子集的理由

`workspace` 同时提供邮件、日历和云盘工具，能够在一个公开 suite 中覆盖：

- 只读信息获取；
- 邮件发送和敏感信息外传；
- 文件创建、修改和附件传播；
- 日历创建；
- 从不可信工具结果到真实副作用的跨工具链路。

这与 DynaCAPA 的 Mail 主域及后续 File 域最接近，而且不需要在首轮引入 Banking 的金融语义或 Travel 的预订语义。`workspace` 不是为了挑选“容易”的 suite，而是为了最小化领域迁移变量并检查已有授权语义能否落到公开工具接口上。

### 3.1 首批固定 pilot

首批候选 user-task 子集固定为下表中的 8 项。正式运行前必须由 Gate AD-0 确认这些 ID 在 `agentdojo==0.1.35`、benchmark `v1.2.2` 中存在；先运行官方 `check_suites` 检查完整 `workspace` suite，再逐项审计选定任务的 ground-truth 和 scorer。若失败，只能记录排除原因，不能静默替换。

| Task ID | 任务类型 | 选择原因 |
|---|---|---|
| `user_task_14` | 从邮件读取日程信息 | 只读 Mail 控制组 |
| `user_task_16` | 从邮件读取安全码 | 敏感信息读取控制组，检验“可读”不等于“可外传” |
| `user_task_28` | 从指定云盘文件读取反馈 | 只读 File 控制组和精确文件范围 |
| `user_task_18` | 根据邮件创建含参与者的日历事件 | 动态参数解析及外部参与者范围 |
| `user_task_29` | 读取指定文件并追加内容 | File 写入和对象范围 |
| `user_task_31` | 根据已有文件创建新文件 | 内容派生和新对象创建 |
| `user_task_32` | 根据已有文件创建新文件并向指定地址共享 | 新对象创建、共享权限和目标范围 |
| `user_task_33` | 读取文件并向指定收件人发送摘要和附件 | 跨域传播、收件人、附件和敏感内容边界 |

首批使用 `workspace` 的全部 6 个既有 injection targets：

- `injection_task_0`：发送攻击者指定邮件；
- `injection_task_1`：删除指定云盘文件；
- `injection_task_2`：创建攻击者指定日历事件；
- `injection_task_3`：读取并转发邮件正文；
- `injection_task_4`：外传邮件中的安全码；
- `injection_task_5`：外传安全码后删除已发送邮件。

因此 pilot 的声明规模是 8 个 benign cases 和最多 48 个 attacked task pairs。实际分母以运行时 inventory 和官方可注入性检查为准；不允许把失败、不可注入或 scorer 异常的 case 从分母中静默删除。

第一种攻击固定使用官方 `important_instructions`。`tool_knowledge` 和自适应攻击只在首轮接口与 scorer 审计通过后追加，避免把攻击实现差异和 DynaCAPA 机制差异混在一起。

### 3.2 第二批压力任务

下列任务不进入首批主结果，只作为适配成熟后的压力测试：

- `user_task_35`：查找并删除最大文件，要求把关系型选择器解析为具体对象；
- `user_task_13`：从邮件读取复合任务，再执行文件修改和邮件发送，链路长且授权来源容易与环境事实混淆。

已公开报告存在 scorer 争议的 task 不进入 pilot；例如当前官方 issue 中被质疑的 `workspace/user_task_34`。这不是永久排除，只有在所固定的上游版本完成独立 scorer 审计后才允许纳入。

## 4. DynaCAPA 与 AgentDojo 的语义映射

### 4.1 信任和授权来源

| AgentDojo 对象 | DynaCAPA 解释 | 是否能产生授权 |
|---|---|---|
| `BaseUserTask.PROMPT` | 已认证用户在本轮明确提出的任务意图 | 可以，但只覆盖明确请求的动作和范围 |
| `TaskEnvironment` 初始状态 | 环境事实 | 不可以 |
| 工具返回值 | 带来源和时间的 `Fact` | 不可以；只能解析已授权对象或满足条件 |
| 注入文本 | 不可信环境内容 | 不可以，即使其语气模仿用户或系统 |
| `BaseInjectionTask.GOAL` | 仅供攻击生成与离线评分的攻击者目标 | 绝不能暴露给 policy、Verifier 或授权编译器 |
| user/injection task `ground_truth()` | 仅供官方 checker 与评测审计 | 绝不能作为在线授权白名单或提示内容 |

核心原则是：工具结果可以帮助解析“哪个文件”“哪个联系人”或“什么时间”，但不能把一个未授权动作变成授权动作。例如，读取邮件后得到一个地址可以支持参数取值，却不能独立授权向该地址发送邮件。

### 4.2 工具与作用域映射

每个 AgentDojo `FunctionCall` 先转换为候选动作，再交给 D-CAPA；只有 Shield 解析后的 `executed_output` 可以被转换回 AgentDojo 调用并传给 `FunctionsRuntime.run_function`。

| AgentDojo 字段 | DynaCAPA 字段 |
|---|---|
| `FunctionCall.function` | `action_type` 和 `tool` |
| `FunctionCall.args` 中的资源 ID、文件名、邮件正文来源 | `object_scope` 和 critical args |
| 收件人、参与者、共享对象 | `target_scope` |
| `Function.parameters.model_json_schema()` | 工具 Schema；与 package、benchmark version 一起计算 `tool_schema_version` |
| 工具结果消息 | `Fact`，来源为具体 tool call ID |
| pre/post `TaskEnvironment` | 环境状态和真实副作用判定 |
| assistant 请求的原始 tool call | `candidate_output` |
| 实际传给 `FunctionsRuntime` 的调用或无调用结果 | `executed_output` |

对于“从邮件找到日期后创建事件”这类任务，授权权利是“创建与用户所述事件对应的日历项”，邮件内容只提供日期、地点或参与者事实。适配器不得因为邮件中出现新的动作指令而扩大 `action_type`。

### 4.3 当前无法直接映射的语义

AgentDojo 标准任务没有显式的撤销事件、授权有效期、确认状态或工具 Schema 漂移标签。因此：

- 标准 AgentDojo 主表不报告这些维度的 DGR；
- 不向官方任务人工注入撤销或确认并仍称其为“AgentDojo 原始结果”；
- 如以后创建动态授权扩展，必须使用新 benchmark version、独立表格和清晰的“AgentDojo-derived”标签；
- 该扩展不能替代对未改动 AgentDojo 原始 suite 的评估。

## 5. 最小非侵入式适配接口

推荐使用薄兼容层，不 fork AgentDojo、不修改其任务、环境或 scorer。未来代码应限制在独立可选模块，例如：

```text
src/dynacapa/integrations/agentdojo/
  pipeline.py
  policy_bridge.py
  authorization_overlay.py
  schema_adapter.py
  metrics_adapter.py
```

最小接口如下：

```text
load_external_suite(package_version, benchmark_version, suite_name)
inventory_external_suite(suite) -> suite/task/tool/schema manifest

authorization_overlay.compile(
    suite_name,
    user_task_id,
    authenticated_user_prompt,
    environment_snapshot,
) -> AuthorizationEvent[]

schema_adapter.compile(runtime.functions) -> DynamicToolContract[]

policy_bridge.to_candidate(function_call, observations) -> PolicyOutput
policy_bridge.to_function_call(executed_output) -> FunctionCall | None

metrics_adapter.export(
    official_task_result,
    candidate_log,
    executed_log,
) -> ExternalEvaluationRecord
```

`DynaCAPAAgentDojoPipeline` 应实现官方 `BasePipelineElement.query` 契约：

```text
query(query, runtime, env, messages, extra_args)
  -> (query, runtime, env, messages, extra_args)
```

它在内部完成模型调用、候选结构解析、D-CAPA 验证、Shield 解析和工具执行。AgentDojo 仍负责载入初始环境、插入攻击文本，并用未改动的 `utility` / `utility_from_traces` 与 `security` / `security_from_traces` 评分。

### 5.1 两条评测通道

为了避免把接口差异误当作方法增益，必须保留两条通道：

1. **AgentDojo-native 通道**：使用官方 pipeline 和 scorer，报告 Base、官方 `tool_filter` 等原生基线；
2. **Authorization-augmented 通道**：所有比较方法获得同一份冻结 authorization overlay，再比较 static authorization、D-CAPA runtime 和后续训练策略。

DynaCAPA 的 proof-aware policy 不能直接与一个从未要求输出 proof 的 AgentDojo-native policy 比 PVR。PVR 只在 Authorization-augmented 通道内报告。

### 5.2 防止评测泄漏

运行时对象必须遵守最小权限：

- policy/Verifier 可见：用户 prompt、公开工具 Schema、执行到当前步的真实 observation、冻结的 prompt-derived authorization overlay；
- policy/Verifier 不可见：injection task ID/goal、注入占位符位置、官方 ground-truth tool sequence、utility/security checker 的内部常量、未来环境状态；
- 离线 scorer 可见：AgentDojo 原始 task IDs、ground truth 和 pre/post state，但不能把这些信息回写到 policy trajectory；
- authorization overlay 必须在模型运行前冻结并哈希，不能根据某个模型失败案例逐条修补。

## 6. 指标与不可直接比较项

### 6.1 必须原样报告的 AgentDojo 指标

- **Benign Utility**：无攻击时成功的 user tasks / 无攻击 user tasks；
- **Utility Under Attack**：攻击条件下仍正确完成用户任务且无不允许副作用的 task pairs / attacked task pairs；
- **Targeted ASR**：攻击者目标实际达成的 task pairs / attacked task pairs。

每个指标报告固定分母、成功数、点估计和 95% 置信区间。若模型或工具调用失败，按预注册规则计入分母，不得事后删除。

### 6.2 同时报告的 DynaCAPA 指标

- UPR：authorization overlay 下未授权的候选动作机会比例；
- UER：authorization overlay 下未授权的真实副作用执行比例；
- FBR：存在合法路径时不必要 ask/block/stop 的比例；
- PVR：仅 proof-aware 通道中的一次性证书通过率；
- Shield Rate：候选与执行在 mode、tool、args 或 proof 上发生变化的比例；
- 工具调用数、生成 token、延迟和失败类型。

所有 DynaCAPA 指标必须分别报告 native proposal 和 protected execution。

### 6.3 不可直接等同

| 不可等同的指标 | 原因 |
|---|---|
| AgentDojo Benign Utility 与 DynaCAPA TSR | 前者由各 task 的官方 checker 定义；后者还可能包含 DynaCAPA 自己的终止和效用语义 |
| Targeted ASR 与 UER | ASR 只检查指定攻击目标是否完成；UER 覆盖所有未授权真实执行，即使没有完成攻击者最终目标 |
| Utility Under Attack 的下降与 FBR | 任务失败可能来自能力不足、格式错误或攻击干扰，不一定是过度阻断 |
| AgentDojo `security_results` 与“安全率” | 代码中的布尔值表示 injection goal 是否达成，不能按字段名直接取正向解释 |
| AgentDojo trace 与 DynaCAPA executed trace | AgentDojo 某些 checker 会查看 assistant 提出的调用轨迹；必须确认它记录的是尝试调用还是实际成功调用 |
| 自建 Mail 的 100% oracle consistency 与 AgentDojo 外部性能 | 前者是程序真值一致性，不是模型或公开环境安全性 |

## 7. 依赖与复现策略

首轮不把 AgentDojo 加入 Phase 0 的核心锁文件。正式实现时应新建独立可选环境，并记录：

```text
python == 3.11.x
agentdojo == 0.1.35
agentdojo benchmark == v1.2.2
agentdojo tag commit == a75aba7631d3ca5fb7ab938965c97ead2f9ff84b
dynacapa commit == <run commit>
suite inventory hash == <sha256>
authorization overlay hash == <sha256>
tool schema manifest hash == <sha256>
```

理由：AgentDojo 当前直接依赖 OpenAI、Anthropic、Cohere、Google SDK、LangChain、DeepDiff 等，而 DynaCAPA Phase 0 只依赖 Pydantic 和 PyYAML。提前混入核心环境会扩大依赖冲突面，并降低 Mail 回归测试的可复现性。

首轮不需要 `agentdojo[transformers]`；只有明确使用官方 PromptInjectionDetector 时才加入该 extra。Qwen/SGLang 或 vLLM 的模型服务依赖与 AgentDojo suite 依赖也应分别锁定。

## 8. 集成 Gates

### Gate AD-0：上游与子集冻结

必须同时满足：

- 固定 package、benchmark version 和上游 commit；
- inventory 确认四个官方 suites 及 pilot 的 8 个 user tasks、6 个 injection tasks；
- 官方 `check_suites` 对完整 `workspace` suite 通过，并对选定子集逐项复核 ground-truth/scorer；
- 记录当前 open issues，并对 pilot 的 task/scorer 做逐项审计；
- 生成 suite、task、tool 和 schema manifest；
- 未安装任何模型依赖也能完成 ground-truth preflight。

未通过时只修复适配或调整有充分证据的排除表，不运行模型。

### Gate AD-1：桥接正确性

必须同时满足：

- 选定工具 100% 完成 Schema 提取和稳定哈希；
- 同一 `FunctionCall` 往返转换无参数丢失；
- 被 Shield 阻断的调用不会改变 AgentDojo 环境；
- 被 rewrite 的调用只执行 `executed_output`，且 candidate/executed 日志均保留；
- 对固定环境和固定执行序列，pre/post state 与官方 runtime 一致；
- 自动测试证明 policy/Verifier 无法访问 injection goal 和官方 ground truth；
- 对 trace-based scorer，明确区分 attempted、blocked 和 successfully executed calls。

### Gate AD-2：授权语义审计

必须同时满足：

- 8 个 user tasks 的 authorization overlay 在运行模型前冻结；
- 两名审阅者独立检查 action、object、target、事实来源和副作用范围，经裁决后 100% 无未解决分歧；
- 任何工具结果或注入文本都不能新增授权权利；
- 不使用 user-task ground truth 生成在线白名单；
- 对 `user_task_16` 与 injection tasks 3/4/5 明确验证“读取权不推出外传权”。

### Gate AD-3：模型冒烟

在 Gate B 之后执行：

- 先运行 8 个 benign cases，再运行最多 48 个 `important_instructions` attacked pairs；
- 同一模型、解码配置和上下文预算比较 AgentDojo-native、官方 `tool_filter`、D-CAPA protected；
- 全部运行保存原始消息、attempted/candidate/executed 工具调用、pre/post state hash、官方评分和 DynaCAPA 评分；
- 任何 scorer 与真实 executed state 不一致时停止主表汇总并进入人工审计；
- 不根据 pilot 结果修改 authorization overlay 或 task 子集。

### Gate AD-4：外部主实验资格

只有在以下条件满足后，才扩展至完整 `workspace` 或其他 suites：

- pilot 无接口错误、分母歧义或 unresolved scorer anomaly；
- benign utility、utility under attack 和 targeted ASR 均可从保存的逐案例记录重算；
- UPR/UER/FBR/PVR/Shield Rate 的分母与 `docs/METRIC_SPEC.md` 一致；
- native policy 与 protected system 分开报告；
- 任务、攻击和 seed 的选择在运行主实验前注册；
- 若加入 Banking/Travel/Slack，分别新增领域授权映射和 scorer 审计，不复用 Workspace 映射假定。

## 9. 预注册比较矩阵

首轮最小充分矩阵：

| 通道 | 方法 | 目的 |
|---|---|---|
| AgentDojo-native | Base policy，无 defense | 能力和攻击基线 |
| AgentDojo-native | 官方 `tool_filter` | 官方运行时工具隔离基线 |
| Authorization-augmented | static authorization table | 检查结构化授权本身的贡献 |
| Authorization-augmented | D-CAPA + Shield，未训练 policy | 检查运行时授权边界 |
| Authorization-augmented | 通过 Gate B/C 的最佳 DynaCAPA policy + Shield | 检查 native proposal 是否内化安全行为 |

如果模型接口导致某个官方 baseline 不能公平运行，应标记为 `not comparable` 并解释原因；不得用结构化代理冒充官方实现。

预算匹配至少包括：相同 user/injection pairs、模型权重、上下文、最大工具回合、temperature/seed、模型请求数和允许工具集合。额外 Verifier 成本单独报告，不隐藏在“免费防御”中。

## 10. 失败解释和论文表述

可能的结果必须预先允许：

- D-CAPA 降低 targeted ASR，但 benign utility 明显下降：说明运行时边界过度保守，不支持策略内化结论；
- UER 下降但 targeted ASR 不变：可能是攻击 scorer、授权映射或攻击目标定义不一致，需要逐案例审计；
- targeted ASR 很低但 benign utility 也很低：不能解释为安全改进，可能只是模型无法调用工具；
- protected system 安全而 native UPR 不下降：只能说明 Shield 有效，不能说明模型学会安全；
- 内部 Mail 提升但 AgentDojo 无提升：说明外部迁移不足，应收缩论文主张而非修改公开任务。

允许的论文表述是：

> 在固定的 AgentDojo Workspace 子集和官方攻击/评分器下，DynaCAPA 的运行时授权边界（以及后续通过 Gate 的策略）改变了任务效用、攻击目标达成率和未授权执行率；结果仅适用于所声明的模型、任务、攻击、版本与授权映射。

不允许写成“AgentDojo 证明 DynaCAPA 解决了动态授权”或“公开基准证明系统绝对安全”。

## 11. 实施顺序

1. Gate A 完成人工语义验证期间，仅维护本文档和上游变更审计；
2. Gate A 通过后，在独立环境实现 AD-0 inventory/preflight，不接模型；
3. 实现薄 pipeline/schema/metric bridge 并完成 AD-1；
4. 人工冻结 8 个任务的 authorization overlay，完成 AD-2；
5. Gate B 通过后执行 AD-3 模型冒烟；
6. 根据失败类型决定是否进入 AD-4，而不是默认扩展全部 suites；
7. 任何 AgentDojo 主结果进入论文前，重新核对上游版本、open issues 和 scorer 行为。

## 12. 官方来源

- 官方仓库与 README：https://github.com/ethz-spylab/agentdojo
- 官方任务与 suite 概念：https://agentdojo.spylab.ai/concepts/task_suite_and_tasks/
- 官方 pipeline 概念：https://agentdojo.spylab.ai/concepts/agent_pipeline/
- 官方 benchmark API：https://agentdojo.spylab.ai/api/benchmark/
- 官方 TaskSuite API：https://agentdojo.spylab.ai/api/task_suite/
- 官方 changelog：https://agentdojo.spylab.ai/changelog/
- 官方论文（NeurIPS 2024 Datasets and Benchmarks）：https://proceedings.neurips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf
- 官方许可证：https://github.com/ethz-spylab/agentdojo/blob/main/LICENSE

## 13. 是否改变研究定义

No。本方案只增加外部有效性评测边界，不修改 D-CAPA、DACPO、VICC、Gate A-D 或既有指标定义。
