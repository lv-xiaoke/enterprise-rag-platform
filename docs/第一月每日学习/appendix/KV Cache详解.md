KV Cache 最容易理解的方法，是把它放到“GPT 一个 token 一个 token 生成”的过程中看。

先假设模型收到：

```text
中国的首都是
```

然后要继续生成：

```text
北京
```

GPT 不是一次把整句答案都算出来，而是类似这样：

```text
输入：中国的首都是
→ 预测：北京

输入：中国的首都是北京
→ 预测：。
```

问题就在这里：第二次生成的时候，前面的“中国的首都是”其实已经计算过一遍了。

---

### 1. 如果没有 KV Cache，会发生什么

假设 Prompt 有 4 个 token：

```text
中国 / 的 / 首都 / 是
```

为了简单，假设每个 token 经过某一层 Attention 后产生：

```text
Q：2维
K：2维
V：2维
```

第一次处理 Prompt：

```text
中国 → Q1 K1 V1
的   → Q2 K2 V2
首都 → Q3 K3 V3
是   → Q4 K4 V4
```

模型最后根据“是”这个位置的结果预测：

[[解释根据“是”这个位置结果预测]]

```text
北京
```

现在准备生成下一个 token。

如果**没有 KV Cache**，模型会把：

```text
中国 / 的 / 首都 / 是 / 北京
```

整个序列重新送进去，然后重新计算：

```text
中国 → Q1 K1 V1    ← 又算一次
的   → Q2 K2 V2    ← 又算一次
首都 → Q3 K3 V3    ← 又算一次
是   → Q4 K4 V4    ← 又算一次
北京 → Q5 K5 V5    ← 新的
```

这里前四个 token 的 K、V，其实和上次完全一样。

所以大量计算重复了。

然后生成第三个 token 时，又会重新计算：

```text
中国
的
首都
是
北京
```

再加上新 token。

上下文越来越长，重复工作越来越多。

---

## 2. KV Cache 做了什么

KV Cache 的思路很简单：

> 既然过去 token 的 K 和 V 已经算好了，而且以后还会继续使用，那我就把它们存起来。

第一次处理：

```text
中国 / 的 / 首都 / 是
```

算出：

```text
K1 V1
K2 V2
K3 V3
K4 V4
```

然后缓存：

```text
K Cache:
[K1
 K2
 K3
 K4]

V Cache:
[V1
 V2
 V3
 V4]
```

比如每个 K、V 是 2 维，那么：

```text
K Cache.shape = 4 × 2
V Cache.shape = 4 × 2
```

模型生成：

```text
北京
```

接下来处理“北京”的时候，就不用重新计算前面四个 token。

只算：

```text
北京 → Q5 K5 V5
```

然后拿：

```text
Q5
```

去查询：

```text
K1
K2
K3
K4
K5
```

也就是：

```text
Q5 × K_cache^T
```

---

## 3. 从矩阵维度看就很清楚

假设当前有 5 个历史/当前 token，每个 head 的维度：

```text
d_k = 2
```

当前新 token 的 Q：

```text
Q5.shape = 1 × 2
```

缓存中的 K：

```text
K Cache.shape = 5 × 2
```

转置：

```text
K Cache.T.shape = 2 × 5
```

所以：

```text
Q5            × K Cache.T

1 × 2         × 2 × 5

            ↓

          1 × 5
```

得到：

```text
[0.1, 0.05, 0.2, 0.1, 0.55]
```

也就是当前 token 对 5 个位置的 Attention 权重。

然后：

```text
Attention    × V Cache

1 × 5        × 5 × 2

           ↓

         1 × 2
```

于是得到当前 token 的 Attention 输出。

你会发现：

> 当前这一次真正需要历史 token 提供的是 **K 和 V**。

---

# 4. 为什么不缓存历史 Q？

这是最重要的问题。

你可以先重新回忆 Q/K/V 的角色：

```text
Q = 我现在想找什么
K = 我这里有什么特征，别人可以拿来匹配
V = 如果别人关注我，我实际提供什么信息
```

假设已经有：

```text
中国 / 的 / 首都 / 是
```

现在处理新 token：

```text
北京
```

当前需要做的是：

```text
“北京”的 Q
       ↓
去和历史所有 K 比较
       ↓
K1 K2 K3 K4 K5
       ↓
得到 Attention 权重
       ↓
再从 V1 V2 V3 V4 V5 中取信息
```

这里根本不需要：

```text
Q1
Q2
Q3
Q4
```

因为：

```text
Q1
```

是在当初处理“中国”的时候用的。

它已经完成使命了。

下一步处理新 token 时，只需要**新 token 自己的 Q**。

所以可以这样理解：

```text
Q：一次性的问题
K：长期保存的索引
V：长期保存的内容
```

这也是为什么叫：

```text
KV Cache
```

而不是：

```text
QKV Cache
```

---

## 5. 一个非常直观的类比

把 Attention 想成图书馆。

历史 token：

```text
中国
的
首都
是
```

每个 token 都留下两样东西：

```text
K：目录标签
V：实际书里的内容
```

现在新 token “北京”来了。

它产生：

```text
Q：我现在想查什么？
```

然后：

```text
Q
↓
去翻历史 K 目录
↓
找到应该关注哪些内容
↓
再读取对应的 V
```

所以图书馆需要长期保存：

```text
K：目录
V：内容
```

但过去的人以前提出过什么查询：

```text
Q1 Q2 Q3 Q4
```

现在并不重要。

这就是：

