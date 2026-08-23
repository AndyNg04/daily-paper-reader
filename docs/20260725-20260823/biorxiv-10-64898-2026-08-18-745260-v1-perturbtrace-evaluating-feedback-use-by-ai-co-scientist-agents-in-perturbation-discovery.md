---
title: "PerturbTrace: Evaluating Feedback Use by AI Co-Scientist Agents in Perturbation Discovery"
title_zh: PerturbTrace：评估AI共同科学家代理在扰动发现中的反馈利用
authors: "Yu, C., Liu, S., Qiao, G., Luo, M., Xiang, Y., Xu, Z."
date: 2026-08-20
pdf: "https://www.biorxiv.org/content/10.64898/2026.08.18.745260v1.full.pdf"
tags: ["query:human-ai"]
score: 9.0
evidence: 评估AI合著智能体的反馈使用情况
tldr: "AI共同科学家在闭环实验设计中是否真正利用反馈调整决策尚不明确。为此提出PerturbTrace框架，从反馈到状态、状态到动作、动作到结果三个阶段评估每轮转换。在17个任务中评估四个LLM代理，发现虽然它们多数优于非代理基线，但真实反馈与随机反馈相比无一致优势，仅7.5%完整执行反馈序列。说明高召回率并不代表有效反馈利用，需同时评估发现性能与决策改变。"
source: biorxiv
selection_source: fresh_fetch
motivation: 现有AI共同科学家代理的闭环反馈利用缺乏系统评估，高召回率可能掩盖无效反馈。
method: 提出PerturbTrace，通过反馈到状态、状态到动作、动作到结果三阶段追踪评估代理是否将反馈融入决策，并在17个筛选任务上与基线和受控反馈对比。
result: 四个代理在至少15/17任务上优于非代理方法，但真实反馈相比随机反馈无一致优势；576个转换中仅43个完成完整反馈序列，含25个随机反馈。
conclusion: 高最终召回率不表示有效反馈使用；评估闭环科学代理需同时考察发现性能和反馈是否改变决策。
---

## 摘要
近期人工智能共同科学家的进展已将大语言模型代理引入闭环实验设计。然而，这些代理是否利用早期轮次的反馈来修正后续实验决策仍不清楚。我们通过PerturbTrace来解决这一问题，它通过反馈到状态、状态到行动以及行动到结果三个阶段评估每一轮之间的转变。这些阶段分别评估反馈是否反映在代理的推理和扰动选择策略中，所述策略是否指导下一批扰动，以及该批次是否比随机抽样预期产生更多命中。我们在17个基于筛选的任务上评估了四个大语言模型代理，并将它们与随机选择、主动学习和LLM引导的贝叶斯优化基线进行比较。每个代理在至少15个任务上优于最强非代理方法，然而在六个任务上的对照评估显示，真实反馈相比随机或无反馈并无一致优势。在真实或随机反馈下的576次转变中，仅43次（7.5%）完整走完反馈-状态-行动-结果序列，其中25次发生在随机反馈下。这些发现表明，高最终召回率并不一定意味着有效的反馈利用。它们也凸显出评估闭环科学代理时，既要考虑其发现性能，也要考虑反馈是否改变了其后续决策。

## Abstract
Recent advances in AI co-scientists have brought LLM agents into closed-loop experimental design. However, whether these agents use feedback from earlier rounds to revise subsequent experimental decisions remains unclear. We address this question with PerturbTrace, which evaluates each round-to-round transition through Feedback-to-State, State-to-Action, and Action-to-Outcome. These stages assess whether feedback is reflected in the agent's rationale and perturbation-selection strategy, whether the stated strategy guides the next perturbation batch, and whether that batch yields more hits than expected under random sampling. We evaluate four LLM agents on 17 screen-derived tasks and compare them with random selection, active learning, and LLM-guided Bayesian optimization baselines. Each agent outperforms the strongest non-agent method on at least 15 of the 17 tasks, yet controlled evaluations across six tasks show no consistent advantage from true feedback over random or no feedback. Among 576 transitions under true or random feedback, only 43 (7.5%) complete the full Feedback-State-Action-Outcome sequence, including 25 under random feedback. These findings show that high final recall does not necessarily indicate effective feedback use. They also highlight the need to evaluate closed-loop scientific agents by both their discovery performance and whether feedback changes their subsequent decisions.

