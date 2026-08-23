---
title: "Automation Disrupts, Explanations Restore: The Neural Signatures of Agency Loss and Recovery in Human-AI Interaction"
title_zh: 自动化扰乱，解释恢复：人机交互中能动性丧失与恢复的神经标志
authors: "Houdoyer, E., Le Bars, S., Chambon, V."
date: 2026-07-27
pdf: "https://www.biorxiv.org/content/10.64898/2026.07.22.740020v1.full.pdf"
tags: ["query:human-ai"]
score: 9.0
evidence: 通过EEG实验研究AI解释如何恢复人机交互中的控制感
tldr: 自动化会削弱人类对自身行为的能动感，破坏意图与效果间的预测联系。本研究利用三个EEG自动驾驶实验，考察自动化和不同层级AI解释对能动性神经标记的影响。结果显示，自动化增强P1-N1、削弱N1-P2并延迟N1潜伏期；目标级解释部分恢复，结合轨迹级解释则最强恢复，且MMN不受影响。研究揭示了解释性AI恢复能动性的神经机制，为可解释自主系统设计提供依据。
source: biorxiv
selection_source: fresh_fetch
motivation: 自动化破坏人机互动中的能动感，可解释AI虽提出可恢复能动性，但其神经认知机制尚不明确。
method: 基于自动驾驶范式开展三个EEG实验，操纵自动化层级与不同解释形式，记录外显判断和事件相关电位。
result: 自动化扰乱P1/N1和N1/P2成分；目标级解释部分恢复，结合轨迹级解释最强恢复，且MMN不受影响。
conclusion: 识别出能动感相关的EEG成分标记，证实多层次意图共享能增强预测参与和主观控制体验，为设计可解释自主系统提供神经依据。
---

## 摘要
已有研究表明，自动化通过破坏意图与效果之间的预测联系，削弱了能动感（SoA），即对自身行为及其结果的控制体验。可解释人工智能（XAI）被提出作为一种解决方案，但解释恢复能动性的神经认知机制仍不清楚。通过使用自动驾驶范式的三项脑电图（EEG）实验，我们考察了自动化以及不同形式的人工智能解释如何调节显式能动性判断和能动性相关预测处理的早期神经标志。在实验1中，自动化降低了显式的控制感，并与感觉衰减的减弱相关，表现为P1-N1振幅增加、N1-P2振幅减少以及N1潜伏期延迟。在实验2中，远端（目标层面）解释部分恢复了能动性，并选择性调节了早期听觉反应，降低了P1-N1振幅，增加了N1-P2振幅。在实验3中，将远端和近端（轨迹层面）解释相结合，产生了最强的行为和神经层面的能动性恢复，表现为P1-N1的分级衰减和N1-P2反应的增强，以及N1潜伏期的加速。在所有实验中，失匹配负波（MMN）均未受影响，表明前注意偏差检测在能动性或可解释性变化时保持不变。综合来看，这些结果识别出对能动感波动敏感的特定成分EEG标志，并证明人工智能系统的多层次意图共享增强了预测参与和显式控制体验。这项工作为设计能够维持用户能动性的可解释自主系统提供了神经认知基础。

## Abstract
Automation has been shown to weaken the sense of agency (SoA), the experience of controlling ones actions and their outcomes, by disrupting the predictive link between intention and effect. Explainable AI (XAI) has been proposed as a solution, yet the neurocognitive mechanisms through which explanations restore agency remain unclear. Across three EEG experiments using an autonomous-driving paradigm, we examined how automation and different forms of AI explanations modulate explicit agency judgments and early neural markers of agency-related predictive processing. In Experiment 1, automation reduced explicit feelings of control and was associated with reduced sensory attenuation, as reflected by increased P1-N1 amplitudes, decreased N1-P2 amplitudes, and delayed N1 latencies. In Experiment 2, distal (goal-level) explanations partially restored agency and selectively modulated early auditory responses, decreasing P1-N1 and increasing N1-P2 amplitudes. In Experiment 3, combining distal and proximal (trajectory-level) explanations produced the strongest behavioural and neural restoration of agency, yielding a graded attenuation of P1-N1 and enhanced N1-P2 responses along with accelerated N1 latencies. Across all experiments, mismatch negativity (MMN) remained unaffected, indicating that pre-attentive deviance detection is preserved regardless of agency or explainability. Together, these results identify component-specific EEG markers that track fluctuations in the sense of agency and demonstrate that multi-level intention sharing by AI systems enhances both predictive engagement and explicit control experience. This work provides a neurocognitive foundation for designing explainable autonomous systems capable of maintaining user agency.

