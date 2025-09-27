#!/usr/bin/env python3
"""Generate HTML lesson files for chapters 3-13 from the production blueprint.

This script parses the markdown blueprint (《视频课程生产蓝图.md》) and
produces fully-rendered HTML files following the four-area layout required by
the project guidelines. The generated files are placed in the same directory as
this script with names like ``video-3-1.html``.

Only videos whose identifiers fall between 3.x and 13.x (inclusive) are
generated. The script intentionally keeps dependencies minimal so it can run in
the constrained execution environment.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Iterable, List, Optional


BLUEPRINT_PATH = Path(__file__).with_name("视频课程生产蓝图.md")
OUTPUT_DIR = Path(__file__).parent
VIDEO_PATTERN = re.compile(r"^###\s+视频\s+(?P<id>\d+\.\d+)\s*:\s*(?P<title>.+?)\s*$")
PAGE_PATTERN = re.compile(
    r"^####\s+页面\s+(?P<page>\d+)/(?:\d+)\s*-\s*(?P<title>.+?)\s*\((?P<seconds>\d+)秒\)"
)


@dataclass
class Slide:
    page: int
    title: str
    duration_ms: int
    board_html: str = ""
    animation_html: str = ""
    speak: str = ""
    actions: List[str] = field(default_factory=list)


@dataclass
class Video:
    identifier: str
    title: str
    chapter_title: str
    slides: List[Slide] = field(default_factory=list)

    @property
    def output_name(self) -> str:
        chapter, section = self.identifier.split(".")
        return f"video-{chapter}-{section}.html"


def load_lines(path: Path) -> List[str]:
    content = path.read_text(encoding="utf-8")
    return content.splitlines()


def current_chapter_title(lines: Iterable[str], start_index: int) -> str:
    """Walk backwards from ``start_index`` to find the nearest chapter title."""

    chapter_header = re.compile(r"^##\s+(第[^：]+章：.+)$")
    for idx in range(start_index, -1, -1):
        line = lines[idx].strip()
        match = chapter_header.match(line)
        if match:
            return match.group(1)
    return ""


def simple_markdown_to_html(lines: Iterable[str]) -> str:
    html_parts: List[str] = []
    in_list = False
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        bullet_match = re.match(r"^[*-]\s*(.+)", stripped)
        nested_bullet_match = re.match(r"^\*?\s*[-*]\s*(.+)", stripped)

        if bullet_match or (not stripped.startswith("**") and nested_bullet_match):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            content = (bullet_match or nested_bullet_match).group(1).strip()
            html_parts.append(f"  <li>{content}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{stripped}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def parse_actions_and_script(lines: Iterable[str]) -> tuple[List[str], str]:
    actions: List[str] = []
    script_lines: List[str] = []

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue

        action_match = re.match(r"^\(动作[:：]\s*([^)]+)\)\s*(.*)$", stripped)
        if action_match:
            action_raw = action_match.group(1)
            actions = [item.strip() for item in re.split(r"[、,，/]+", action_raw) if item.strip()]
            remainder = action_match.group(2)
            if remainder:
                script_lines.append(_strip_quotes(remainder))
            continue

        script_lines.append(_strip_quotes(stripped))

    script = "\n".join(line for line in script_lines if line)
    return actions, script


def _strip_quotes(text: str) -> str:
    return text.strip('"“”')


def parse_blueprint(path: Path) -> List[Video]:
    lines = load_lines(path)
    videos: List[Video] = []
    current_video: Optional[Video] = None
    current_slide: Optional[Slide] = None
    section_buffer: List[str] = []
    active_section: Optional[str] = None

    def flush_section():
        nonlocal section_buffer, active_section, current_slide
        if current_slide is None or active_section is None:
            section_buffer = []
            active_section = None
            return

        if active_section == "board":
            current_slide.board_html = simple_markdown_to_html(section_buffer)
        elif active_section == "animation":
            current_slide.animation_html = simple_markdown_to_html(section_buffer)
        elif active_section == "script":
            actions, speak = parse_actions_and_script(section_buffer)
            current_slide.actions = actions
            current_slide.speak = speak

        section_buffer = []
        active_section = None

    def flush_slide():
        nonlocal current_slide, current_video
        flush_section()
        if current_video and current_slide:
            current_video.slides.append(current_slide)
        current_slide = None

    def flush_video():
        nonlocal current_video
        flush_slide()
        if current_video:
            videos.append(current_video)
        current_video = None

    for idx, line in enumerate(lines):
        stripped = line.strip()

        video_match = VIDEO_PATTERN.match(stripped)
        if video_match:
            flush_video()
            identifier = video_match.group("id")
            # Only keep videos within chapters 3-13
            chapter_num = int(identifier.split(".")[0])
            if 3 <= chapter_num <= 13:
                chapter_title = current_chapter_title(lines, idx)
                current_video = Video(
                    identifier=identifier,
                    title=video_match.group("title"),
                    chapter_title=chapter_title,
                )
            else:
                current_video = None
            continue

        if current_video is None:
            continue

        page_match = PAGE_PATTERN.match(stripped)
        if page_match:
            flush_slide()
            page = int(page_match.group("page"))
            seconds = int(page_match.group("seconds"))
            current_slide = Slide(
                page=page,
                title=page_match.group("title"),
                duration_ms=seconds * 1000,
            )
            continue

        if stripped.startswith("**板书内容**"):
            flush_section()
            active_section = "board"
            section_buffer = []
            continue

        if stripped.startswith("**动画脚本**"):
            flush_section()
            active_section = "animation"
            section_buffer = []
            continue

        if stripped.startswith("**虚拟人讲稿**"):
            flush_section()
            active_section = "script"
            section_buffer = []
            continue

        if active_section:
            section_buffer.append(line)

    flush_video()
    return videos


def extract_animation_lines(raw_html: str) -> List[str]:
    if not raw_html:
        return ["参照蓝图补充动画。"]

    text = raw_html
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|li|h\d)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", item).strip() for item in text.splitlines()]
    cleaned = [line for line in lines if line]
    return cleaned or ["参照蓝图补充动画。"]




def detect_primary_function(slide: Slide) -> str:
    """Infer a function family from the slide content."""

    html_source = (slide.board_html or "") + " " + (slide.animation_html or "")
    text = re.sub(r"<[^>]+>", " ", html_source)
    text = html.unescape(text)
    lowered = text.lower()

    mapping = [
        ("absolute", ["|x|", "绝对值"]),
        ("log", ["ln", "对数", "log"]),
        ("exponential", ["e^", "指数", "exp"]),
        ("sine", ["sin", "正弦"]),
        ("cosine", ["cos", "余弦"]),
        ("tangent", ["tan", "正切"]),
        ("cubic", ["x^3", "x³", "三次"]),
        ("quartic", ["x^4", "x⁴", "四次"]),
        ("rational", ["/x", "分母", "有理"]),
        ("sqrt", ["√", "根号"]),
    ]

    for name, keywords in mapping:
        for key in keywords:
            if key.lower() in lowered:
                return name

    if "x^2" in lowered or "x²" in lowered or "平方" in lowered:
        return "parabola"

    return "parabola"


def build_animation_plan(slide: Slide, lines: List[str]) -> dict:
    """Translate animation notes into a drawable plan."""

    concatenated = " ".join(lines)
    lowered = concatenated.lower()
    duration = max(3000, slide.duration_ms or 5000)
    plan: dict[str, object] = {
        "title": slide.title,
        "duration": duration,
        "background": "grid",
        "items": [],
    }

    function_name = detect_primary_function(slide)

    def add_item(item: dict) -> None:
        plan["items"].append(item)

    if any(keyword in concatenated for keyword in ["速度表", "速度计", "车速"]):
        add_item({"type": "gauge", "label": "速度", "min": 0, "max": 180})

    if "温度" in concatenated:
        add_item({"type": "thermo", "label": "温度"})

    if any(key in concatenated for key in ["割线", "切线", "Δx", "斜率"]):
        add_item({"type": "secant", "function": function_name, "anchor": 1})

    if "对比" in concatenated and "切线" in concatenated:
        add_item({"type": "tangentComparison", "function": function_name})

    if any(key in concatenated for key in ["表格", "差商", "数据表", "近似"]):
        add_item({
            "type": "table",
            "rows": [
                {"dx": 0.5, "slope": 2.25},
                {"dx": 0.1, "slope": 2.05},
                {"dx": 0.01, "slope": 2.001},
            ],
        })

    if any(key in concatenated for key in ["位移", "速度-时间", "加速度", "物理"]):
        add_item({"type": "dualGraph"})

    if "不可导" in concatenated or "|x|" in concatenated:
        add_item({"type": "cusp"})

    if any(key in concatenated for key in ["流程图", "步骤图", "结构图"]):
        add_item({"type": "flow"})

    if any(key in concatenated for key in ["清单", "checklist", "勾选"]):
        add_item({"type": "checklist", "count": max(3, len(lines))})

    if any(key in concatenated for key in ["练习", "思考", "倒计时"]):
        add_item({"type": "exercise", "countdown": 8})

    if "倒计时" in concatenated:
        add_item({"type": "countdown", "seconds": 8})

    if any(key in concatenated for key in ["错误", "打叉", "易错"]):
        add_item({"type": "errorHighlight"})

    if any(key in concatenated for key in ["面积", "积分", "定积分"]):
        add_item({"type": "areaUnderCurve", "function": function_name})

    if any(key in concatenated for key in ["极值", "最小", "最大", "拐点"]):
        add_item({"type": "extremaScene", "function": function_name})

    if any(key in concatenated for key in ["级数", "泰勒", "幂级数", "数列"]):
        add_item({"type": "series"})

    if any(key in concatenated for key in ["向量", "梯度", "方向导数", "场"]):
        add_item({"type": "vectorField"})

    if not plan["items"]:
        add_item({"type": "concept", "count": max(3, len(lines) or 3)})

    return plan


def build_animation_functions(slides: List[Slide]) -> tuple[str, str, str]:
    ordered_slides = sorted(slides, key=lambda s: s.page)
    function_snippets: List[str] = []
    start_cases: List[str] = []
    stop_cases: List[str] = []
    common_helpers = """
    const TWO_PI = Math.PI * 2;

    function createCanvasState(canvas) {
      const ctx = canvas.getContext('2d');
      const dpr = window.devicePixelRatio || 1;
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      let logicalWidth = 0;
      let logicalHeight = 0;

      function resize() {
        const rect = canvas.getBoundingClientRect();
        const width = Math.max(1, Math.floor(rect.width * dpr));
        const height = Math.max(1, Math.floor(rect.height * dpr));
        if (canvas.width !== width || canvas.height !== height) {
          canvas.width = width;
          canvas.height = height;
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        logicalWidth = rect.width || canvas.width / dpr;
        logicalHeight = rect.height || canvas.height / dpr;
      }

      resize();

      return {
        ctx,
        dpr,
        resize,
        get width() {
          return logicalWidth || canvas.width / dpr;
        },
        get height() {
          return logicalHeight || canvas.height / dpr;
        },
      };
    }

    function drawBackground(ctx, plan, width, height) {
      ctx.save();
      const bg = plan.background === 'dark' ? '#061225' : '#0d1a33';
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, width, height);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      const step = Math.max(24, Math.min(width, height) / 12);
      ctx.lineWidth = 1;
      for (let x = step; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = step; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      ctx.restore();
    }

    function evaluateFunction(type, x) {
      switch (type) {
        case 'cubic':
          return 0.12 * Math.pow(x, 3) + 1.2;
        case 'quartic':
          return 0.04 * Math.pow(x, 4) + 0.5 * x + 1.1;
        case 'sine':
          return Math.sin(x) + 1.5;
        case 'cosine':
          return Math.cos(x) + 1.5;
        case 'tangent':
          return Math.tan(x * 0.6) * 0.4 + 1.5;
        case 'log':
          return Math.log(x + 2.6) + 1.0;
        case 'exponential':
          return Math.exp(x * 0.4) * 0.3 + 0.8;
        case 'sqrt':
          return Math.sqrt(Math.max(0, x + 2.4));
        case 'absolute':
          return Math.abs(x) * 0.8 + 0.4;
        case 'rational':
          return 1.2 + 1 / (x * x + 1.4);
        default:
          return 0.25 * Math.pow(x, 2) + 0.8;
      }
    }

    function derivativeAt(type, x) {
      switch (type) {
        case 'cubic':
          return 0.36 * Math.pow(x, 2);
        case 'quartic':
          return 0.16 * Math.pow(x, 3) + 0.5;
        case 'sine':
          return Math.cos(x);
        case 'cosine':
          return -Math.sin(x);
        case 'tangent':
          const cosSq = Math.pow(Math.cos(x * 0.6), 2);
          return 0.6 / Math.max(0.2, cosSq);
        case 'log':
          return 1 / Math.max(0.2, x + 2.6);
        case 'exponential':
          return 0.4 * Math.exp(x * 0.4);
        case 'sqrt':
          return 0.5 / Math.sqrt(Math.max(0.3, x + 2.4));
        case 'absolute':
          return x >= 0 ? 0.8 : -0.8;
        case 'rational':
          return -2 * x / Math.pow(x * x + 1.4, 2);
        default:
          return 0.5 * x;
      }
    }

    function renderPlan(ctx, plan, state, elapsed) {
      const width = state.width;
      const height = state.height;
      ctx.clearRect(0, 0, width, height);
      const margin = Math.min(width, height) * 0.1;
      const dims = { width, height, margin, centerX: width / 2, centerY: height / 2 };
      drawBackground(ctx, plan, width, height);
      plan.items.forEach((item, idx) => {
        renderItem(ctx, item, dims, elapsed, idx, plan);
      });
    }

    function renderItem(ctx, item, dims, elapsed, idx, plan) {
      switch (item.type) {
        case 'gauge':
          renderGauge(ctx, item, dims, elapsed);
          break;
        case 'thermo':
          renderThermo(ctx, item, dims, elapsed);
          break;
        case 'secant':
          renderSecant(ctx, item, dims, elapsed);
          break;
        case 'tangentComparison':
          renderTangentComparison(ctx, item, dims, elapsed);
          break;
        case 'table':
          renderTable(ctx, item, dims, elapsed);
          break;
        case 'dualGraph':
          renderDualGraph(ctx, item, dims, elapsed);
          break;
        case 'cusp':
          renderCusp(ctx, item, dims, elapsed);
          break;
        case 'flow':
          renderFlow(ctx, item, dims, elapsed);
          break;
        case 'checklist':
          renderChecklist(ctx, item, dims, elapsed);
          break;
        case 'exercise':
          renderExercise(ctx, item, dims, elapsed);
          break;
        case 'countdown':
          renderCountdown(ctx, item, dims, elapsed, plan);
          break;
        case 'errorHighlight':
          renderError(ctx, item, dims, elapsed);
          break;
        case 'areaUnderCurve':
          renderArea(ctx, item, dims, elapsed);
          break;
        case 'extremaScene':
          renderExtrema(ctx, item, dims, elapsed);
          break;
        case 'series':
          renderSeries(ctx, item, dims, elapsed);
          break;
        case 'vectorField':
          renderVectorField(ctx, item, dims, elapsed);
          break;
        default:
          renderConcept(ctx, item, dims, elapsed);
      }
    }

    function renderGauge(ctx, item, dims, elapsed) {
      const radius = Math.min(dims.width, dims.height) * 0.28;
      const cx = dims.margin + radius;
      const cy = dims.height - dims.margin * 0.8;
      const value = (Math.sin(elapsed * 1.2) * 0.5 + 0.5) * (item.max - item.min) + item.min;
      const angle = Math.PI + (value / (item.max - item.min)) * Math.PI;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
      ctx.beginPath();
      ctx.arc(0, 0, radius + 12, Math.PI, 0);
      ctx.lineTo(0, 0);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = '#2ecc71';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(0, 0, radius, Math.PI, 0);
      ctx.stroke();
      ctx.rotate(angle);
      ctx.strokeStyle = '#f39c12';
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.moveTo(-6, 0);
      ctx.lineTo(radius - 16, 0);
      ctx.stroke();
      ctx.restore();
      ctx.save();
      ctx.fillStyle = '#ecf0f1';
      ctx.font = `${Math.round(radius * 0.24)}px 'Noto Serif SC', serif`;
      ctx.textAlign = 'center';
      ctx.fillText(`${Math.round(value)} km/h`, cx, cy - radius * 0.55);
      ctx.restore();
    }

    function renderThermo(ctx, item, dims, elapsed) {
      const width = Math.min(60, dims.width * 0.12);
      const height = dims.height * 0.6;
      const x = dims.width - dims.margin - width;
      const y = dims.margin;
      const level = Math.sin(elapsed * 0.8) * 0.5 + 0.5;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x - 10, y - 10, width + 20, height + 40);
      ctx.fillStyle = '#1abc9c';
      ctx.fillRect(x, y, width, height);
      const h = height * (0.2 + 0.75 * level);
      const sy = y + height - h;
      ctx.fillStyle = '#e74c3c';
      ctx.fillRect(x + 6, sy, width - 12, h);
      ctx.fillStyle = '#ecf0f1';
      ctx.font = '18px "Noto Serif SC", serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${Math.round(12 + level * 28)}℃`, x + width / 2, sy - 12);
      ctx.restore();
    }

    function renderSecant(ctx, item, dims, elapsed) {
      const margin = dims.margin * 1.1;
      const width = dims.width - margin * 2;
      const height = dims.height - margin * 2;
      const ox = margin;
      const oy = dims.height - margin;
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.25)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(ox + width, oy);
      ctx.moveTo(ox, oy);
      ctx.lineTo(ox, oy - height);
      ctx.stroke();
      ctx.strokeStyle = '#3498db';
      ctx.lineWidth = 3;
      ctx.beginPath();
      const samples = 160;
      for (let i = 0; i <= samples; i += 1) {
        const t = (i / samples) * 4 - 2;
        const px = ox + (t + 2) / 4 * width;
        const val = evaluateFunction(item.function || 'parabola', t);
        const py = oy - (val / 4.5) * height;
        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
      const anchor = item.anchor ?? 1;
      const delta = 1.2 * Math.pow(Math.cos(elapsed * 0.6) * 0.5 + 0.5, 2);
      const x0 = anchor - 2;
      const x1 = x0 + delta * 0.6;
      const y0 = evaluateFunction(item.function || 'parabola', x0);
      const y1 = evaluateFunction(item.function || 'parabola', x1);
      const toCanvasX = (val) => ox + (val + 2) / 4 * width;
      const toCanvasY = (val) => oy - (val / 4.5) * height;
      const p0 = { x: toCanvasX(x0), y: toCanvasY(y0) };
      const p1 = { x: toCanvasX(x1), y: toCanvasY(y1) };
      ctx.strokeStyle = '#f1c40f';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();
      ctx.fillStyle = '#e74c3c';
      ctx.beginPath();
      ctx.arc(p0.x, p0.y, 6, 0, TWO_PI);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p1.x, p1.y, 6, 0, TWO_PI);
      ctx.fill();
      const slope = (y1 - y0) / Math.max(0.2, x1 - x0);
      const tangent = derivativeAt(item.function || 'parabola', x0);
      ctx.fillStyle = '#ecf0f1';
      ctx.font = '18px "Noto Serif SC", serif';
      ctx.fillText(`割线≈${slope.toFixed(2)}`, ox + 12, oy - height + 32);
      ctx.fillText(`切线→${tangent.toFixed(2)}`, ox + 12, oy - height + 60);
      ctx.restore();
    }

    function renderTangentComparison(ctx, item, dims, elapsed) {
      const width = dims.width;
      const height = dims.height;
      const half = width / 2;
      const margin = dims.margin * 0.8;
      const plotWidth = half - margin * 1.4;
      const plotHeight = height - margin * 2;
      const draw = (offset, funcType, anchor) => {
        ctx.save();
        ctx.translate(offset, margin);
        ctx.strokeStyle = '#16a085';
        ctx.lineWidth = 3;
        ctx.beginPath();
        const samples = 120;
        for (let i = 0; i <= samples; i += 1) {
          const t = (i / samples) * 4 - 2;
          const x = (t + 2) / 4 * plotWidth;
          const val = evaluateFunction(funcType, t);
          const y = plotHeight - (val / 4.5) * plotHeight;
          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
        const slope = derivativeAt(funcType, anchor);
        const px = (anchor + 2) / 4 * plotWidth;
        const py = plotHeight - (evaluateFunction(funcType, anchor) / 4.5) * plotHeight;
        const angle = Math.atan(slope);
        const len = plotWidth * 0.6;
        ctx.strokeStyle = '#f39c12';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(px - Math.cos(angle) * len, py + Math.sin(angle) * len);
        ctx.lineTo(px + Math.cos(angle) * len, py - Math.sin(angle) * len);
        ctx.stroke();
        ctx.restore();
      };
      draw(margin, item.function || 'parabola', 0.5);
      draw(half + margin * 0.5, 'cubic', 0);
    }

    function renderTable(ctx, item, dims, elapsed) {
      const rows = item.rows || [];
      const width = dims.width - dims.margin * 2;
      const height = dims.height * 0.4;
      const x = dims.margin;
      const y = dims.height - height - dims.margin;
      const rowHeight = height / (rows.length + 1);
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.45)';
      ctx.fillRect(x, y, width, height);
      ctx.strokeStyle = 'rgba(255,255,255,0.2)';
      ctx.lineWidth = 2;
      for (let i = 0; i <= rows.length; i += 1) {
        const yy = y + (i + 1) * rowHeight;
        ctx.beginPath();
        ctx.moveTo(x, yy);
        ctx.lineTo(x + width, yy);
        ctx.stroke();
      }
      const columns = ['Δx', '割线斜率'];
      const colWidth = width / columns.length;
      ctx.fillStyle = '#f1c40f';
      ctx.font = '20px "Noto Serif SC", serif';
      columns.forEach((col, idx) => {
        ctx.fillText(col, x + colWidth * idx + 16, y + rowHeight * 0.7);
      });
      const active = rows.length ? Math.floor((elapsed * 0.75) % rows.length) : 0;
      rows.forEach((row, idx) => {
        const rowY = y + rowHeight * (idx + 1.6);
        if (idx === active) {
          ctx.fillStyle = 'rgba(243, 156, 18, 0.35)';
          ctx.fillRect(x, rowY - rowHeight * 0.6, width, rowHeight);
        }
        ctx.fillStyle = '#ecf0f1';
        ctx.fillText(row.dx.toString(), x + 16, rowY);
        ctx.fillText(row.slope.toFixed(3), x + colWidth + 16, rowY);
      });
      ctx.restore();
    }

    function renderDualGraph(ctx, item, dims, elapsed) {
      const width = dims.width - dims.margin * 2;
      const height = dims.height * 0.45;
      const x = dims.margin;
      const y = dims.margin;
      const progress = (elapsed % 8) / 8;
      const s = (t) => 0.5 * t * t + 0.5 * t;
      const v = (t) => t + 0.5;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      ctx.strokeStyle = '#3498db';
      ctx.lineWidth = 3;
      ctx.beginPath();
      for (let i = 0; i <= 160; i += 1) {
        const t = i / 40;
        const px = x + (t / 4) * width;
        const py = y + height * 0.6 - s(t) * (height * 0.12);
        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
      ctx.strokeStyle = '#e74c3c';
      ctx.beginPath();
      for (let i = 0; i <= 160; i += 1) {
        const t = i / 40;
        const px = x + (t / 4) * width;
        const py = y + height * 0.9 - v(t) * (height * 0.25);
        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
      const markerX = x + progress * width;
      const time = progress * 4;
      const markerY1 = y + height * 0.6 - s(time) * (height * 0.12);
      const markerY2 = y + height * 0.9 - v(time) * (height * 0.25);
      ctx.fillStyle = '#f1c40f';
      ctx.beginPath();
      ctx.arc(markerX, markerY1, 6, 0, TWO_PI);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(markerX, markerY2, 6, 0, TWO_PI);
      ctx.fill();
      ctx.fillStyle = '#ecf0f1';
      ctx.font = '18px "Noto Serif SC", serif';
      ctx.fillText(`t=${time.toFixed(1)}s`, markerX + 12, y + height * 0.25);
      ctx.restore();
    }

    function renderCusp(ctx, item, dims, elapsed) {
      const width = dims.width - dims.margin * 2;
      const height = dims.height - dims.margin * 2;
      const x = dims.margin;
      const y = dims.margin;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      ctx.strokeStyle = '#ecf0f1';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x + width / 2, y + height * 0.2);
      ctx.lineTo(x + width * 0.2, y + height * 0.8);
      ctx.moveTo(x + width / 2, y + height * 0.2);
      ctx.lineTo(x + width * 0.8, y + height * 0.8);
      ctx.stroke();
      const pulse = Math.sin(elapsed * 3) * 6 + 18;
      ctx.strokeStyle = '#e74c3c';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(x + width / 2 - pulse, y + height * 0.2 - pulse);
      ctx.lineTo(x + width / 2 + pulse, y + height * 0.2 + pulse);
      ctx.moveTo(x + width / 2 + pulse, y + height * 0.2 - pulse);
      ctx.lineTo(x + width / 2 - pulse, y + height * 0.2 + pulse);
      ctx.stroke();
      ctx.restore();
    }

    function renderFlow(ctx, item, dims, elapsed) {
      const steps = Math.max(3, item.steps || 4);
      const width = dims.width - dims.margin * 2;
      const height = dims.height * 0.35;
      const x = dims.margin;
      const y = dims.margin;
      const spacing = width / steps;
      ctx.save();
      ctx.font = '18px "Noto Serif SC", serif';
      for (let i = 0; i < steps; i += 1) {
        const boxX = x + spacing * i + spacing * 0.1;
        const boxY = y + height * 0.25;
        const boxW = spacing * 0.8;
        const boxH = height * 0.5;
        const active = Math.floor(elapsed) % steps === i;
        ctx.fillStyle = active ? 'rgba(241, 196, 15, 0.4)' : 'rgba(0,0,0,0.35)';
        ctx.strokeStyle = 'rgba(255,255,255,0.25)';
        ctx.lineWidth = 2;
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.strokeRect(boxX, boxY, boxW, boxH);
        ctx.fillStyle = '#ecf0f1';
        ctx.fillText(`步骤 ${i + 1}`, boxX + boxW / 2 - 36, boxY + boxH / 2);
        if (i < steps - 1) {
          const arrowX = boxX + boxW;
          const arrowMid = boxY + boxH / 2;
          ctx.strokeStyle = '#f39c12';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(arrowX + 8, arrowMid);
          ctx.lineTo(arrowX + spacing * 0.2, arrowMid);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(arrowX + spacing * 0.2 - 10, arrowMid - 8);
          ctx.lineTo(arrowX + spacing * 0.2, arrowMid);
          ctx.lineTo(arrowX + spacing * 0.2 - 10, arrowMid + 8);
          ctx.fillStyle = '#f39c12';
          ctx.fill();
        }
      }
      ctx.restore();
    }

    function renderChecklist(ctx, item, dims, elapsed) {
      const count = Math.max(3, item.count || 3);
      const width = dims.width * 0.42;
      const x = dims.width - width - dims.margin;
      const y = dims.margin;
      const rowHeight = Math.min(48, (dims.height - y * 2) / count);
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.4)';
      ctx.fillRect(x, y, width, rowHeight * count + 24);
      ctx.font = '18px "Noto Serif SC", serif';
      for (let i = 0; i < count; i += 1) {
        const rowY = y + 12 + rowHeight * i;
        const checked = (elapsed * 0.7) % count > i - 0.5;
        ctx.strokeStyle = '#ecf0f1';
        ctx.lineWidth = 2;
        ctx.strokeRect(x + 16, rowY, 24, 24);
        if (checked) {
          ctx.strokeStyle = '#2ecc71';
          ctx.beginPath();
          ctx.moveTo(x + 20, rowY + 14);
          ctx.lineTo(x + 30, rowY + 22);
          ctx.lineTo(x + 40, rowY + 6);
          ctx.stroke();
        }
        ctx.fillStyle = '#ecf0f1';
        ctx.fillText(`任务 ${i + 1}`, x + 56, rowY + 20);
      }
      ctx.restore();
    }

    function renderExercise(ctx, item, dims, elapsed) {
      const width = dims.width * 0.48;
      const height = dims.height * 0.4;
      const x = dims.margin;
      const y = dims.height - height - dims.margin;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      const active = Math.floor(elapsed % 2);
      for (let i = 0; i < 2; i += 1) {
        const cardX = x + 20 + i * (width / 2);
        const cardY = y + 24;
        const cardW = width / 2 - 40;
        const cardH = height - 48;
        ctx.fillStyle = i === active ? 'rgba(241, 196, 15, 0.35)' : 'rgba(255,255,255,0.08)';
        ctx.strokeStyle = 'rgba(255,255,255,0.25)';
        ctx.lineWidth = 2;
        ctx.fillRect(cardX, cardY, cardW, cardH);
        ctx.strokeRect(cardX, cardY, cardW, cardH);
        ctx.fillStyle = '#ecf0f1';
        ctx.font = '20px "Noto Serif SC", serif';
        ctx.fillText(`练习 ${i + 1}`, cardX + cardW / 2 - 36, cardY + cardH / 2);
      }
      ctx.restore();
    }

    function renderCountdown(ctx, item, dims, elapsed, plan) {
      const seconds = item.seconds || Math.round((plan.duration || 5000) / 1000);
      const remaining = seconds - (elapsed % seconds);
      const radius = Math.min(dims.width, dims.height) * 0.14;
      ctx.save();
      ctx.translate(dims.centerX, dims.margin + radius + 12);
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.lineWidth = 8;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, TWO_PI);
      ctx.stroke();
      ctx.strokeStyle = '#f1c40f';
      ctx.beginPath();
      ctx.arc(0, 0, radius, -Math.PI / 2, -Math.PI / 2 + (elapsed % seconds) / seconds * TWO_PI);
      ctx.stroke();
      ctx.fillStyle = '#ecf0f1';
      ctx.font = `${Math.round(radius * 0.9)}px 'Noto Serif SC', serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(Math.ceil(remaining).toString(), 0, 0);
      ctx.restore();
    }

    function renderError(ctx, item, dims, elapsed) {
      const width = dims.width * 0.36;
      const height = dims.height * 0.25;
      const x = dims.width - width - dims.margin;
      const y = dims.height - height - dims.margin;
      const pulse = Math.sin(elapsed * 4) * 0.15 + 0.85;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.5)';
      ctx.fillRect(x, y, width, height);
      ctx.strokeStyle = '#e74c3c';
      ctx.lineWidth = 6 * pulse;
      ctx.beginPath();
      ctx.moveTo(x + width * 0.2, y + height * 0.2);
      ctx.lineTo(x + width * 0.8, y + height * 0.8);
      ctx.moveTo(x + width * 0.8, y + height * 0.2);
      ctx.lineTo(x + width * 0.2, y + height * 0.8);
      ctx.stroke();
      ctx.restore();
    }

    function renderArea(ctx, item, dims, elapsed) {
      const width = dims.width - dims.margin * 2;
      const height = dims.height * 0.42;
      const x = dims.margin;
      const y = dims.margin;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      ctx.strokeStyle = '#27ae60';
      ctx.lineWidth = 3;
      ctx.beginPath();
      const samples = 160;
      for (let i = 0; i <= samples; i += 1) {
        const t = (i / samples) * 4 - 2;
        const px = x + (t + 2) / 4 * width;
        const val = evaluateFunction(item.function || 'parabola', t);
        const py = y + height - (val / 4.5) * height;
        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
      const progress = (elapsed % 6) / 6;
      const upper = -2 + progress * 4;
      ctx.fillStyle = 'rgba(241, 196, 15, 0.35)';
      ctx.beginPath();
      ctx.moveTo(x, y + height);
      for (let i = 0; i <= 120; i += 1) {
        const t = -2 + (upper + 2) * (i / 120);
        const px = x + (t + 2) / 4 * width;
        const val = evaluateFunction(item.function || 'parabola', t);
        const py = y + height - (val / 4.5) * height;
        if (i === 0) {
          ctx.lineTo(px, y + height);
          ctx.lineTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.lineTo(x + (upper + 2) / 4 * width, y + height);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    function renderExtrema(ctx, item, dims, elapsed) {
      const width = dims.width - dims.margin * 2;
      const height = dims.height - dims.margin * 2;
      const x = dims.margin;
      const y = dims.margin;
      const anchor = Math.sin(elapsed * 0.5);
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      ctx.strokeStyle = '#9b59b6';
      ctx.lineWidth = 3;
      ctx.beginPath();
      for (let i = 0; i <= 160; i += 1) {
        const t = (i / 160) * 4 - 2;
        const px = x + (t + 2) / 4 * width;
        const val = evaluateFunction(item.function || 'cubic', t);
        const py = y + height - (val / 4.5) * height;
        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();
      const px = x + (anchor + 2) / 4 * width;
      const py = y + height - (evaluateFunction(item.function || 'cubic', anchor) / 4.5) * height;
      ctx.fillStyle = '#e74c3c';
      ctx.beginPath();
      ctx.arc(px, py, 8, 0, TWO_PI);
      ctx.fill();
      ctx.restore();
    }

    function renderSeries(ctx, item, dims, elapsed) {
      const width = dims.width - dims.margin * 2;
      const height = dims.height * 0.4;
      const x = dims.margin;
      const y = dims.height - height - dims.margin;
      const terms = 6;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      const active = Math.floor(elapsed % terms);
      for (let i = 0; i < terms; i += 1) {
        const barWidth = width / terms * 0.6;
        const barX = x + width / terms * i + width / terms * 0.2;
        const value = Math.exp(-i * 0.6);
        const barH = (height - 24) * value;
        ctx.fillStyle = i <= active ? 'rgba(46, 204, 113, 0.7)' : 'rgba(255,255,255,0.15)';
        ctx.fillRect(barX, y + height - barH - 12, barWidth, barH);
      }
      ctx.restore();
    }

    function renderVectorField(ctx, item, dims, elapsed) {
      const width = dims.width - dims.margin * 2;
      const height = dims.height * 0.45;
      const x = dims.margin;
      const y = dims.margin;
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillRect(x, y, width, height);
      const cols = 10;
      const rows = 6;
      for (let i = 0; i <= cols; i += 1) {
        for (let j = 0; j <= rows; j += 1) {
          const px = x + (i / cols) * width;
          const py = y + (j / rows) * height;
          const vx = Math.sin(px * 0.05 + elapsed * 0.6);
          const vy = Math.cos(py * 0.05 + elapsed * 0.6);
          ctx.strokeStyle = '#1abc9c';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(px, py);
          ctx.lineTo(px + vx * 14, py + vy * 14);
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    function renderConcept(ctx, item, dims, elapsed) {
      const count = item.count || 4;
      const radius = Math.min(dims.width, dims.height) * 0.32;
      ctx.save();
      ctx.translate(dims.centerX, dims.centerY);
      for (let i = 0; i < count; i += 1) {
        const angle = (i / count) * TWO_PI + elapsed * 0.5;
        const x = Math.cos(angle) * radius * 0.6;
        const y = Math.sin(angle) * radius * 0.4;
        ctx.fillStyle = `rgba(52, 152, 219, ${0.3 + 0.6 * (i / count)})`;
        ctx.beginPath();
        ctx.arc(x, y, 26, 0, TWO_PI);
        ctx.fill();
      }
      ctx.restore();
    }

    """


    function_snippets.append(common_helpers)

    for index, slide in enumerate(ordered_slides):
        lines = extract_animation_lines(slide.animation_html)
        plan = build_animation_plan(slide, lines)
        plan_json = json.dumps(plan, ensure_ascii=False)
        template = """
    let animationHandle__IDX__ = null;
    let resizeListener__IDX__ = null;
    let animationState__IDX__ = null;

    function startAnimation__IDX__(canvas) {
      if (!canvas) return;
      stopAnimation__IDX__();
      const plan = __PLAN__;
      const state = createCanvasState(canvas);
      state.resize();
      animationState__IDX__ = { state, plan, start: null };

      function drawFrame__IDX__(timestamp) {
        if (!animationState__IDX__) {
          return;
        }
        if (animationState__IDX__.start === null) {
          animationState__IDX__.start = timestamp;
        }
        const elapsed = (timestamp - animationState__IDX__.start) / 1000;
        const active = animationState__IDX__;
        renderPlan(active.state.ctx, active.plan, active.state, elapsed);
        animationHandle__IDX__ = requestAnimationFrame(drawFrame__IDX__);
      }

      animationHandle__IDX__ = requestAnimationFrame(drawFrame__IDX__);
      resizeListener__IDX__ = () => {
        if (!animationState__IDX__) {
          return;
        }
        animationState__IDX__.state.resize();
      };
      window.addEventListener('resize', resizeListener__IDX__);
    }

    function stopAnimation__IDX__() {
      if (animationHandle__IDX__ !== null) {
        cancelAnimationFrame(animationHandle__IDX__);
        animationHandle__IDX__ = null;
      }
      if (resizeListener__IDX__) {
        window.removeEventListener('resize', resizeListener__IDX__);
        resizeListener__IDX__ = null;
      }
      animationState__IDX__ = null;
    }
"""
        snippet = template.replace('__IDX__', str(index)).replace('__PLAN__', plan_json)
        function_snippets.append(snippet)

        start_cases.append(
            """
      {keyword} (index === {idx}) {{
        startAnimation{idx}(canvas);
        return;
      }}
""".format(keyword="if" if index == 0 else "else if", idx=index)
        )

        stop_cases.append(
            """
      {keyword} (index === {idx}) {{
        stopAnimation{idx}();
        return;
      }}
""".format(keyword="if" if index == 0 else "else if", idx=index)
        )

    if not ordered_slides:
        start_cases.append(
            """
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width || canvas.clientWidth || 0, canvas.height || canvas.clientHeight || 0);
      }
"""
        )
        stop_cases.append(
            """
      return;
"""
        )
    else:
        start_cases.append(
            """
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width || canvas.clientWidth || 0, canvas.height || canvas.clientHeight || 0);
      }
"""
        )
        stop_cases.append(
            """
      return;
"""
        )

    return ("".join(function_snippets), "".join(start_cases), "".join(stop_cases))


def serialise_slides(slides: List[Slide]) -> str:
    payload = [
        {
            "page": slide.page,
            "title": slide.title,
            "durationMs": slide.duration_ms,
            "boardHTML": slide.board_html,
            "animationHTML": slide.animation_html,
            "speak": slide.speak,
            "actions": slide.actions,
        }
        for slide in sorted(slides, key=lambda s: s.page)
    ]
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        json_text.replace("\\u003c", "<")
        .replace("\\u003e", ">")
        .replace("\\u0026", "&")
    )


HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>$title</title>
  <link rel="stylesheet" href="./noto-serif-sc.css" />
  <script src="./polyfill.min.js" defer></script>
  <script id="MathJax-script" async src="./mathjax-tex-mml-chtml.js"></script>
  <style>
    :root {
      --chalkboard-bg: #1a1a2e;
      --chalk-text: #e0e0e0;
      --highlight: #f1c40f;
      --accent: #f39c12;
      --danger: #e74c3c;
      --control-bg: rgba(0, 0, 0, 0.35);
      --control-text: #fefefe;
      --control-hover: rgba(255, 255, 255, 0.12);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body.blackboard {
      font-family: 'Noto Serif SC', serif;
      background: var(--chalkboard-bg);
      color: var(--chalk-text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    #statusIndicator {
      position: fixed;
      top: 12px;
      right: 16px;
      background: rgba(0, 0, 0, 0.45);
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 0.85rem;
      letter-spacing: 0.08em;
      z-index: 1000;
      transition: background 0.3s ease;
    }

    .avatar-container {
      position: fixed;
      top: 50%;
      left: 10%;
      width: 320px;
      height: 540px;
      transform: translateY(-50%);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
      pointer-events: none;
    }

    .avatar-container .wrapper {
      width: 100%;
      height: 100%;
      border-radius: 16px;
      overflow: hidden;
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(8px);
    }

    .slide-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 32px 48px 140px;
      position: relative;
      gap: 12px;
    }

    .slide {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: calc(100% - 8px);
      opacity: 0;
      visibility: hidden;
      transition: opacity 0.4s ease, visibility 0.4s ease;
      display: flex;
      align-items: stretch;
      justify-content: center;
      padding: 16px 20px;
    }

    .slide.active {
      opacity: 1;
      visibility: visible;
    }

    .slide-content {
      display: flex;
      flex: 1;
      gap: 24px;
      max-width: 1440px;
    }

    .blackboard-text {
      flex: 1 1 50%;
      background: rgba(255, 255, 255, 0.04);
      border-radius: 18px;
      padding: 24px 28px;
      box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.35);
      overflow-y: auto;
    }

    .blackboard-text h1,
    .blackboard-text h2 {
      color: var(--highlight);
      margin-bottom: 12px;
      text-shadow: 0 0 6px rgba(241, 196, 15, 0.45);
    }

    .blackboard-text ul {
      margin-left: 1.2rem;
      line-height: 1.7;
    }

    .blackboard-text li {
      margin-bottom: 0.45rem;
    }

    .animation-pane {
      flex: 1 1 50%;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 18px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      box-shadow: inset 0 0 16px rgba(0, 0, 0, 0.3);
    }

    .animation-pane h3 {
      color: var(--accent);
      margin-bottom: 16px;
      font-size: 1.15rem;
      letter-spacing: 0.08em;
    }

    .animation-canvas-wrapper {
      flex: 1;
      border-radius: 16px;
      border: 1px solid rgba(241, 196, 15, 0.35);
      background: radial-gradient(circle at top, rgba(46, 204, 113, 0.12), rgba(10, 24, 48, 0.65));
      position: relative;
      overflow: hidden;
      min-height: 260px;
    }

    .animation-canvas-wrapper canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    .animation-notes {
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 0.95rem;
      line-height: 1.6;
      color: rgba(255, 255, 255, 0.85);
      overflow-y: auto;
      max-height: 220px;
    }

    .animation-notes ul {
      margin-left: 1.15rem;
    }

    .animation-notes li {
      margin-bottom: 0.45rem;
    }

    .subtitle-area {
      position: fixed;
      bottom: 92px;
      left: 50%;
      transform: translateX(-50%);
      min-height: 64px;
      min-width: 60%;
      max-width: 80%;
      padding: 12px 24px;
      background: rgba(0, 0, 0, 0.55);
      border-radius: 12px;
      text-align: center;
      font-size: 1.05rem;
      letter-spacing: 0.05em;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 900;
    }

    .subtitle-area[aria-live="polite"] {
      outline: none;
    }

    .control-bar {
      position: fixed;
      bottom: 16px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--control-bg);
      padding: 16px 28px;
      border-radius: 999px;
      display: flex;
      gap: 12px;
      align-items: center;
      backdrop-filter: blur(8px);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
    }

    .control-bar button {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.35);
      color: var(--control-text);
      padding: 10px 18px;
      border-radius: 999px;
      font-size: 0.95rem;
      cursor: pointer;
      transition: background 0.2s ease, transform 0.2s ease;
    }

    .control-bar button:hover:not([disabled]) {
      background: var(--control-hover);
      transform: translateY(-1px);
    }

    .control-bar button[disabled] {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .meta-bar {
      position: fixed;
      top: 18px;
      left: 24px;
      max-width: 40%;
      background: rgba(0, 0, 0, 0.35);
      padding: 12px 16px;
      border-radius: 14px;
      line-height: 1.5;
      font-size: 0.95rem;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    }

    .meta-bar strong {
      color: var(--highlight);
    }

    @media (max-width: 1200px) {
      .slide-content {
        flex-direction: column;
      }

      .avatar-container {
        display: none;
      }
    }
  </style>
</head>
<body class="blackboard">
  <div id="statusIndicator" class="status-indicator">等待连接</div>
  <div class="meta-bar">
    <div><strong>$chapter</strong></div>
    <div>$title</div>
  </div>
  <div class="avatar-container"><div class="wrapper" id="avatarWrapper"></div></div>
  <div id="slide-container" class="slide-container"></div>
  <div class="subtitle-area" id="subtitleArea" aria-live="polite">欢迎来到本节课程</div>
  <div class="control-bar">
    <button id="prevBtn">上一页</button>
    <button id="restartBtn">重新开始</button>
    <button id="playBtn">开始讲解</button>
    <button id="autoBtn">自动播放</button>
    <button id="nextBtn">下一页</button>
  </div>

  <script type="module">
    import AvatarPlatform from './avatar-sdk-web_3.1.2.1002/index.js';

    const indicator = document.getElementById('statusIndicator');
    const avatarWrapper = document.getElementById('avatarWrapper');

    async function initAvatarPlatform() {
      if (!AvatarPlatform) {
        indicator.textContent = '虚拟人库缺失';
        indicator.style.background = 'rgba(231, 76, 60, 0.55)';
        return null;
      }

      indicator.textContent = '虚拟人连接中…';
      indicator.style.background = 'rgba(241, 196, 15, 0.35)';

      try {
        const platform = new AvatarPlatform();
        if (typeof platform.setApiInfo === 'function') {
          platform.setApiInfo({
            appId: '98c558c1',
            apiKey: '133adcc14bda6e315040f78700b38267',
            apiSecret: 'NjJmZmM5YTM2YzBhZTY3NzEzMGVmMDIy',
            sceneId: '216155854796361728',
            serverUrl: 'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact'
          });
        }

        if (typeof platform.setGlobalParams === 'function') {
          platform.setGlobalParams({
            stream: { protocol: 'xrtc', fps: 25, bitrate: 1000000 },
            avatar: { avatar_id: '110332017', width: 1920, height: 1080 },
            tts: { vcn: 'x4_yiting', speed: 50, pitch: 50, volume: 100 },
            avatar_dispatch: { interactive_mode: 1, content_analysis: 0 }
          });
        }

        if (typeof platform.createPlayer === 'function') {
          const maybePlayer = platform.createPlayer({
            container: avatarWrapper,
            domId: 'avatarWrapper',
            width: avatarWrapper?.clientWidth || 320,
            height: avatarWrapper?.clientHeight || 540
          });
          if (maybePlayer && typeof maybePlayer.then === 'function') {
            await maybePlayer;
          }
        }

        if (typeof platform.start === 'function') {
          try {
            const maybeStart = platform.start();
            if (maybeStart && typeof maybeStart.then === 'function') {
              await maybeStart;
            }
          } catch (startError) {
            console.warn('虚拟人启动失败', startError);
          }
        }

        window.avatarPlatform = platform;
        window.dispatchEvent(new CustomEvent('avatarReady'));
        indicator.textContent = '连接成功';
        indicator.style.background = 'rgba(46, 204, 113, 0.45)';
        return platform;
      } catch (error) {
        console.error('虚拟人 SDK 初始化失败', error);
        indicator.textContent = '虚拟人未连接';
        indicator.style.background = 'rgba(231, 76, 60, 0.55)';
        throw error;
      }
    }

    window.avatarReadyPromise = initAvatarPlatform();
  </script>

  <script>
    const videoMeta = $meta;
    const slidesSpec = $slides;

    window.avatarReadyPromise = window.avatarReadyPromise || Promise.resolve(null);

    const slideContainer = document.getElementById('slide-container');
    const subtitleArea = document.getElementById('subtitleArea');
    const statusIndicator = document.getElementById('statusIndicator');
    const autoBtn = document.getElementById('autoBtn');

    let currentIndex = -1;
    let autoPlaying = false;
    let autoPlayToken = 0;

    function buildSlides() {
      slideContainer.innerHTML = '';
      slidesSpec.forEach((slide, idx) => {
        const slideEl = document.createElement('div');
        slideEl.className = 'slide';

        const content = document.createElement('div');
        content.className = 'slide-content';

        const board = document.createElement('div');
        board.className = 'blackboard-text';
        const boardTitle = '<h2>第' + slide.page + '页 · ' + slide.title + '</h2>';
        board.innerHTML = boardTitle + (slide.boardHTML || '<p>本页暂无板书内容。</p>');

        const animationPane = document.createElement('div');
        animationPane.className = 'animation-pane';

        const animationTitle = document.createElement('h3');
        animationTitle.textContent = '动画演示';
        animationPane.appendChild(animationTitle);

        const canvasWrapper = document.createElement('div');
        canvasWrapper.className = 'animation-canvas-wrapper';

        const canvas = document.createElement('canvas');
        canvas.className = 'animationCanvas';
        canvas.dataset.slideIndex = String(idx);
        canvas.setAttribute('aria-label', '第' + slide.page + '页动画演示');
        canvasWrapper.appendChild(canvas);
        animationPane.appendChild(canvasWrapper);

        const notes = document.createElement('div');
        notes.className = 'animation-notes';
        notes.innerHTML = slide.animationHTML || '<p>参照蓝图补充动画。</p>';
        animationPane.appendChild(notes);

        content.appendChild(board);
        content.appendChild(animationPane);
        slideEl.appendChild(content);
        slideContainer.appendChild(slideEl);
      });
    }

    function getSlides() {
      return Array.from(document.querySelectorAll('.slide'));
    }

    function switchToSlide(index) {
      const slides = getSlides();
      if (index < 0 || index >= slides.length) {
        return;
      }

      const previous = currentIndex;
      if (previous !== -1) {
        const previousSlide = slides[previous];
        if (previousSlide) {
          previousSlide.classList.remove('active');
        }
        stopAnimationFor(previous);
      }

      const targetSlide = slides[index];
      if (targetSlide) {
        targetSlide.classList.add('active');
      }
      currentIndex = index;
      subtitleArea.textContent = slidesSpec[currentIndex]?.speak || '';
      startAnimationFor(currentIndex);
    }

    function wait(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    }

    async function ensureAvatarReady() {
      try {
        const platform = await window.avatarReadyPromise;
        return platform || null;
      } catch (error) {
        console.warn('虚拟人未就绪', error);
        return null;
      }
    }

    async function speakContent(slide) {
      if (!slide) {
        return;
      }
      subtitleArea.textContent = slide.speak || '';

      const platform = await ensureAvatarReady();
      if (!platform) {
        return;
      }

      try {
        if (Array.isArray(slide.actions)) {
          for (const action of slide.actions) {
            if (typeof platform.writeCmd === 'function') {
              try {
                const maybeAction = platform.writeCmd('action', action);
                if (maybeAction && typeof maybeAction.then === 'function') {
                  await maybeAction;
                }
              } catch (err) {
                console.warn('动作执行失败', action, err);
              }
            }
          }
        }

        if (slide.speak && typeof platform.writeText === 'function') {
          const textResult = platform.writeText(slide.speak, { nlp: false });
          if (textResult && typeof textResult.then === 'function') {
            await textResult;
          }
        }
      } catch (error) {
        console.warn('虚拟人交互失败', error);
        statusIndicator.textContent = '虚拟人未连接';
        statusIndicator.style.background = 'rgba(231, 76, 60, 0.55)';
      }
    }

    async function startAutoPlay() {
      if (autoPlaying) {
        return;
      }
      autoPlaying = true;
      autoPlayToken += 1;
      const token = autoPlayToken;
      setControlsDisabled(true);
      autoBtn.textContent = '停止自动播放';

      let startIndex = currentIndex;
      if (startIndex < 0) {
        startIndex = 0;
      }

      for (let i = startIndex; i < slidesSpec.length; i += 1) {
        if (!autoPlaying || token !== autoPlayToken) {
          break;
        }
        switchToSlide(i);
        await speakContent(slidesSpec[i]);
        const duration = slidesSpec[i]?.durationMs ?? 5000;
        const safeDuration = Number.isFinite(duration) ? duration : 5000;
        await wait(safeDuration);
      }

      if (token === autoPlayToken) {
        autoPlaying = false;
        setControlsDisabled(false);
        autoBtn.textContent = '自动播放';
      }
    }

    function stopAutoPlay() {
      if (!autoPlaying) {
        return;
      }
      autoPlaying = false;
      autoPlayToken += 1;
      setControlsDisabled(false);
      autoBtn.textContent = '自动播放';
    }

    function setControlsDisabled(disabled) {
      document.querySelectorAll('.control-bar button').forEach((btn) => {
        if (btn.id === 'autoBtn') {
          return;
        }
        btn.disabled = disabled;
      });
    }

    document.getElementById('prevBtn').addEventListener('click', () => {
      stopAutoPlay();
      const target = currentIndex <= 0 ? 0 : currentIndex - 1;
      switchToSlide(target);
    });

    document.getElementById('nextBtn').addEventListener('click', () => {
      stopAutoPlay();
      const target = currentIndex < slidesSpec.length - 1 ? currentIndex + 1 : slidesSpec.length - 1;
      switchToSlide(target);
    });

    document.getElementById('restartBtn').addEventListener('click', () => {
      stopAutoPlay();
      switchToSlide(0);
    });

    document.getElementById('playBtn').addEventListener('click', async () => {
      stopAutoPlay();
      if (currentIndex === -1) {
        switchToSlide(0);
      }
      await speakContent(slidesSpec[currentIndex]);
    });

    autoBtn.addEventListener('click', () => {
      if (autoPlaying) {
        stopAutoPlay();
      } else {
        startAutoPlay();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight' || event.key === ' ') {
        document.getElementById('nextBtn').click();
      } else if (event.key === 'ArrowLeft') {
        document.getElementById('prevBtn').click();
      } else if (event.key === 'Enter') {
        document.getElementById('playBtn').click();
      } else if (event.key === 'Escape') {
        stopAutoPlay();
      }
    });

    function startAnimationFor(index) {
      const selector = '.animationCanvas[data-slide-index="' + index + '"]';
      const canvas = document.querySelector(selector);
      if (!canvas) {
        return;
      }
$animation_start_cases
    }

    function stopAnimationFor(index) {
$animation_stop_cases
    }

$animation_functions

    buildSlides();
    switchToSlide(0);
  </script>
</body>
</html>
""")



def write_video_html(video: Video) -> None:
    slides_json = serialise_slides(video.slides)
    meta_json = json.dumps(
        {
            "identifier": video.identifier,
            "title": video.title,
            "chapterTitle": video.chapter_title,
        },
        ensure_ascii=False,
    )
    meta_json = (
        meta_json.replace("\\u003c", "<")
        .replace("\\u003e", ">")
        .replace("\\u0026", "&")
    )

    animation_functions, start_cases, stop_cases = build_animation_functions(video.slides)

    html = HTML_TEMPLATE.substitute(
        title=f"{video.identifier} {video.title}",
        chapter=video.chapter_title,
        meta=meta_json,
        slides=slides_json,
        animation_functions=animation_functions,
        animation_start_cases=start_cases,
        animation_stop_cases=stop_cases,
    )

    output_path = OUTPUT_DIR / video.output_name
    output_path.write_text(html, encoding="utf-8")


def main() -> None:
    if not BLUEPRINT_PATH.exists():
        raise FileNotFoundError(f"未找到蓝图文件: {BLUEPRINT_PATH}")

    videos = parse_blueprint(BLUEPRINT_PATH)
    if not videos:
        raise RuntimeError("未能解析到任何视频信息，请检查蓝图格式是否发生变化。")

    for video in videos:
        write_video_html(video)


if __name__ == "__main__":
    main()

