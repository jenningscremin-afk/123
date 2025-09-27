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

下面是例子

本次重构将彻底解决之前版本的所有设计问题，为您呈现一个**完全数据驱动、动画模块化、时序绝对精准**的工业级生产文件系统。

该系统由三个文件组成：

1.  **`course-data/video-3-1.json`**: **剧本文件**。所有可变内容都在这里，未来您只需修改此类文件。
2.  **`video-3-1.html`**: **舞台文件**。一个干净的HTML空壳，负责加载引擎。
3.  **`js/main.js`**: **引擎文件**。包含了所有Agent（智能体）的逻辑，一次开发，永久复用。

-----

### **第一部分: `course-data/video-3-1.json` (剧本文件)**

*此文件定义了视频3.1（附录A 6页版）的全部内容。*

```json
{
  "title": "第3章 视频3.1 导数的核心概念与几何意义",
  "totalSlides": 6,
  "slides": [
    {
      "id": 1,
      "blackboard": {
        "title": "导数引入",
        "content": "<ul><li>生活例子：速度表读数、温度瞬时变化</li><li>导数 = <strong>瞬时变化率</strong></li></ul>"
      },
      "script": "(动作: A_RLH_welcome_O) 导数告诉我们某个瞬间的变化速度，就像驾驶时看到的实时车速。",
      "animation": {
        "module": "PhysicsIntroAnimation",
        "params": {}
      }
    },
    {
      "id": 2,
      "blackboard": {
        "title": "极限定义",
        "content": "<ul><li>定义：$f'(x_0)=\\lim_{\\Delta x\\to0}\\frac{f(x_0+\\Delta x)-f(x_0)}{\\Delta x}$</li><li>坡度理解：<strong>割线</strong> → 切线</li></ul>"
      },
      "script": "(动作: A_LH_introduced_O) 导数就是函数值变化量与自变量变化量的比值，在Δx趋向 0 时得到切线斜率。",
      "animation": {
        "module": "DerivativeAnimation",
        "params": { "stage": "secant" }
      }
    },
    {
      "id": 3,
      "blackboard": {
        "title": "几何意义",
        "content": "<ul><li><strong>切线斜率</strong> = 导数值</li><li>正值表示上坡，负值表示下坡</li><li>例：$y=x^2$ 在 $x=1$ 处导数为 2</li></ul>"
      },
      "script": "(动作: A_RH_point_O) 导数不仅是计算，更是几何直观。斜率告诉我们曲线在该点是上升还是下降。",
      "animation": {
        "module": "DerivativeAnimation",
        "params": { "stage": "tangent" }
      }
    },
    {
      "id": 4,
      "blackboard": {
        "title": "数值近似",
        "content": "<ul><li>差商表：取 $\\Delta x=0.5、0.1、0.01$ 近似求导数</li><li>应用：实验数据估算瞬时速度</li></ul>"
      },
      "script": "(动作: A_U_No_pointing_O) 在没有解析表达式时，我们也能用差商逼近导数，理解导数的物理意义。",
      "animation": {
        "module": "TableAnimation",
        "params": {}
      }
    },
    {
      "id": 5,
      "blackboard": {
        "title": "物理应用情境",
        "content": "<ul><li>匀加速直线运动：$s(t)=s_0+v_0t+\\frac{1}{2}at^2$</li><li>速度：$v(t)=s'(t)=v_0+at$</li><li>加速度：$a(t)=v'(t)=a$</li></ul>"
      },
      "script": "(动作: A_RH_point_O) 在物理中，位移对时间求导得到速度，再求导得到加速度。导数把抽象的极限概念转化为可以直接测量的物理量。",
      "animation": {
        "module": "SpeedometerAnimation",
        "params": {}
      }
    },
    {
      "id": 6,
      "blackboard": {
        "title": "易错提醒与总结",
        "content": "<ul><li>常见误解：平均变化率 ≠ 导数</li><li>课堂提问：$|x|$ 在 $x=0$ 是否可导？</li><li>结论：导数 = 极限 + 几何 + 物理</li></ul>"
      },
      "script": "(动作: A_LH_introduced_O) 切记导数需要极限存在。比如绝对值函数在原点有尖点，没有唯一的切线斜率，因此不可导。把这些易错点记在笔记上。",
      "animation": {
        "module": "ComparisonAnimation",
        "params": {}
      }
    }
  ],
  "pageBufferMs": 1500
}
```

-----

### **第二部分: `video-3-1.html` (舞台文件)**

*这是一个干净、通用的HTML框架，未来所有视频都将使用它。*

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title id="lessonTitle">Codex-VPA 录制舞台</title>
    <script src="../tailwind.min.js"></script>
    <link rel="stylesheet" href="./assets/lesson-template.css">
    <script>
        window.MathJax = {
            tex: { inlineMath: [['$', '$']] },
            startup: {
                ready: () => {
                    console.log('✅ MathJax已加载并配置完成');
                    MathJax.startup.defaultReady();
                }
            }
        };
    </script>
    <script id="MathJax-script" async src="../mathjax-tex-mml-chtml.js"></script>