---

## 论文详细总结（自动生成）

# 论文总结：Automation Disrupts, Explanations Restore: The Neural Signatures of Agency Loss and Recovery in Human-AI Interaction

## 1. 核心问题与整体含义（研究动机和背景）

- **核心问题**：自动化系统（如自动驾驶）在接管人类决策与行动后，会通过破坏“意图—效果”的预测性联结，削弱用户的能动感（Sense of Agency, SoA，即对自己行为及其结果的主观控制体验）。尽管可解释人工智能（XAI）被提出作为解决方案，但其从神经认知层面上如何恢复能动性、不同层级的解释信息（目标级 vs. 轨迹级）对能动性恢复是否存在差异化的神经机制，此前尚不清楚。
- **背景支撑**：研究建立在三个理论框架之上——① 预测加工框架（sensory attenuation，感觉衰减：当行为结果符合内部预测时，早期感觉反应被抑制）；② 意图的层级架构理论（Pacherie, 2008；将意图分为远端/目标级、近端/子目标级和运动级）；③ 联合行动研究中"意图共享"对人类协调和能动感支持作用的证据。
- **整体含义**：该研究将"意图共享"原则从人际联合行动迁移到人机交互（HAI），从神经科学角度为设计能维护用户能动感的可解释自主系统提供实证基础，具有重要的理论与应用价值。

## 2. 方法论（核心思想、关键技术细节）

- **核心思想**：采用EEG技术实时、非侵入性地捕捉自动化与AI解释对能动性相关预测加工的影响。核心逻辑是：当个体拥有（或感知到）对行动结果的控制时，感觉皮层会对可预测的感觉结果产生更强的"感觉衰减"（sensory attenuation），表现为早期听觉事件相关电位（ERP）振幅的抑制。
- **关键测量指标**：
  - **显式能动性指标**：主观控制感评分（Feeling of Control, FoC），9点Likert量表，在20%的试次中收集。
  - **隐式神经指标**：
    - **P1–N1峰-峰振幅复合**：早期预测编码的指标，能动性越强（预测越精确），振幅越小（衰减更显著）。
    - **N1–P2峰-峰振幅复合**：反映后期结果评估/整合阶段，其调制方向依任务情境而定。
    - **N1潜伏期**：自动化条件下延迟，解释恢复后加速。
    - **失匹配负波（MMN）**：前注意偏差检测指标（Mismatch减Match的差异波，100–250 ms）。
  - 采用峰-峰复合测量（peak-to-peak measures）以减小基线波动和ERP成分间时间重叠的干扰，更适合复杂自然化范式。
- **任务范式**：简化的自动驾驶任务。被试（或声称由AI系统）在两种策略（安全低回报 vs. 冒险高回报）间做出选择，随后车辆向目标移动300 ms，到达后播放匹配（80%）或不匹配（20%）的纯音反馈。所有条件均包含单次按键，确保运动输出在各条件间等价，从而将差异归因于能动性操纵而非运动差异。
- **统计方法**：行为数据使用线性混合效应模型（LMM，被试随机截距 + 条件固定效应 + Satterthwaite自由度近似 + Tukey多重比较校正）；ERP数据使用重复测量方差分析（rmANOVA）+ Benjamini-Hochberg FDR校正 + Hedges g效应量。
- **关键实验控制**：AI条件采用"信念式自动化"范式——AI行为实际是预设程序化的，但被试被告知AI在优化安全、奖励和驾驶时间三个参数，并通过事先设置风险偏好来强化信用。所有条件在视觉显示时长、按键数量等方面均匹配。

## 3. 实验设计（数据集/场景、benchmark、对比方法）

