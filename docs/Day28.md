# Day 28：用自己的语言讲清 Transformer 与 LLM 核心原理

Day 27 已经整理了 Python 与后端面试题，学习计划也完成了提交。不过当前的 `docs/appendix/Day27-Python与后端面试回答.md` 仍然只有 9 个标题，没有留下实际回答。今天先把这个记录补齐，再进入月计划中的 Transformer 与 LLM。当前 Mini RAG 项目通过 API 调用大模型，并使用 BGE 模型生成 Embedding，因此不需要训练或修改模型代码；今天的目标是看懂一次 Transformer 信息流，完成一个 Temperature 小实验，并把 11 个核心概念整理成能口述的面试回答。

今天不要追求推导整篇 Transformer 论文。抓住一条主线即可：

```text
输入 Token
→ 加入位置信息
→ Q、K、V 与 Attention
→ Multi-head Attention
→ Residual 与 LayerNorm
→ 多层堆叠
→ 输出下一个 Token 的概率
→ 按 Temperature 等参数采样
```

---

# 一、先补齐 Day 27 留下的回答记录

打开项目并检查状态：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
git status --short
git log -2 --oneline
```

当前工作区应该干净，最近一次提交应是 Day 27。

打开昨天的回答笔记：

```powershell
code "docs\appendix\Day27-Python与后端面试回答.md"
```

目前文件只有题目标题。先不要重新抄写 Day 27 的长篇参考答案，而是根据昨天已经理解的内容，在每个标题下补 3～5 句自己的话。每道题至少包含：

```text
它是什么或核心区别
一个 Mini RAG 项目中的例子
一个边界或常见误解
```

例如 `async/await` 可以简短写成：

```markdown
`async def` 定义协程函数，`await` 用来等待一个可等待对象。
等待网络 I/O 时，事件循环可以先处理其他任务。
项目的 `LLMService.chat()` 使用 `await client.post()` 等待 LLM API。
异步不会让大模型生成得更快，也不会自动加速同步的 Embedding 和 FAISS 计算。
```

如果昨天并没有实际完成口述，就如实补做，不要因为 Day 27 已经提交而把空白标题当成已经掌握。补完后保存，今天提交时一起提交这个修正。

---

# 二、从当前项目找到 LLM 与 Transformer 的联系

今天不会在项目里实现 Transformer，但已经有三个真实联系：

```text
app/services/llm_service.py
→ 把 messages 发给大模型，并接收生成结果

app/services/embedding_service.py
→ 使用 BGE 模型把文本编码为向量

app/services/rag_service.py
→ 先检索 Context，再让生成模型根据 Context 回答
```

用下面的命令查看相关代码：

```powershell
Select-String `
    -Path app\services\llm_service.py,app\services\embedding_service.py,app\services\rag_service.py `
    -Pattern 'model|messages|stream|encode|prompt|answer'
```

重点观察 `llm_service.py` 的请求体：

```python
payload = {
    "model": self.model,
    "messages": [...],
    "stream": False,
}
```

这里调用的是已经训练好的模型。当前后端只负责组织输入、发送请求和处理输出，并不知道服务端模型的每一层参数。

还要注意，当前请求体没有显式提供 `temperature`。这表示生成时使用服务商或模型的默认值，不代表 Temperature 不存在，也不代表它固定等于 0。

Embedding 模型和聊天模型都可能基于 Transformer，但任务不同：

```text
Embedding 模型
→ 把文本压缩成适合相似度比较的向量

生成式 LLM
→ 根据已有 Token 的上下文预测后续 Token
```

不要把“项目中有 Embedding”直接说成“Embedding 模型就是 GPT”。

---

# 三、先建立 Transformer 的整体图景

Transformer 的核心作用，可以先用一句话说明：

> 它让序列中的每个 Token 根据当前任务，从其他 Token 中选择需要的信息，再经过多层变换形成上下文相关的表示。

例如句子：

```text
小明把书放进书包，因为它很轻。
```

模型处理“它”时，不能只看“它”本身。它需要结合“书”和“书包”等上下文，判断哪些词与当前理解更相关。Attention 就是在做这种“根据当前 Token，动态汇总其他 Token 信息”的工作。

一次简化的信息流是：

```text
Token ID
→ Token Embedding
→ 加入位置信息
→ Attention 汇总上下文
→ 前馈网络进一步变换
→ Residual 保留原信息
→ LayerNorm 稳定数值
→ 重复多层
```

真实模型还会包含激活函数、前馈网络、掩码、输出投影等细节。今天重点是能说清主要部件之间的关系，不要求背出所有张量形状。

---

# 四、理解 Attention 与 Q、K、V


[[QKV例子详解]]

## Attention 是什么

Scaled Dot-Product Attention 的常见公式是：

```text
Attention(Q, K, V) = softmax(QKᵀ / √dₖ)V
```

可以按四步理解：

```text
1. 用 Q 和每个 K 做点积，得到相关性分数
2. 除以 √dₖ，避免维度增大后点积过大
3. 用 softmax 把分数变成总和为 1 的权重
4. 用这些权重对 V 做加权求和
```

生活化地理解：

```text
Q（Query）
→ 当前 Token 正在寻找什么信息

