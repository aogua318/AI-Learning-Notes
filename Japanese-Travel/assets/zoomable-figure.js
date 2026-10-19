/* ============================================================
   zoomable-figure.js — 可放大图表组件（Rust-Driver 教学工作区）
   用法：在课程 HTML 里放一个带 data-zoomable 属性的 figure：

     <figure class="figure-zoom" data-zoomable>
       <iframe src="../assets/xxx.html?embed=1" title="图注"></iframe>
       <!-- 或者 <img src="..."> / <svg>...</svg> -->
       <figcaption>图注文字</figcaption>
       <button class="zoom-badge" type="button">⤢ 点击放大</button>
     </figure>

   然后在 </body> 前引入：
     <script src="../assets/zoomable-figure.js"></script>

   行为：
   - 点徽章 / 点图表本体 → 图表变身为近全屏浮层；
   - 浮层内【滚轮】= 以当前光标位置为中心放大 / 缩小（1~8 倍）；
   - 放大后【按住拖拽】= 平移视图（触屏单指拖动同样有效）；
   - 再点徽章、按 Esc、或点浮层任意处（图注链接除外）→ 收起并复位。
   设计约束：不搬移任何已有 DOM 节点（iframe 场景会追加一个透明
   事件捕获层——浏览器不会把 iframe 内的滚轮冒泡到父页面），
   只切 class + 改写媒体元素的宽高与 left/top。
   为什么不用 transform: scale()：CSS transform 走合成器光栅化，
   放大看到的是按原尺寸光栅化的纹理，SVG 文字会糊；布局式缩放
   （改宽高）让浏览器按新尺寸重新矢量渲染，永远清晰。
   已知限制：双指捏合缩放未实现；浮层展开期间改变窗口大小后，
   缩放基准会失真，重新开关一次即可（教学场景足够）。
   ============================================================ */