- **数据集/场景**：共3个独立实验，87名付费被试参与采集，最终有效样本57人（实验1：20人；实验2：18人；实验3：19人），均为巴黎高师征集的大学生志愿者。任务场景为实验室内的简化自动驾驶模拟（无真实驾驶环境，为非沉浸式屏幕任务）。
- **实验结构**（均为被试内设计）：
  - **实验1（自动化效应）**：Motor/no-AI条件（被试自主选择策略并触发移动）vs. 信念式AI条件（AI选择，被试仅按空格键触发）。8个block，每条件400试次。
  - **实验2（远端解释效应）**：AI无解释条件（绿色对勾+无意义占位文本"Null/Inconnu"）vs. AI远端解释条件（黄色高亮AI所选策略目标 + 文字"Gain"/"Security"）。8个block，每条件400试次。
  - **实验3（近端+远端组合解释）**：三水平——AI无解释 vs. AI远端解释（两个目标高亮指示策略） vs. AI近端+远端组合解释（仅高亮单一目标，同时指示策略与轨迹）。四目标布局引入轨迹歧义。8个block，每block内三个子块各34试次。
- **Benchmark与对比方法**：本研究没有对比其他XAI方法（如反事实解释、注意力权重可视化、事后解释等）。其基准主要来自：① 前序行为学工作（Houdoyer et al., under review）中Intentional Binding和显式评分的发现；② 自主动作（Motor条件）作为"高能动性"神经响应的参考标准，各解释条件与之做定性对比。因此，其对比主要是自身条件间的递进层级比较，而非跨方法的横向比较。

## 4. 资源与算力

- **论文中未提及任何GPU型号、数量、训练时长或大规模计算资源**。该研究为EEG实验研究，主体成本为被试采集（87人，每人€20补偿）和EEG设备（Neuroelectrics Enobio 20系统，17通道，500 Hz采样）。数据预处理（MNE-Python）和统计分析（R）均为常规计算负载，不涉及深度学习模型训练。论文仅在"展望"部分提出未来可考虑对连续EEG使用深度学习数据驱动方法，但未实施。

## 5. 实验数量与充分性

- **实验数量**：共3个EEG实验 + 3组行为评分分析（作为操纵检验）+ 每个实验的MMN分析 + 3组潜伏期分析（见补充材料）。属于典型的递进式多实验设计：自动化效应→远端解释→组合解释。
- **充分性评估**：
  - **优点**：实验设计呈逻辑递进，每个后续实验在前一实验基础上增加一层操纵（自动化→目标级透明度→路径级透明度），形成清晰的分级逻辑。被试内设计提高了统计功效，跨实验保持了统一的反馈结构和任务流程。
  - **不足**：
    - 每个实验的有效样本量较小（18–20人），且原始采集87人中排除了30人（其中20人因EEG噪声过大致约半数epoch被拒后剩余MMN试次不足40个），排除率约34%，可能引入选择偏差。
    - **缺乏全面的消融控制**：没有对比"仅近端解释"单独条件，无法完全区分近端和远端解释的独立贡献及其交互作用的分解。
    - 三个实验使用了不同被试群体，因此跨实验的"自动化—解释—组合解释"效应比较属于间接比较，无法直接进行统计上的跨实验交互检验。
    - 行为评分只占20%试次，用于操纵检验而非逐试次EEG-行为相关分析，因此无法从试次层面确立神经-行为映射关系。
    - 没有与其他XAI解释形式（如文本反事实、可视化注意力图等）的对比，无法得出"多层级解释是最优的XAI策略"的普适结论。

## 6. 主要结论与发现

- **自动化削弱能动性（实验1）**：自动化显著降低显式控制感（FoC从M=7.52降至M=6.80）；神经层面表现为P1–N1振幅增大（感觉衰减减弱）、N1–P2振幅减小、N1潜伏期延迟，表明自动化同时影响早期预测耦合和后期结果评估阶段。
- **远端解释部分恢复能动性（实验2）**：目标级解释显著提升显式控制感，并选择性调节早期听觉响应——P1–N1振幅降低（预测加工增强）、N1–P2振幅增加（结果整合增强），产生与自主控制条件定性相似的神经模式。
- **组合解释最强恢复（实验3）**：近端+远端组合解释产生最强的行为和神经恢复效果：P1–N1振幅呈分级衰减（无解释 > 远端解释 > 组合解释），N1–P2振幅在组合条件下显著增强，N1潜伏期加速。显式FoC呈现同样的分级模式（组合条件最高）。
- **MMN保持稳定**：三个实验中，MMN振幅均不受自动化或解释层级影响，表明前注意偏差检测机制对能动性和可解释性变化保持稳定。
- **音调可预测性效应独立于操纵**：匹配音与失匹配音的P1–N1差异在所有条件下保持一致，且与实验条件无交互，说明感官预测效应与能动性操纵相对独立。
- **总体结论**：研究识别出追踪能动感波动的成分特异EEG标记（P1–N1和N1–P2复合），证明多层次意图共享能同时增强预测参与和显式控制体验，为可解释自主系统的神经认知设计原则提供了直接证据。