K（Key）
→ 每个 Token 用什么特征表明“我可能相关”

V（Value）
→ 如果这个 Token 被关注，真正传递什么内容
```

Q、K、V 不是人为给每个词写的三个标签。它们通常由输入表示 X 分别乘以可训练矩阵得到：

```text
Q = XWQ
K = XWK
V = XWV
```

模型训练时会学习 `WQ`、`WK`、`WV`，（这里WQ是一个矩阵）从数据中形成适合任务的匹配和信息传递方式。

## 为什么要除以 `√dₖ`

向量维度较大时，点积的绝对值通常也会变大。直接送入 softmax，概率可能过早变得非常尖锐，梯度不容易训练。除以 `√dₖ` 是一种尺度控制，让数值更稳定。

## 一个两 Token 的小例子

假设当前 Q 与两个 K 的缩放后分数分别是：

```text
0.7 和 0.0
```

softmax 后的权重大约是：

```text
0.67 和 0.33
```

如果两个 Value 分别是：

```text
V1 = [1, 0]
V2 = [0, 2]
```

加权结果约为：

```text
0.67 × [1, 0] + 0.33 × [0, 2]
= [0.67, 0.66]
```

这说明 Attention 输出不是简单复制某一个 Token，而是按相关性组合多个 Value。

## 容易误解的地方

Attention 权重大，只能说明模型在当前层、当前头和当前输入下赋予了更大的权重。它不一定等价于人类可以直接解释的“因果原因”，也不是检索系统的正确概率。也就是说 Attention 权重回答的是“模型当前更关注谁”，而不是“谁一定是原因”，更不是“谁有多大概率是正确答案”。

---

# 五、理解 Multi-head Attention 与位置编码

## Multi-head Attention

单头 Attention 只有一组 Q、K、V 投影。Multi-head Attention 会使用多组投影并行计算，再把各个头的结果拼接和投影。

直观上，不同头有机会学习不同关系，例如：

```text
某个头更关注局部搭配
某个头更关注较远的指代
某个头更关注句法或语义关系
```

这样比只用一个很大的注意力计算更有表达能力。

但不要回答成“第 1 个头一定负责语法，第 2 个头一定负责指代”。这些作用是模型通过训练形成的，不保证每个头都有固定、清晰、可人工命名的职责。

## 为什么需要位置编码

纯粹的 Self-Attention 根据内容计算相关性，本身没有天然的先后顺序概念。下面两句话包含相似的词，但含义不同：

```text
小明批评了小王
小王批评了小明
```

模型必须知道 Token 在序列中的位置。位置编码会把位置信息加入表示，让模型区分第几个 Token 以及相对距离。

常见方法包括：

```text
固定的正弦、余弦位置编码
可学习位置向量
RoPE 等相对位置信息方法
```

面试时不需要在今天展开 RoPE 公式，只要能说明“Attention 本身不表达顺序，因此需要额外注入位置关系”即可。

生成式 GPT 还会使用因果掩码，让当前位置不能看到未来 Token。否则训练时模型会提前看到要预测的答案。

---

# 六、理解 Residual 与 LayerNorm

## Residual 是什么

Residual Connection 常写成：

```text
输出 = 输入 + 子层变换(输入)
```

它不是完全丢掉原表示后再生成一个新表示，而是保留输入，并在上面叠加本层学到的变化。

主要作用可以概括为：

```text
保留原始信息
让梯度更容易跨越很多层传播
帮助深层网络训练
```

可以把它理解成“在原稿上做增量修改”，而不是每经过一层都从空白纸重新写。

## LayerNorm 是什么

LayerNorm 会对一个样本的特征维度做归一化，再使用可学习参数调整。它有助于控制不同层之间的数值尺度，使深层网络的训练更稳定。

不要简单说“LayerNorm 把所有值都永久变成均值 0、方差 1”。归一化后通常还有可学习的缩放和偏移，而且它在具体架构中的放置位置可能是 Pre-Norm 或 Post-Norm。

## 两者的关系

Residual 主要解决信息与梯度传递问题，LayerNorm 主要帮助数值尺度稳定。它们经常一起出现，但不是同一种操作，也不能互相替代。

---

# 七、区分 BERT 与 GPT

## BERT 的核心思路

经典 BERT 使用 Transformer Encoder，通过双向上下文理解一个 Token。预训练中的代表任务是 Masked Language Modeling：遮住一部分 Token，再根据左右两侧上下文预测它们。

它更自然地适合：

```text
文本分类
信息抽取
句子表示
理解型任务
```

[[BERT-适合任务解释]]

## GPT 的核心思路

GPT 使用带因果掩码的 Transformer Decoder，按从左到右的方式预测下一个 Token：

```text
P(xₜ | x₁, x₂, ..., xₜ₋₁)
```

生成时把新 Token 接回上下文，再继续预测下一个 Token，所以天然适合连续文本生成。

## 面试时怎样比较

可以先抓住这条主线：

```text
BERT
→ Encoder、双向上下文、遮盖词预测、偏理解