(function () {
  "use strict";

  var MIN_ZOOM = 1;      // 1 倍 = 铺满浮层的适配态
  var MAX_ZOOM = 8;      // 最大放大倍率
  var WHEEL_BASE = 1.002; // 滚轮倍率基底：按 deltaY 像素数连续缩放
  var WHEEL_CLAMP = 1.5;  // 单次滚轮事件的倍率限幅，防触控板惯性跳变

  /* ---------- 纯函数：以光标为中心缩放一步 ----------
     输入当前状态 (z, tx, ty) 与光标在媒体本地坐标系的 (x, y)，
     输出新状态。数学原理（缩放作用于媒体元素自身的盒子，
     等效于以其左上角为原点）：内容点 c 在屏幕上的位置
     = 左上角平移量 t + c * z；要让光标下的内容点缩放后
     仍留在光标处，新平移 tx' = x - k * (x - tx)，
     其中 k = 新倍率 / 旧倍率。本函数不碰 DOM，可在 Node 里单测。 */
  function computeZoom(z, tx, ty, x, y, factor) {
    var newZ = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z * factor));
    var k = newZ / z;
    var backToBase = newZ <= MIN_ZOOM;
    return {
      z: newZ,
      // 缩回 1 倍时顺手把平移归零，保证“适配态”永远居中
      tx: backToBase ? 0 : x - k * (x - tx),
      ty: backToBase ? 0 : y - k * (y - ty)
    };
  }

  // 展开状态下锁住背景滚动，避免浮层后面页面跟着滚
  function lockScroll() {
    document.body.style.overflow = "hidden";
  }
  function unlockScroll() {
    document.body.style.overflow = "";
  }

  // 找到 figure 里的媒体元素（svg / img / iframe，取第一个）
  function getMedia(figure) {
    return figure.querySelector("svg, img, iframe");
  }

  // iframe 专用：展开时追加一个透明捕获层盖在 iframe 上，
  // 把滚轮 / 拖拽引到父页面（iframe 内的滚轮不会冒泡出来）。
  // 注意是 appendChild 追加，不是搬移已有节点。
  function ensureShield(figure) {
    var media = getMedia(figure);
    if (!media || media.tagName !== "IFRAME") { return null; }
    var shield = figure.querySelector(".zoom-shield");
    if (!shield) {
      shield = document.createElement("div");
      shield.className = "zoom-shield";
      figure.appendChild(shield);
    }
    return shield;
  }

  // 把当前缩放状态写成 宽高 + left/top（布局式缩放，见文件头说明）
  function applyZoom(figure) {
    var media = getMedia(figure);
    var s = figure.__zoom;
    var base = figure.__baseRect;
    if (!media || !s || !base) { return; }
    media.style.width = base.width * s.z + "px";
    media.style.height = base.height * s.z + "px";
    media.style.left = s.tx + "px";
    media.style.top = s.ty + "px";
  }

  // 展开：记录媒体元素的布局盒（适配态下的位置和尺寸），
  // 作为光标坐标换算与倍率缩放的基准
  function enterZoom(figure) {
    var media = getMedia(figure);
    figure.__zoom = { z: MIN_ZOOM, tx: 0, ty: 0 };
    if (media) {
      // 清掉上一次的宽高/位移，让 CSS 的 100% 适配态重新生效，
      // 再读取布局盒作为基准
      media.style.width = "";
      media.style.height = "";
      media.style.left = "";
      media.style.top = "";
      // 图片默认可拖拽会抢走我们的平移手势，关掉它
      if (media.tagName === "IMG") { media.draggable = false; }
      figure.__baseRect = media.getBoundingClientRect();
    }
    ensureShield(figure);
  }

  // 收起：清掉所有缩放样式与辅助节点，下次打开从头开始
  function exitZoom(figure) {
    var media = getMedia(figure);
    if (media) {
      media.style.width = "";
      media.style.height = "";
      media.style.left = "";
      media.style.top = "";
    }
    var shield = figure.querySelector(".zoom-shield");
    if (shield && shield.parentNode) {
      shield.parentNode.removeChild(shield);
    }
    figure.__zoom = null;
    figure.__baseRect = null;
    figure.__drag = null;
  }

  // 滚轮：以光标为中心缩放
  function onWheel(figure, event) {
    if (!figure.classList.contains("expanded")) { return; }
    var s = figure.__zoom;
    var rect = figure.__baseRect;
    if (!s || !rect) { return; }
    // preventDefault 阻止浮层内的滚动冒泡成页面滚动
    // （监听器必须以 { passive: false } 注册才能调它）
    event.preventDefault();
    var factor = Math.pow(WHEEL_BASE, -event.deltaY);
    factor = Math.max(1 / WHEEL_CLAMP, Math.min(WHEEL_CLAMP, factor));
    // 光标换算成媒体布局盒内的本地坐标
    var next = computeZoom(
      s.z, s.tx, s.ty,
      event.clientX - rect.left,
      event.clientY - rect.top,
      factor
    );
    figure.__zoom = next;
    applyZoom(figure);
  }

  // 拖拽平移（只有放大后有内容可移；徽章和图注区域不参与）
  function onPointerDown(figure, event) {
    var s = figure.__zoom;
    if (!s || s.z <= MIN_ZOOM) { return; }
    var t = event.target;
    if (t.closest && t.closest(".zoom-badge, figcaption")) { return; }
    // preventDefault 抑制图片的原生拖拽和文本选中
    event.preventDefault();
    figure.__drag = {
      x: event.clientX, y: event.clientY,
      tx: s.tx, ty: s.ty, moved: false
    };
    figure.classList.add("dragging");
    // setPointerCapture 把后续 move/up 都收到 figure 上，
    // 光标移出浮层也不会断掉平移
    if (figure.setPointerCapture) {
      figure.setPointerCapture(event.pointerId);
    }
  }
  function onPointerMove(figure, event) {
    var d = figure.__drag;
    if (!d) { return; }
    var dx = event.clientX - d.x;
    var dy = event.clientY - d.y;
    if (!d.moved && Math.abs(dx) + Math.abs(dy) > 4) { d.moved = true; }
    var s = figure.__zoom;
    s.tx = d.tx + dx;
    s.ty = d.ty + dy;
    applyZoom(figure);
  }
  function onPointerUp(figure) {
    figure.__drag = null;
    figure.classList.remove("dragging");
  }

  // 切换某个 figure 的放大/收起状态
  function toggleZoom(figure) {
    var badge = figure.querySelector(".zoom-badge");
    var willExpand = !figure.classList.contains("expanded");

    // 语法糖注释：classList.toggle(class, force) 第二个参数为 true/false
    // 时分别是“强制添加/移除”，等价于手写 if 判断再 add/remove。
    figure.classList.toggle("expanded", willExpand);
    if (willExpand) { enterZoom(figure); } else { exitZoom(figure); }

    if (badge) {
      badge.textContent = willExpand ? "✕ 收起（Esc）" : "⤢ 点击放大";
      // setAttribute 给按钮加无障碍标签，屏幕阅读器能读出当前状态
      badge.setAttribute("aria-expanded", willExpand ? "true" : "false");
    }
    if (willExpand) { lockScroll(); } else { unlockScroll(); }
  }

  // 文档级初始化：给所有 [data-zoomable] 绑事件
  function init() {
    // querySelectorAll 返回所有匹配元素的列表；forEach 遍历它
    // （语法糖注释：等价于原始 for (var i = 0; i < list.length; i++) 循环）。
    document.querySelectorAll("[data-zoomable]").forEach(function (figure) {
      var badge = figure.querySelector(".zoom-badge");

      // 点徽章：放大 / 收起
      if (badge) {
        badge.addEventListener("click", function (event) {
          // stopPropagation 阻止事件冒泡到 figure，
          // 否则点徽章会同时触发下面 figure 的点击逻辑，行为打架
          event.stopPropagation();
          toggleZoom(figure);
        });
      }

      // 点图表本体 → 放大；浮层内点任意处（图注链接除外）→ 收起。
      // svg/img 的事件会冒泡到 figure；iframe 由捕获层负责送到这。
      figure.addEventListener("click", function (event) {
        // 刚完成拖拽平移的那次点击要吞掉，否则松手瞬间就把浮层关了
        if (figure.__dragged) { figure.__dragged = false; return; }
        var t = event.target;
        if (t.closest && t.closest(".zoom-badge")) { return; }
        if (t.closest && t.closest("figcaption a")) { return; }
        toggleZoom(figure);
      });

      // 滚轮缩放：{ passive: false } 才能 preventDefault
      figure.addEventListener("wheel", function (event) {
        onWheel(figure, event);
      }, { passive: false });

      // 拖拽平移（Pointer Events 一套覆盖鼠标 / 触摸 / 触控笔）
      figure.addEventListener("pointerdown", function (event) {
        onPointerDown(figure, event);
      });
      figure.addEventListener("pointermove", function (event) {
        onPointerMove(figure, event);
        // 拖拽过的痕迹交给 click 处理器消费后清零
        if (figure.__drag && figure.__drag.moved) {
          figure.__dragged = true;
        }
      });
      figure.addEventListener("pointerup", function () {
        onPointerUp(figure);
      });
      figure.addEventListener("pointercancel", function () {
        onPointerUp(figure);
      });
    });

    // Esc 键收起所有展开的图表（键盘无障碍）
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        document.querySelectorAll("[data-zoomable].expanded").forEach(function (figure) {
          toggleZoom(figure);
        });
      }
    });
  }

  // DOMContentLoaded 事件：等 HTML 解析完再执行，
  // 保证 figure 元素都已存在（等价于把 <script> 放到 </body> 前）
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  }

  // Node 环境导出纯函数供单测；浏览器里没有 module，自动跳过
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { computeZoom: computeZoom };
  }
})();