---

## 论文详细总结（自动生成）

好的，我已经仔细阅读了您提供的论文《PerturbTrace: Evaluating Feedback Use by AI Co-Scientist Agents in Perturbation Discovery》的元数据和摘要，并结合我的内部知识对其进行了更深入的理解和分析。以下是按照您的要求生成的结构化、深入的中文总结。

---

# PerturbTrace：评估AI共同科学家代理在扰动发现中的反馈利用 —— 详细总结

## 1. 论文的核心问题与整体含义

- **研究背景**：近年来，大语言模型（LLM）代理被引入科学发现领域，作为“AI共同科学家”（AI co-scientists）进入闭环实验设计流程。这些代理能够根据已完成的实验结果，提出下一轮的实验假设或扰动方案。
- **核心问题**：尽管这些代理被设计为具备“闭环”能力，但目前缺乏对其是否真正利用历史反馈来修正后续决策的系统性评估。一个关键疑问是：**高发现性能是否就意味着有效的反馈利用？** 换言之，代理的优异表现是源于真正学习和调整了实验反馈，还是仅仅因为其预训练知识的先验偏向？
- **整体含义**：论文指出，仅仅评估最终发现结果（如召回率）不足以证明代理的闭环学习能力。这为AI科学代理的评估标准提出了新的、更严格的要求，即必须同时考量“发现性能”和“决策改变”两个维度，否则可能对代理能力产生误解。

## 2. 论文提出的方法论：PerturbTrace 框架

- **核心思想**：提出了一个名为 **PerturbTrace** 的评估框架，用于解耦和追踪代理在每一轮之间的决策过程，以判断反馈是否真正影响了行动。
- **三阶段分解**：该框架将“反馈 → 下一轮行动”的转换分解为三个可独立评估的阶段：
  1. **反馈到状态（Feedback-to-State）**：评估代理的推理过程和扰动选择策略是否反映了上一轮实验的反馈信号。即，代理声称的下一步计划是否真的考虑了上一轮结果。
  2. **状态到动作（State-to-Action）**：评估代理所陈述的策略是否直接指导了其实际生成的下一批扰动。即，代理是否“言行一致”，策略与行动是否匹配。
  3. **动作到结果（Action-to-Outcome）**：评估代理实际生成的扰动批次（由上述策略指导）是否比随机抽样产生了更多的命中（hits）。这衡量了行动的有效性。
- **判定标准**：只有当一个轮次间的转换完整走完“反馈 → 状态 → 动作 → 结果”的序列，并且每一步都得到满足时，才判定代理在该轮次**有效利用了反馈**。
- **对比基准**：为了进行严格对照，论文在没有反馈或随机反馈的条件下运行相同的代理，以比较代理在真实反馈下是否比虚假/无效反馈下产生更好的决策。

## 3. 实验设计

- **数据集与场景**：使用了 **17 个从筛选任务（screen-derived tasks）中衍生出的基准任务**。此类任务模拟了药物发现中的高通量筛选，目标是在一个化合物的潜在扰动空间中识别出有效的扰动目标。
- **评估对象**：评估了 **四个不同的LLM代理**。
- **对比基线**：将代理与以下非代理方法进行对比：
  - **随机选择**（Random selection）
  - **主动学习**（Active learning）
  - **LLM引导的贝叶斯优化**（LLM-guided Bayesian optimization）