GPT
→ Decoder、因果注意力、下一个 Token 预测、偏生成
```

这是经典架构的概括，不表示 BERT 完全不能生成，也不表示 GPT 只能生成、不能完成分类或抽取。现代模型会通过提示、微调和不同架构扩展任务能力。

当前项目中的聊天 API 调用生成式 LLM；`BAAI/bge-small-zh-v1.5` 则用于生成检索向量。回答时应区分“生成回答”和“编码为向量”这两个用途。

---

# 八、区分训练与推理

## 训练阶段

训练的核心流程是：

```text
输入训练样本
→ 前向计算
→ 计算预测与目标的损失
→ 反向传播计算梯度
→ 优化器更新模型参数
```

训练需要保存反向传播所需的中间结果，通常比单次推理占用更多显存和计算资源。

## 推理阶段

推理时参数通常固定，不再反向传播。生成式模型的推理又可以分成：

```text
Prefill
→ 一次处理已有 Prompt，建立上下文表示和 KV Cache

Decode
→ 每次生成一个新 Token，再继续生成下一个
```

训练时已知完整目标序列，可以较多地并行计算各位置；自回归推理时后一个 Token 依赖前一个新生成的 Token，因此 Decode 有明显的串行性。

当前 Mini RAG 项目只做推理调用：

```text
项目构造 messages 或 RAG Prompt
→ 服务商加载已经训练好的模型
→ 模型推理生成回答
→ API 返回文本
```

上传 PDF、建立 FAISS 索引不是在训练 LLM，也不会修改 LLM 参数。

---

# 九、理解 KV Cache

[[KV Cache详解]]

自回归模型每次只生成一个新 Token。如果生成第 100 个 Token 时把前 99 个 Token 的所有 K、V 都重新计算一遍，会产生大量重复工作。

KV Cache 的做法是：

```text
第一次处理 Prompt
→ 保存各层历史 Token 的 K 和 V

生成新 Token
→ 只计算新 Token 的 Q、K、V
→ 新 Q 与缓存的历史 K 比较
→ 使用缓存的历史 V 汇总信息
→ 把新 K、V 加入缓存
```

为什么主要缓存 K 和 V，而不是把历史 Q 全部缓存下来？

```text
生成当前 Token 时，需要的是当前 Q 去查询所有历史 K，
再用注意力权重汇总历史 V。
历史 Q 不参与当前这次查询。
```

KV Cache 的取舍是：

```text
优点：减少重复计算，显著加快逐 Token 生成
代价：占用额外显存，且随层数、上下文长度和并发数增加
```

所以更长上下文并不是“完全免费”，它会影响 Prefill 计算以及 KV Cache 的内存占用。

---

# 十、用小实验理解 Temperature

模型输出的是每个候选 Token 的 logits。Temperature 会在 softmax 前缩放 logits：

```text
softmax(logits / T)
```

一般来说：

```text
T 较低
→ 概率分布更尖锐，更偏向最高概率 Token

T 较高
→ 概率分布更平坦，低概率 Token 更有机会被选中
```

在项目根目录运行下面的纯 Python 小实验，不会调用 LLM API，也不会修改文件：

```powershell
@'
import math

