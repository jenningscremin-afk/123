# agents.md — 通用课程生产规范（Video 系列 + 虚拟人）

> 适配你的现有样式与蓝图：四区布局（黑板/动画/字幕/控制）、MathJax、讯飞虚拟人 SDK、自动播放与键盘导航。用于 **Video 3.1** 及后续章节的“可复制生产”与“自动化生成”。

---

## 0) 元信息

* **Repo / Track**：`jenningscremin-afk/12345` → `codex/generate-html-code-for-video-3.1`
* **目标产物**：单文件 `video-<chapter>-<section>.html`（或 `video-3-1.html`）+ 可选 `assets/`
* **唯一真源（SSOT）**：《视频课程生产蓝图.md》各章节“虚拟人讲稿 / 幻灯片执行矩阵 / 动画脚本”

---

## 1) 任务定义（Codex）

**Goal**：从蓝图中的“章节 N.M”读取讲稿、动作与时长，**生成完整 HTML**：

* 复用既有 **四区 UI**：左黑板、右 Canvas 动画、底部字幕、左侧控制栏
* 接入 **虚拟人 SDK**：鉴权、动作、发声、字幕同步
* 支持 **自动播放**：按每页时长顺序演示；禁用/解锁导航；录制友好
* **键盘操作**：←/→、空格、Enter（开始）、Esc（停止自动）

**Non‑Goals**：不承担视频导出与云端上传；不解决素材版权与配音人授权。

---

## 2) 页面壳（可复用）

```html
<body class="blackboard">
  <div id="statusIndicator" class="status-indicator">等待连接</div>
  <div class="avatar-container"><div class="wrapper" id="avatarWrapper"></div></div>
  <div id="slide-container" class="slide-container flex-grow">
    <!-- 每页 slide：左黑板（.blackboard-text）+ 右动画（.animation-pane > canvas.animationCanvas） -->
    <div class="slide active">
      <div class="slide-content">
        <div class="blackboard-text w-1/2">…</div>
        <div class="animation-pane w-1/2"><canvas class="animationCanvas"></canvas></div>
      </div>
    </div>
  </div>
  <div class="subtitle-area" id="subtitleArea">欢迎学习！</div>
  <div class="control-bar">…上一页/开始讲课/自动播放/下一页/重启…</div>
</body>
```

### 2.1 样式基线

* 背景 `#1a1a2e`；正文字体 `Noto Serif SC`；黑板文字 `#e0e0e0`
* 标题高亮 `#f1c40f`；公式边线 `#f39c12`；警示 `#e74c3c`
* `.slide` 使用 `opacity + visibility` 切换；`.slide-content` 左右分栏；`control-bar` 悬停滑出

> 此处样式可直接复用你现有页面 CSS 片段（标题、数学公式卡片、控制栏 hover 展开、按钮风格）。

---

## 3) 数据契约（每一页）

```ts
interface SlideSpec {
  page: number;            // 1..N
  boardHTML: string;       // 左侧黑板区（允许 MathJax）
  animId?: string;         // 右侧 Canvas 动画类名或模块 key
  speak: string;           // 虚拟人讲稿（纯文本）
  actions?: string[];      // 虚拟人动作序列 ["A_RLH_welcome_O", ...]
  durationMs: number;      // 本页停留时长（蓝图秒数 → 毫秒）
}
```

* **subtitleScript**：由 `SlideSpec.speak` 聚合，运行时投喂虚拟人 + 字幕区
* **getActionsForPage(n)**：由 `SlideSpec.actions` 生成
* **getSlideDuration(n)**：读取 `SlideSpec.durationMs`

---

## 4) 虚拟人集成（SDK）

### 4.1 引入与就绪

```html
<script type="module">
  const { default: AvatarPlatform } = await import('./avatar-sdk-web_3.1.2.1002/index.js');
  window.dispatchEvent(new CustomEvent('sdkReady'));
</script>
```

### 4.2 鉴权与全局参数

```js
avatarPlatform.setApiInfo({
  appId: '98c558c1',
  apiKey: '133adcc14bda6e315040f78700b38267',
  apiSecret: 'NjJmZmM5YTM2YzBhZTY3NzEzMGVmMDIy',
  sceneId: '216155854796361728',
  serverUrl: 'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact'
});

avatarPlatform.setGlobalParams({
  stream: { protocol: 'xrtc', fps: 25, bitrate: 1000000 },
  avatar: { avatar_id: '110332017', width: 1920, height: 1080 },
  tts: { vcn: 'x4_yiting', speed: 50, pitch: 50, volume: 100 },
  avatar_dispatch: { interactive_mode: 1, content_analysis: 0 }
});
```

### 4.3 播放管线（最小实现）

```js
async function speakContent(n){
  const slide = slidesSpec[n-1];
  if (!slide) return;
  // 动作
  for (const a of (slide.actions||[])) { try { await avatarPlatform.writeCmd('action', a); } catch(e){} }
  // 讲稿
  if (slide.speak) {
    await avatarPlatform.writeText(slide.speak, { nlp: false });
    subtitleArea.textContent = slide.speak; // 同步字幕
  }
}

async function startAutoPlay(){
  for (let n=1; n<=slidesSpec.length; n++) {
    switchToSlide(n);          // 切页（UI/动画）
    await speakContent(n);     // 讲稿 + 动作
    await wait(slideDuration(n) + 800); // 节奏缓冲
  }
}
```