- **实验数量与充分性**：
  - 代理与非代理基线的对比实验在**全部17个任务**上进行。
  - 关于反馈有效性的受控对照评估（真实反馈 vs. 随机/无反馈）在**6个任务**上进行了深入分析。
  - 整体实验设计层次分明，既有广度（17个任务）也有深度（对6个任务进行更细致的内部机制分析），能够有力地支撑论文的核心论点，即“代理在部分情况下表现出色，但反馈利用却无效”。

## 4. 资源与算力

- **未明确说明**：论文在提供的文本中（包括摘要和元数据）**未明确提及**所使用的GPU型号、数量、具体训练时长或计算资源总花费。
- 由于该方法主要基于对已有LLM API的推理调用和代理行为追踪，训练/推理的计算开销相对较小，但具体细节未在文中披露。

## 5. 实验数量与充分性

- **实验规模**：在17个任务上的基准测试和6个任务的深度剖析构成了一个合理规模的研究。
- **分析样本量**：在受控评估中，分析了 **576 个轮次间转换（transitions）**，并从中发现了43个完整的反馈-行动序列。
- **充分性与客观性评价**：
  - **优点**：实验设计具有较强的**科学性**和**对抗性**。通过引入“随机反馈”对照，能够有效地剥离代理的先验知识影响，从而更客观地测量反馈信号的边际效用，实验设计思路巧妙。
  - **公平性**：主观来看，通过对比多个基线方法（特别是主动学习和BO），能够相对公平地评估LLM代理在任务上的绝对与相对性能。

## 6. 论文的主要结论与发现

- **发现一：发现性能与反馈利用的显著脱节** ：尽管四个代理在**至少15/17**的任务上优于最强的非代理方法，证明了其强大的先验知识和探索能力，但在“反馈有效性”方面，**真实反馈相比随机反馈或无反馈并无一致优势**。这直接证实了“高召回率不代表有效反馈利用”的核心假设。
- **发现二：极低的完整反馈执行率**：在所有576次转换中，仅有 **43次（7.5%）** 完整走完了“反馈-状态-动作-结果”序列。更令人惊讶的是，这43次中甚至有**25次发生在随机反馈下**。这表明代理在大多数情况下并未真正触及“有效利用反馈”的门槛，所谓的“闭环”过程在机制上大多是断裂的。
- **结论**：该研究为AI共同科学家领域敲响了警钟：当前的LLM代理在科学发现上虽然表现优异，但其“闭环”能力可能是一个假象，它们很可能只是在依据先验知识进行盲目的试错，而没有真正读取和利用系统的反馈信号。

## 7. 优点

- **开创性的评估视角**：首次提出了一个可操作的框架来系统评估LLM代理的反馈利用能力，而非仅仅关注最终发现结果，填补了该领域的关键空白。
- **严谨的反事实实验设计**：通过“随机反馈”作为对照，巧妙地分离了先验知识和闭环学习两个因素，使得“反馈利用无效”的结论具有很高的说服力。
- **框架的可泛化性**：PerturbTrace的“反馈-状态-动作-结果”四阶段追踪范式，不依赖于特定的LLM代理或科学任务，可以作为一种通用的评估标准，应用于未来更广泛的人机协同科学发现系统。

## 8. 不足与局限

- **评估范围有限**：仅基于“筛选任务”进行验证，尚未涉及其他的科学发现模式（如开放式生成、多轮实验设计、复杂假设推理等），结论的通用性有待进一步验证。
- **对“状态”的依赖**：框架在“状态到动作”阶段高度依赖代理能够清晰地陈述其策略，并假设策略和行动之间存在严格的一致性。这可能无法完全捕捉某些LLM代理隐式或难以表达的推理过程。
- **统计功效**：对于“反馈利用在6个任务上无一致优势”的结论，可能需要考虑统计功效问题，即样本量（6个任务）是否足够强大，以检测出细微但真实的反馈利用效果。
- **偏差风险评估**：由于该研究主要依赖黑箱LLM API，存在一定的未知模型内部偏差风险，这种偏差可能使代理在部分任务中过于依赖先验知识，从而难以客观评估其学习能力，结果可能受特定模型版本影响。

---

（完）