logits = [2.0, 1.0, 0.0]

for temperature in [0.5, 1.0, 2.0]:
    scaled = [value / temperature for value in logits]
    exps = [math.exp(value) for value in scaled]
    total = sum(exps)
    probabilities = [value / total for value in exps]
    rounded = [round(value, 3) for value in probabilities]
    print(f"T={temperature}: {rounded}")
'@ | python -
```

预期得到接近：

```text
T=0.5: [0.867, 0.117, 0.016]
T=1.0: [0.665, 0.245, 0.09]
T=2.0: [0.506, 0.307, 0.186]
```

观察：Temperature 改变的是概率分布，不是把模型“知识量”调高或调低。高 Temperature 不等于模型更聪明，只是采样更分散，创造性和错误风险都可能增加。

低 Temperature 也不等于所有请求必然逐字相同。服务端实现、并行计算、模型版本和其他采样参数都可能影响结果。

当前项目的 RAG 问答偏事实准确，通常适合较低的随机性；但今天只理解参数，不修改 `llm_service.py`，也不产生额外 API 费用。

---

# 十一、区分 LoRA 与量化

## LoRA 是什么

完整微调会更新大量模型参数，成本很高。LoRA 的思路是冻结原权重 `W`，只训练一个低秩增量：

```text
W' = W + BA
```

其中 `A` 和 `B` 的秩远小于原矩阵维度，因此需要训练和保存的参数更少。

LoRA 的主要价值：

```text
降低微调的可训练参数量
减少训练显存和存储开销
可以为不同任务保存不同的轻量适配器
```

LoRA 不是外部知识库。需要频繁更新、可以追溯来源的文档知识，通常更适合 RAG；需要调整模型的表达风格、格式或特定行为时，LoRA 才可能更合适。

## 量化是什么

量化是用更低精度表示权重或计算，例如从 FP16 降到 INT8 或 4-bit，以减少：

```text
模型存储空间
显存占用
内存带宽压力
部分硬件上的推理成本
```

代价是可能出现精度损失，而且真实加速效果依赖硬件、推理框架、量化方法和算子支持。

LoRA 和量化解决的问题不同：

```text
LoRA
→ 怎样用较少可训练参数适配模型

量化
→ 怎样用更低精度降低模型部署成本
```

二者可以组合，例如量化基础模型后再训练 LoRA 适配器，但不要把“4-bit 量化”说成“只训练了 4-bit 的 LoRA”。

还要区分权重量化与 KV Cache 量化：前者主要压缩模型参数，后者主要降低长上下文和高并发时缓存所占的内存。

---

# 十二、整理成自己的面试回答

[[Day28-Transformer与LLM面试回答]]

今天新建一份回答笔记：

```powershell
New-Item `
    -Path "docs\appendix\Day28-Transformer与LLM面试回答.md" `
    -ItemType File
```

如果文件已经存在，PowerShell 会提示冲突，此时不要覆盖，直接打开原文件：

```powershell
code "docs\appendix\Day28-Transformer与LLM面试回答.md"
```

先写入这些标题：

```markdown
# Day 28：Transformer 与 LLM 面试回答

## 1. Attention 是什么？
## 2. Q、K、V 分别有什么作用？
## 3. 为什么需要 Multi-head Attention？
## 4. 为什么 Transformer 需要位置编码？
## 5. Residual 和 LayerNorm 分别解决什么问题？
## 6. BERT 和 GPT 有什么区别？
## 7. LLM 的训练和推理有什么区别？
## 8. KV Cache 是什么，为什么能加速生成？
## 9. Temperature 如何影响生成？
## 10. LoRA 是什么？
## 11. 量化是什么，它和 LoRA 有什么区别？
```

每道题用自己的话写 4～6 句，使用下面的结构：

```text
第一句：概念是什么
第二句：它怎样工作或为什么需要
第三句：与相邻概念的区别
第四句：联系当前 Mini RAG 项目或给一个例子
第五句：补一个边界、代价或常见误解
```

其中至少把下面四个项目联系写进去：

```text
当前项目调用的是训练完成后的 LLM，属于推理，不是训练
BGE Embedding 与生成式聊天模型承担不同任务
llm_service.py 没有显式传 temperature，使用服务端默认设置
上传 PDF 和建立 FAISS 索引不会修改 LLM 参数，因此不是微调
```

如果时间有限，优先保证 Attention/QKV、训练与推理、KV Cache、Temperature 四道题能真正说清，再给其他题写简短但准确的答案。不要复制整篇参考说明。

---

# 十三、进行一轮随机口述

关闭 Day 28 计划和回答笔记，在 PowerShell 中随机打乱问题：

```powershell
$questions = @(
    "Attention 是什么？"
    "Q、K、V 分别有什么作用？"
    "为什么需要 Multi-head Attention？"
    "为什么 Transformer 需要位置编码？"
    "Residual 和 LayerNorm 分别解决什么问题？"
    "BERT 和 GPT 有什么区别？"
    "训练和推理有什么区别？"
    "KV Cache 为什么能加速生成？"
    "Temperature 如何影响生成？"
    "LoRA 是什么？"
    "量化是什么，它和 LoRA 有什么区别？"
)