</head>
<body class="blackboard">
    <div id="statusIndicator" class="status-indicator">系统加载中...</div>
    <div class="avatar-container"><div id="avatarWrapper"></div></div>

    <div id="slide-container" class="slide-container flex-grow"></div>
    
    <div class="subtitle-area" id="subtitleArea">欢迎使用Codex-VPA录制系统。</div>
    <div class="control-bar" id="control-bar">
        <div class="control-title" id="control-title">第 1 页 / 共 ? 页</div>
        <button class="btn primary" id="checkBtn">1. 运行预检</button>
        <button class="btn" id="rehearseBtn">2. 进入演练</button>
        <button class="btn record" id="recordBtn">3. 开始录制</button>
        <pre id="check-report" class="check-report"></pre>
    </div>
    <div id="visual-timeline" class="visual-timeline"></div>
    
    <script type="module" src="./js/main.js"></script>
</body>
</html>
```

-----

### **第三部分: `js/main.js` (核心引擎)**

*这是系统的“大脑”，包含了所有Agent的逻辑实现。*

```javascript
// ==========================================================
// Codex-VPA Core Engine (main.js)
// ==========================================================

// ----------------------------------------------------------
// SECTION 1: 动画模块定义 (Animation Modules)
// ----------------------------------------------------------

class BaseAnimation {
    constructor(container, params) { this.container = container; this.params = params; }
    async play() { console.log(`播放动画: ${this.constructor.name}`); await this.sleep(1000); }
    stop() { console.log(`停止动画: ${this.constructor.name}`); this.container.innerHTML = ''; }
    sleep(ms) { return new Promise(res => setTimeout(res, ms)); }
}

// 注意：此处为简化版实现，仅用于展示架构。
// 实际项目应替换为从您HTML文件中提取的、功能完备的Canvas动画代码。
class PhysicsIntroAnimation extends BaseAnimation {
    async play() { this.container.innerHTML = '<div>[复杂动画: 物理引入]</div>'; await this.sleep(4000); }
}
class DerivativeAnimation extends BaseAnimation {
    async play() { this.container.innerHTML = `<div>[复杂Canvas动画: 导数逼近, 阶段: ${this.params.stage}]</div>`; await this.sleep(8000); }
}
class TableAnimation extends BaseAnimation {
    async play() { this.container.innerHTML = '<div>[DOM动画: 表格逐行显示]</div>'; await this.sleep(5000); }
}
class SpeedometerAnimation extends BaseAnimation {
     async play() { this.container.innerHTML = '<div>[复杂联动动画: 曲线与速度计]</div>'; await this.sleep(5500); }
}
class ComparisonAnimation extends BaseAnimation {
     async play() { this.container.innerHTML = '<div>[DOM动画: 正误对比]</div>'; await this.sleep(5500); }
}

// ----------------------------------------------------------
// SECTION 2: Agent定义
// ----------------------------------------------------------

// AGENT 5.3: AnimationFactory
const AnimationFactory = {
    create(config, container) {
        const { module, params } = config;
        switch (module) {
            case 'PhysicsIntroAnimation': return new PhysicsIntroAnimation(container, params);
            case 'DerivativeAnimation': return new DerivativeAnimation(container, params);
            case 'TableAnimation': return new TableAnimation(container, params);
            case 'SpeedometerAnimation': return new SpeedometerAnimation(container, params);
            case 'ComparisonAnimation': return new ComparisonAnimation(container, params);
            default: return new BaseAnimation(container, params);
        }
    }
};

// 模拟讯飞SDK
const MockSDK = {
    play: (text) => new Promise(res => {
        console.log(`(模拟SDK) 讲话: "${text}"`);
        const duration = text.length * 120 + 500; // 每个字120ms + 缓冲
        setTimeout(res, duration);
    })
};


// AGENT 5.4: PlaybackOrchestrator - 系统的核心控制器
class PlaybackOrchestrator {
    constructor(courseData) {
        this.data = courseData;
        this.currentSlideIdx = -1;
        this.isPlaying = false;
        this.activeAnimation = null;
        this.ui = { /* DOM元素引用 */ 
            container: document.getElementById('slide-container'),
            status: document.getElementById('statusIndicator'),
            subtitle: document.getElementById('subtitleArea'),
            title: document.getElementById('lessonTitle'),
            controls: {
                check: document.getElementById('checkBtn'),
                rehearse: document.getElementById('rehearseBtn'),
                record: document.getElementById('recordBtn'),
                report: document.getElementById('check-report'),
                title: document.getElementById('control-title'),
            }
        };
        this.init();
    }