## 7. 优点（方法与实验设计的亮点）

- **实验设计的递进逻辑清晰**：三个实验逐步增加操纵层级（自动化→目标级解释→目标+路径级组合），形成严谨的因果推断线索，实验3的分级P1–N1衰减更提供了剂量-反应式证据。
- **精细的运动混淆控制**：所有条件均包含单次按键，使运动输出在各条件间等价，从而能够将行为和神经差异更干净地归因于决策自主性和解释质量，而非运动差异——这是该领域常见问题（运动输出不同导致的N1差异）的较大改进。
- **峰-峰复合测量策略**：采用P1–N1和N1–P2峰-峰测量而非单一成分峰值，对复杂自然范式下成分重叠和基线波动具有更强稳健性，提升了测量可靠性。
- **"信念式AI"范式**：AI行为完全程序化，但通过风险偏好设置、任务参数说明等操作有效构建了被试对AI自主性的信念，在生态效度和实验控制之间取得了较好的平衡——这是一种经过深思熟虑的方法论选择。
- **多模态测量融合**：同时采集显式主观评分（操纵检验）和隐式神经指标，在20%试次上维持行为锚点而不干扰EEG记录，兼顾主观体验与客观神经过程。
- **跨学科理论整合**：将联合行动研究中的"意图共享"框架扩展到人机交互，具备理论创新性；将Pacherie的意图层级模型操作化为不同类型的解释信息，实现了理论的实验检验。

## 8. 不足与局限

- **样本量偏小且排除率高**：有效样本18–20人/实验，但排除率约34%（87人中排除30人），可能引入系统选择偏差（例如噪声高的被试可能是注意力较低或对任务投入较少的个体）。未来研究应使用更大样本或更鲁棒的伪迹处理策略。
- **范式的生态效度局限**：尽管自称"自动驾驶范式"，但任务是极简化的——一次按键、一次300 ms移动、单一听觉反馈，与真实驾驶中连续的视觉-运动协调和动态决策环境仍有较大差距。结果向真实自动驾驶场景的推广需谨慎。
- **跨实验不可直接比较**：三个实验使用不同被试，实验1的Motor条件与实验2、3的解释条件之间无法进行统计上的直接对比，因此"解释恢复至接近自主控制"的说法缺乏直接的跨实验统计支持（作者也谨慎地承认了这一点）。
- **无独立的近端解释条件**：实验3中近端解释总是与远端解释共同出现，无法分离近端解释的独立贡献，削弱了关于"近端信息是否单独有效"的结论。
- **缺乏对其他XAI方法的比较基准**：未测试反事实解释、特征归因、示例解释等常见XAI方法，因此无法在神经层面裁定何类XAI策略最优，限制了直接的应用指导价值。
- **FoC评分与EEG的关联有限**：评分仅用于操纵检验且占比20%，无法用于试次级EEG-行为的关联分析，行为和神经指标的一致性论证停留在条件均值层面。
- **预先设定的时间窗和电极ROI**：P1（30–70 ms）、N1（80–120 ms）、P2（150–250 ms）的时间窗和ROI选择有一定先验设定性，可能限制了对个体差异和任务特异性成分变化的捕捉。
- **被试样本同质化**：样本以大学本科生为主，年龄集中在23岁左右，未考察年龄、驾驶经验、个体对AI的态度等潜在调节因子对效应的调制。
- **无长期效应评估**：所有测量均在单次实验session内完成，无法评估解释信息对能动性的长期维持效果、学习效应或自动化信任的动态变化。

（完）