$questions | Sort-Object { Get-Random }
```

随机选择至少 5 道进行口述。每道题尽量在一分钟左右讲完，不要求逐字背诵，但要能回答面试官的追问。

重点检查这些常见误解：

```text
Q、K、V 不是人工编写的固定标签
Attention 权重不等于可直接解释的因果关系
不同 Attention Head 不保证有固定的人类职责
位置编码和因果掩码不是同一个东西
Residual 和 LayerNorm 不能互相替代
上传 PDF 建索引不是训练 LLM
KV Cache 用内存换取少做重复计算
Temperature 不改变模型已经学到的知识
LoRA 是参数高效微调，量化是降低数值精度
```

在回答笔记末尾记录：

```text
最流畅的三题：
最容易卡住的三题：
需要再查证的概念：
```

---

# 十四、检查笔记并提交 Git

先确认 Day 27 的 9 道回答不再只有空标题：

```powershell
Get-Content "docs\appendix\Day27-Python与后端面试回答.md"
```

再检查 Day 28 回答笔记的标题数量：

```powershell
Select-String `
    -Path "docs\appendix\Day28-Transformer与LLM面试回答.md" `
    -Pattern '^## ([1-9]|1[01])\.'
```

预期找到 11 行。还要人工检查标题下是否真的有回答，不能只看标题数量。

查看今天的修改：

```powershell
git status --short
git diff --check
```

今天正常应包含：

```text
docs/Day28.md
docs/appendix/Day27-Python与后端面试回答.md
docs/appendix/Day28-Transformer与LLM面试回答.md
```

今天不需要修改：

```text
app 中的业务代码
README.md
requirements.txt
Dockerfile
评估数据
.env
```

确认回答是自己的表达、没有秘密信息后再暂存：

```powershell
git add `
    docs/Day28.md `
    "docs/appendix/Day27-Python与后端面试回答.md" `
    "docs/appendix/Day28-Transformer与LLM面试回答.md"

git diff --cached --stat
git status
```

确认暂存文件正确后提交：

```powershell
git commit -m "docs: prepare Transformer and LLM interview answers"
```

最后检查：

```powershell
git log -1 --oneline
git status --short
```

---

# Day 28 完成标准

- [ ] 已补齐 Day 27 的 9 道 Python 与后端回答，不再只有空标题
- [ ] 能按照完整数据流解释 Token 如何经过 Transformer 得到输出
- [ ] 能写出 Attention 公式并解释缩放、softmax 和加权求和
- [ ] 能用自己的语言说明 Q、K、V 的作用，并知道它们来自可训练投影
- [ ] 能解释 Multi-head Attention 的意义以及位置编码为什么必要
- [ ] 能区分位置编码与因果掩码
- [ ] 能分别说明 Residual 与 LayerNorm 的作用
- [ ] 能从架构、上下文方向和预训练任务比较经典 BERT 与 GPT
- [ ] 能区分训练、Prefill 和逐 Token Decode
- [ ] 能解释 KV Cache 为什么减少重复计算，以及它的内存代价
- [ ] 已运行 Temperature 小实验，并能解释三组概率的变化
- [ ] 能说明当前项目没有显式传 Temperature，而不是假设它等于 0
- [ ] 能解释 LoRA 的低秩增量思路和适用场景
- [ ] 能解释量化的收益、代价，以及它和 LoRA 的区别
- [ ] 能说明 BGE Embedding、生成式 LLM、RAG 和微调不是同一件事
- [ ] 已完成 `docs/appendix/Day28-Transformer与LLM面试回答.md`
- [ ] 已随机口述至少 5 道题，并记录最容易卡住的三题
- [ ] 已确认没有修改业务代码、依赖、README、评估数据或 `.env`
- [ ] 检查成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