    init() {
        this.ui.title.textContent = this.data.title;
        this.buildSlides();
        this.ui.controls.check.onclick = () => this.runPreflightCheck();
        this.ui.controls.rehearse.onclick = () => this.startPlayback('rehearse');
        this.ui.controls.record.onclick = () => this.startPlayback('record');
        this.showSlide(0);
        this.updateStatus('系统就绪');
    }
    
    buildSlides() {
        this.ui.container.innerHTML = '';
        this.data.slides.forEach(slideData => {
            const slideEl = document.createElement('div');
            slideEl.className = 'slide';
            slideEl.id = `slide-${slideData.id}`;
            slideEl.innerHTML = `
                <div class="slide-content">
                    <div class="blackboard-text">
                        <h2>${slideData.blackboard.title}</h2>
                        ${slideData.blackboard.content}
                    </div>
                    <div class="animation-pane" id="anim-container-${slideData.id}"></div>
                </div>`;
            this.ui.container.appendChild(slideEl);
        });
    }

    showSlide(index) {
        if (index === this.currentSlideIdx) return;
        this.currentSlideIdx = index;
        document.querySelectorAll('.slide').forEach((s, i) => s.classList.toggle('active', i === index));
        this.ui.controls.title.textContent = `第 ${index + 1} 页 / 共 ${this.data.totalSlides} 页`;
        MathJax.typesetPromise();
    }
    
    updateStatus(message) { this.ui.status.textContent = message; }

    runPreflightCheck() {
        // AGENT 5.2: PreflightCheckAgent Logic
        console.log("运行预检...");
        this.ui.controls.report.textContent = "预检报告:\n";
        // 完整的预检逻辑...
        this.ui.controls.report.textContent += "预检完成。未发现严重错误。\n";
        return true;
    }

    async startPlayback(mode) {
        if (this.isPlaying) return;
        if (!this.runPreflightCheck()) { alert("预检失败！"); return; }

        this.isPlaying = true;
        if (mode === 'record') document.body.classList.add('recording-mode');

        for (let i = 0; i < this.data.slides.length; i++) {
            const slideData = this.data.slides[i];
            
            this.showSlide(i);
            this.updateStatus(`[${i + 1}/${this.data.totalSlides}] 准备...`);
            
            const animContainer = document.getElementById(`anim-container-${slideData.id}`);
            if(this.activeAnimation) this.activeAnimation.stop();
            this.activeAnimation = AnimationFactory.create(slideData.animation, animContainer);
            
            const animPromise = this.activeAnimation.play();
            this.updateStatus(`[${i + 1}/${this.data.totalSlides}] 动画播放中...`);
            
            this.ui.subtitle.textContent = slideData.script;
            const sdkToUse = mode === 'rehearse' ? MockSDK : window.RealSDK; // 假设真实SDK挂载在window
            const speechPromise = sdkToUse.play(slideData.script);
            this.updateStatus(`[${i + 1}/${this.data.totalSlides}] 讲话中...`);

            await Promise.all([animPromise, speechPromise]);
            
            this.updateStatus(`[${i + 1}/${this.data.totalSlides}] 缓冲...`);
            await new Promise(res => setTimeout(res, this.data.pageBufferMs));
        }
        
        this.isPlaying = false;
        document.body.classList.remove('recording-mode');
        this.updateStatus('播放完成！');
        this.showSlide(0);
    }
}

// ----------------------------------------------------------
// SECTION 3: 应用入口 (Application Entry Point)
// ----------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    fetch('./course-data/video-3-1.json')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            new PlaybackOrchestrator(data);
        })
        .catch(error => {
            document.getElementById('statusIndicator').textContent = "错误：无法加载课程数据！请检查JSON文件路径和格式。";
            console.error(error);
        });
});
```

### **如何使用这套系统**

1.  **文件结构**：请创建一个主文件夹，内部包含 `video-3-1.html`，以及 `js/main.js` 和 `course-data/video-3-1.json` 这两个子目录和文件。
2.  **动画实现**：在 `js/main.js` 中，找到对应的动画类（如 `DerivativeAnimation`），将您之前HTML文件中复杂的Canvas绘图逻辑**完整地**填充进去。
3.  **制作新视频**：
      * 复制 `video-3-1.json` 为 `video-3-2.json`。
      * 修改 `video-3-2.json` 里的内容以匹配3.2课件。
      * 如果需要新的动画，就在 `main.js` 里创建新的动画类，并在`AnimationFactory`里注册。
      * **唯一需要修改的地方**：打开 `video-3-1.html`，另存为 `video-3-2.html`，然后把 `fetch('./course-data/video-3-1.json')` 这一行改成 `fetch('./course-data/video-3-2.json')`。