> **历史 Q 用完就可以扔，历史 K/V 以后还要反复使用。**

---

# 6. Prefill 和 Decode 又是什么

**Prefill** 可以理解成：

> **模型第一次把你输入的整段 Prompt 一次性“读完并处理”的阶段。**

比如你输入：

```text
中国的首都是
```

假设 tokenizer 后是 4 个 token：

```text
中国 / 的 / 首都 / 是
```

模型第一次处理这 4 个 token 时，会把它们**一起送进 Transformer**：

```text
中国 / 的 / 首都 / 是
        ↓
     Transformer
        ↓
计算每一层的 Q、K、V
        ↓
得到各位置的隐藏表示
        ↓
把历史 K、V 存进 KV Cache
        ↓
根据最后一个位置预测下一个 token
```

这个“一次性处理已有输入”的过程，就是 **Prefill**。

比如 Prefill 完成后，KV Cache 里已经有：

```text
中国 → K1 V1
的   → K2 V2
首都 → K3 V3
是   → K4 V4
```

然后模型根据最后一个位置的结果预测：

```text
北京
```

接下来就不再叫 Prefill 了，而进入 **Decode** 阶段。

Decode 是：

```text
新生成：北京
↓
只处理“北京”这一个新 token
↓
计算 Q5、K5、V5
↓
Q5 去查询缓存中的 K1~K5
↓
利用 V1~V5 得到结果
↓
继续预测下一个 token
```

所以最简单的区别是：

```text
Prefill：
一次处理用户已经输入的整段 Prompt

Decode：
之后一个 token 一个 token 地生成
```

例如你输入一个 1000-token 的问题，然后模型回答 200 token：

```text
前 1000 token
→ Prefill，一次处理

后面生成的 200 token
→ Decode，一个一个生成
```

为什么叫 **prefill**？

可以直译成“预填充”。

因为模型在真正开始逐 token 生成之前，先用你的 Prompt：

```text
把上下文处理好
+
把 KV Cache 填好
```

相当于提前把后面生成需要用到的信息“填进去”。

你可以把它想成考试：

```text
Prefill：
先把题目全部读完，记住题目信息

Decode：
开始一个字一个字写答案
```

因此你以后看到：

```text
Prefill latency
```

通常指：

> 模型处理用户 Prompt 所花的时间。

而：

```text
Decode speed
```

通常指：

> 模型开始回答以后，每秒能生成多少 token。

这也是为什么你有时候输入特别长的 Prompt，会感觉模型**第一句话出来得比较慢**：因为它得先完成 Prefill。

---

# 7. KV Cache 到底省了什么？

注意一个容易误解的地方：

> KV Cache 并不是让 Attention 完全变成常数时间。

假设已经有 10,000 个历史 token。

新 token 的 Q 还是需要和：

```text
10,000 个 K
```

比较。

也就是说：

```text
Q_new × K_cache^T
```

仍然要看整个历史上下文。

但是 KV Cache 避免了一个更大的浪费：

```text
重新为历史10000个token计算：

K
V
以及之前网络中的相关投影
```

不用做了。

所以：

```text
没有 Cache：
每生成一个新 token
→ 重新处理整个历史

有 Cache：
每生成一个新 token
→ 只处理新 token
→ 复用历史 K/V
```

差别非常大。

---

# 8. 为什么上下文越长，KV Cache 越占显存

因为每增加一个 token，都需要在**每一层**保存：

```text
K
V
```

假设模型有：

```text
32 层
```

那么一个 token 不是只存一份 K/V，而是：

```text
Layer 1：K、V
Layer 2：K、V
Layer 3：K、V
...
Layer 32：K、V
```

所以缓存大致随着这些因素增长：

```text
上下文长度 ↑
→ KV Cache ↑

层数 ↑
→ KV Cache ↑

batch / 并发用户数 ↑
→ KV Cache ↑
```

比如一个用户缓存：

```text
8000 token
```

如果同时有 100 个用户：

```text
100 × 8000 token
```

需要保存的 KV 就非常可观。

这也是为什么大模型服务器经常很关注：

```text
KV Cache 显存
```

---

# 9. 把整个流程连起来

你现在可以把 GPT 推理理解成：

```text
用户 Prompt：

A B C D
   ↓

Prefill
   ↓

计算：
QA KA VA
QB KB VB
QC KC VC
QD KD VD

   ↓

缓存：
K = [KA KB KC KD]
V = [VA VB VC VD]

   ↓

生成新 token E
```

下一次：

```text
只算 E：

QE
KE
VE

↓

QE 与：

KA
KB
KC
KD
KE

比较

↓

根据 Attention 权重
从：

VA
VB
VC
VD
VE

读取信息

↓

生成 F
```

然后把：

```text
KE、VE
```

加入缓存。

下一轮：

```text
只算 F 的：

QF
KF
VF
```

继续重复。

---

所以最后你只需要牢牢记住一句：

> **KV Cache 本质上就是：把历史 token 已经计算好的 K 和 V 保存下来，后续生成时让新的 Q 直接查询这些历史 K，并读取对应 V，从而避免重复计算历史 token。**

而为什么没有 Q Cache：

> **因为历史 Q 只服务于历史 token 当时的那一次查询；以后真正会被新 token 重复使用的是历史 K 和 V。**

如果你把这一点和前面学过的 QKV 角色联系起来，KV Cache 其实就非常自然了：

```text
Q = 当前问题
K = 历史索引
V = 历史信息

当前问题每次都会变
历史索引和信息却会一直被查
```

这就是 KV Cache。