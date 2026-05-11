# Tasks

- [ ] Task 1: 双 Canvas 分层渲染架构
  - [ ] SubTask 1.1: 创建双 Canvas HTML 结构（staticCanvas + dynamicCanvas），staticCanvas z-index 低于 dynamicCanvas
  - [ ] SubTask 1.2: 实现 StaticLayerRenderer 类，10fps 刷新率，负责背景渐变、远景氛围粒子、书法阶段名
  - [ ] SubTask 1.3: 实现 DynamicLayerRenderer 类，60fps 刷新率，负责球体、文字流、撞击碎片、波浪
  - [ ] SubTask 1.4: 实现帧率监控与自动降级逻辑（低于 30fps 持续 1 秒时降低粒子数和关闭模糊）

- [ ] Task 2: 五层景深空间系统
  - [ ] SubTask 2.1: 定义 DepthLayer 配置对象，包含 z-range、模糊参数、视差系数、速度系数
  - [ ] SubTask 2.2: 实现鼠标视差系统，根据鼠标偏移量和各层视差系数计算层偏移
  - [ ] SubTask 2.3: 实现球体深度着色（近亮远暗、近大远小），z 值映射到 alpha 和 size 的非线性曲线
  - [ ] SubTask 2.4: 实现球体边缘光晕（Rim Light），z 绝对值 < 0.3 的粒子叠加山水绿高光
  - [ ] SubTask 2.5: 实现球体内部雾化，径向渐变叠加在球体中心区域

- [ ] Task 3: 氛围粒子空气透视
  - [ ] SubTask 3.1: 将氛围粒子分为远景组（60%）和近景组（40%），远景更大更模糊更慢更淡
  - [ ] SubTask 3.2: 远景粒子应用 σ=2 高斯模糊模拟（通过多层半透明绘制实现），视差系数 0.2
  - [ ] SubTask 3.3: 近景粒子保持清晰，视差系数 0.8，速度为远景的 3 倍

- [ ] Task 4: 书法阶段名 3D 切换动效
  - [ ] SubTask 4.1: 实现阶段名沿 Y 轴 3D 旋转消失（透视变形 + 模糊递增），持续 500ms
  - [ ] SubTask 4.2: 实现新阶段名从 Y 轴 -90° 旋转到 0° 出现，持续 500ms
  - [ ] SubTask 4.3: 切换时触发球体脉冲波（粒子向外扩散后回弹）

- [ ] Task 5: 3D 文字撞击效果
  - [ ] SubTask 5.1: 文字飞入时增加 z 轴深度变化，从远处（小字淡色）逐渐靠近（大字亮色）
  - [ ] SubTask 5.2: 有用信息碎片沿球体法线飞入，z 轴先远离后靠近，到达球心缩小消失
  - [ ] SubTask 5.3: 无用信息碎片向下飘落时 z 轴远离（变小变淡），30% 碎片飞向观察者（变大后消失）

- [ ] Task 6: 波浪透视与墨雾过渡带
  - [ ] SubTask 6.1: 波浪粒子增加透视收缩，底部粒子更大更亮，顶部粒子更小更淡
  - [ ] SubTask 6.2: 三层波浪增加深度着色差异（前景饱和、远景灰淡）
  - [ ] SubTask 6.3: 球体底部与波浪顶部之间增加 40px 墨雾渐变过渡区域

- [ ] Task 7: 后端 API 对接
  - [ ] SubTask 7.1: 实现 SSE 流式对话客户端，调用 `/api/flow/chat/stream`，逐字推送为文字粒子
  - [ ] SubTask 7.2: 实现工作流状态轮询，调用 `/api/flow/status/{id}`，根据 should_advance 触发阶段切换
  - [ ] SubTask 7.3: 实现 LLM 配置面板，调用 `/api/llm/config`、`/api/llm/apply-model`、`/api/llm/list-providers`
  - [ ] SubTask 7.4: 实现对话历史恢复，调用 `/api/flow/state/{id}` 获取历史消息

- [ ] Task 8: 双主题空间感适配
  - [ ] SubTask 8.1: 浅灰主题下远景为淡墨色，近景为深墨色，球体边缘光为山水绿
  - [ ] SubTask 8.2: 深灰主题下远景为淡白色，近景为亮白色，球体边缘光为亮山水绿
  - [ ] SubTask 8.3: 验证两种主题下所有 5 层景深均有效且对比度达标

# Task Dependencies

- [Task 2] depends on [Task 1] (景深系统需要双 Canvas 架构)
- [Task 3] depends on [Task 2] (空气透视需要景深系统)
- [Task 4] depends on [Task 2] (3D 切换需要景深系统)
- [Task 5] depends on [Task 2] (3D 撞击需要景深系统)
- [Task 6] depends on [Task 2] (波浪透视需要景深系统)
- [Task 7] 独立，可与 Task 2-6 并行
- [Task 8] depends on [Task 2, Task 3, Task 6] (主题适配需要所有景深层完成)
