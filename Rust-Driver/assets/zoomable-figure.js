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

   行为：点徽章 / 点图表本体 → 图表变身为近全屏浮层；
   再点徽章、按 Esc、或点浮层空白背景 → 收起。
   设计约束：不克隆、不搬移任何 DOM 节点，只切 class，
   所以 SVG 内部 id、iframe 状态都不会丢。
   ============================================================ */

(function () {
  "use strict";

  // 语法糖注释：const 表示常量绑定；let 表示可变绑定（ES6 写法，
  // 原始等价形式分别是 var，但 const/let 有块级作用域，更安全）。

  // 展开状态下锁住背景滚动，避免浮层后面页面跟着滚
  function lockScroll() {
    document.body.style.overflow = "hidden";
  }
  function unlockScroll() {
    document.body.style.overflow = "";
  }

  // 切换某个 figure 的放大/收起状态
  function toggleZoom(figure) {
    var badge = figure.querySelector(".zoom-badge");
    var willExpand = !figure.classList.contains("expanded");

    // 语法糖注释：classList.contains/add/remove 是元素类名集合的操作方法，
    // 等价于原始的 element.className 字符串拼接判断，但不会误伤其他类名。
    figure.classList.toggle("expanded", willExpand);

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

      // 点图表本体区域也放大（iframe 内容里的点击不会冒泡出来，
      // 所以只有点到 figure 自己的空白/图注区域才会到这）
      figure.addEventListener("click", function (event) {
        // event.target 是真正被点的元素；只有点到 figure 自身
        // （即浮层展开后的深色背景）才收起，点到图注不收起
        if (event.target === figure) {
          toggleZoom(figure);
        }
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
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
