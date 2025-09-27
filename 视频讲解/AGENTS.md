为虚拟人数学课程提供一个所见即所得 (WYSIWYG) 的自动化录制舞台。该系统将课程内容、复杂的可视化动画、虚拟人SDK控制以及自动播放逻辑高度整合在一个HTML文件中，通过精密的时序控制，实现“一键录制”的高效生产流程。

2. 核心架构与原则
根据基准代码分析，系统遵循以下核心设计原则：

一体化设计 (Integrated Design): 课程的所有元素——结构(HTML)、样式(CSS)、逻辑(JS)和内容数据——都封装在单一的HTML文件中。这种方式确保了每个课程单元的独立性和可移植性。

模块化动画 (Modular Animations): 系统的核心亮点。每一种复杂的可视化效果（如物理模拟、导数逼近、仪表盘联动）都被封装在独立的JavaScript类中，实现了动画逻辑的高度复用和可维护性。

混合驱动模型 (Hybrid-Driven Model): 系统的自动播放流程采用“事件驱动为主，定时器为辅”的混合模型。它会优先等待虚拟人SDK的“语音播放结束”事件，以确保语音的完整性；在SDK未连接等情况下，则回退到预设的固定时长，保证流程的健壮性。

状态驱动UI (State-Driven UI): 应用的界面（如当前页码、状态指示灯、字幕）根据内部状态变量（currentSlide, isAutoPlaying等）动态更新，确保用户界面与系统内部状态的实时同步。

3. Agent规格定义 (逻辑模块)
系统内部的复杂逻辑可被抽象为以下几个协同工作的智能体（逻辑模块）：

Agent 3.1: UIManager (UI管理器)

ID: VPA-UI-01

描述: 负责管理和更新所有用户界面元素，响应用户的基本交互。

核心职责:

管理幻灯片的显示与切换 (showSlide, nextSlide, previousSlide)。

更新状态指示器 (updateStatus) 和字幕区域 (updateSubtitle)。

处理控制按钮的点击事件和键盘快捷键。

在录制模式下，管理UI元素的显示与隐藏。

实现代码: 主要由 showSlide, updateSubtitle, updateStatus 等全局函数和 DOMContentLoaded / keydown 事件监听器构成。

Agent 3.2: AnimationManager (动画管理器)

ID: VPA-ANIM-02

描述: 系统的可视化核心。负责在不同幻灯片上初始化、启动和停止对应的复杂动画模块。

核心职责:

在页面加载时，根据DOM结构初始化所有幻灯片对应的动画控制器实例 (initAnimations)。

维护一个动画控制器映射表 (animationControllers)，将幻灯片索引与其动画实例关联。

在幻灯片切换时，确保当前页的动画被启动 (controller.start())，而其他页的动画被停止 (controller.stop())。

实现代码: initAnimations 函数、animationControllers Map对象，以及showSlide函数内部对动画控制器的调用逻辑。

Agent 3.3: SDKCoordinator (SDK协调器)

ID: VPA-SDK-03

描述: 专门负责与讯飞虚拟人SDK进行通信的模块。封装了所有与虚拟人相关的操作，如连接、语音合成、动作驱动等。

核心职责:

处理SDK的加载和初始化流程 (waitForSDK, startTeaching)。

管理与SDK服务器的连接状态，并处理连接、断开、错误等事件。

封装语音播放指令 (speakContent)，并包含驱动虚拟人动作的逻辑。

实现一个基于Promise的事件监听器 (waitForSpeechEndOrTimeout)，这是实现混合驱动模型的关键，它能够等待SDK的SPEECH_END事件。

处理付费资源的使用授权逻辑，避免意外开销。

实现代码: waitForSDK, startTeaching, speakContent, waitForSpeechEndOrTimeout 等函数，以及 AvatarPlatform 实例的事件回调。

Agent 3.4: PlaybackOrchestrator (播放编排器)

ID: VPA-CORE-04

描述: 系统的“大脑”，负责执行自动播放的宏观流程，按照预定时序调度其他模块协同工作。

核心职责:

实现核心的 startAutoPlay 异步函数，这是自动化录制的入口。

循环遍历所有幻灯片，按顺序调用 UIManager 进行页面切换。

调用 SDKCoordinator 播放当前页的语音，并等待其播放完成。

在语音播放结束后，执行固定的缓冲延时，然后进入下一个循环。

实现代码: startAutoPlay 函数。

4. 关键动画模块详解
您的代码中包含了多个设计精良的动画模块，它们是本课件的核心特色：

PhysicsIntroAnimation:

功能: 模拟汽车沿预设弯道轨迹行驶，并同步在屏幕一侧的坐标系中绘制出其非线性的位移-时间(s−t)曲线。

技术: 使用Catmull-Rom样条插值算法生成平滑的赛道路径，动态计算小车位置和角度。s-t图实时绘制，并通过闪烁的点与赛车位置关联。

DerivativeAnimation:

功能: 演示导数几何意义的核心动画。能在Canvas上绘制函数图像、P点和Q点，并通过平滑动画将连接两点的割线转变为P点的切线。

技术: 实时计算并显示割线斜率。通过缓动函数 (Easing) 控制 Δx 的变化，实现Q点向P点的平滑逼近。能够清晰地在图中标注 Δx 和 Δy。

TableAnimation:

功能: 以动态、逐行浮现的方式展示数值近似表。

技术: 基于DOM和CSS transition，通过JavaScript的 setTimeout 控制每一行 <tr> 元素的 visible 类的添加，产生交错动画效果。

SpeedometerAnimation:

功能: 将物理情境推向高潮。它在一个Canvas上绘制s−t图像和切线，同时驱动另一个DOM元素构成的模拟速度计。

技术: 实时计算曲线上某点的导数（瞬时速度），并将该数值映射为速度计指针的旋转角度，实现数据与UI的完美联动。

ComparisonAnimation:

功能: 用于对比正确与错误的概念，或展示特殊案例。

技术: 主要通过DOM元素的显隐和CSS动画实现。例如，先同时展示“正确”与“错误”面板，随后“错误”面板淡出，“尖点案例”面板淡入。

5. 核心工作流 (自动播放)
用户点击“自动播放”按钮。

PlaybackOrchestrator 启动，进入循环。

For slide = 1 to totalSlides:
a.  UIManager 调用 showSlide(slide)。
b.  showSlide 激活当前幻灯片，并触发 AnimationManager 启动该页的动画控制器 (controller.start())。
c.  PlaybackOrchestrator 调用 SDKCoordinator 的 speakContent(slide)。
d.  SDKCoordinator 向讯飞SDK发送语音和动作指令。
e.  PlaybackOrchestrator await 等待 speakContent 函数返回的Promise完成（即waitForSpeechEndOrTimeout完成）。
f.  语音结束后，PlaybackOrchestrator 等待一个固定的缓冲时间 sleep(800)。
g.  循环进入下一页。

循环结束，PlaybackOrchestrator 更新状态为“播放结束”。