---

## 5) 动画框架（Canvas）

* 抽象父类 `BaseAnimation`：`resizeCanvas()` + `start/stop()` + `requestAnimationFrame`
* 每页一个派生类（或复用），在 `showSlide(index)` 中统一启停

```js
class BaseAnimation {
  constructor(canvas){ this.canvas = canvas; this.ctx = canvas.getContext('2d'); this.isActive = false; this.resizeCanvas(); window.addEventListener('resize', () => this.resizeCanvas()); }
  resizeCanvas(){ const c = this.canvas.parentElement; if(!c) return; this.canvas.width = c.clientWidth; this.canvas.height = c.clientHeight; }
  start(){ this.isActive = true; this.animate(); }
  stop(){ this.isActive = false; cancelAnimationFrame(this._raf); }
  animate(){ if (!this.isActive) return; this._raf = requestAnimationFrame(() => this.animate()); }
}
```

> 典型派生：标题线描、连续三条件渐显、间断分类机、Δx/Δy 增量演示等。统一颜色/线宽与标签。

---

## 6) 控制与可访问性

* **控制栏**：上一页 / 下一页 / 重新开始 / 开始讲课 / 自动播放；录制模式下隐藏 UI
* **键盘**：→/空格=下一页，←=上一页，Enter=开始，Esc=停播
* **字幕区**：`aria-live="polite"`；颜色对比达 AA；颜色非唯一编码

---

## 7) 生成规范（从蓝图到 HTML）

1. 解析蓝图章节（N.M）：抽取 **板书文案**、**虚拟人讲稿**、**动作**、**建议时长**
2. 构造 `slidesSpec: SlideSpec[]` → 渲染左侧黑板（支持 MathJax）
3. 为每一页绑定/复用动画类；在 `showSlide()` 中 `controller.start()/stop()`
4. 初始化虚拟人 → `startAutoPlay()`（可切换为手动）
5. 验证节奏（总时长/单页时长）与字幕、动作一致

---

## 8) 目录结构（建议）

```
video-3-1.html
assets/
  tailwind.min.js
  noto-serif-sc.css
  modules/
    base.js           # BaseAnimation
    anim-*.js         # 各页动画
    avatar.js         # SDK 封装
    slides-3-1.js     # SlideSpec 数据
```

---

## 9) 验收标准（DoD）

* 打开 HTML 即可运行；MathJax 正常；切页与自动播放无抖动
* 虚拟人能连接并按页 **动作 + 讲稿** 同步；字幕区与语音一致
* 动画在 DPR=1/2/3 下标签不重叠；窗口 resize 后无拉伸/模糊
* 自动播放一遍通过：**无报错、帧率流畅、字幕/讲稿/动作/节拍一致**

---

## 10) 质量清单（手测 + 轻测）

* [ ] 连接 SDK 成功；异常时给出 UI 提示并可重试
* [ ] 1→N 页自动播放完成；每页时长符合蓝图秒数
* [ ] 讲稿出现前，先切页；讲稿期间禁用导航；完结后解锁
* [ ] 颜色与字重一致；黑板区排版不与动画区重叠
* [ ] 键盘与按钮均可驱动完整流程

---

## 11) 典型差异位（可定制）

* 语音人 `vcn` / 语速 `speed`
* 控制栏位置（左/右）与显隐策略
* 动画采样密度与线宽（性能与清晰度的权衡）

---

## 12) 安全与合规

* 鉴权信息建议在内网构建时注入，外发 Demo 前请做掩码或换用测试凭据
* 所有外链（CDN 字体/脚本）提供离线备份；无网环境保证可演示

---

## 13) 开发到执行（短流程）

1. `slides-3-1.js`：填 `SlideSpec[]`
2. `anim-*.js`：复用或实现动画类
3. `avatar.js`：初始化与 `speakContent()` / `startAutoPlay()`
4. `video-3-1.html`：拼装四区壳 + 控件 + 脚本引入
5. 本地起服，逐页核对并录屏

---

## 14) 示例占位（Video 3.1）

* Page 1：导数引入（车与 s(t) 曲线）；讲稿：瞬时变化率直觉；动作：欢迎/指向
* Page 2：割线定义（y=x², P(1,1), Q 可变）；Δx/Δy 标签
* Page 3：割线→切线（Δx: 2→0.01，斜率 4.000→2.010，终帧 f'(1)=2）
* Page 4：数值表（Δx, 割线斜率, 与 2 的误差）
* Page 5：物理速度计（s(t)=6t+1.75t², v(t)=6+3.5t）
* Page 6：易错对比（切线 vs 割线；|x| 尖点不可导）

> 将蓝图中 3.1 的“讲稿/时长/动作”填入 `SlideSpec[]` 即可生成最终页。
