/* ============================================================
   diagram-tabs.js — Git 教学工作区通用图表切换组件
   所有 lessons/ 与 reference/ 页面通过 <script src="../assets/diagram-tabs.js"></script> 引入。

   用法：
   <div class="diagram-tabs" data-tabs data-initial="0">
     <div class="tab-bar">
       <button class="tab-btn" data-tab="0">初始</button>
       <button class="tab-btn" data-tab="1">建分支</button>
     </div>
     <div class="tab-panel" data-panel="0" data-status="main 指向 c3，HEAD 指向 main。">
       …完整 SVG…
     </div>
     <div class="tab-panel" data-panel="1" data-status="feature 与 main 同时指向 c3，HEAD 改指 feature。">
       …完整 SVG…
     </div>
     <p class="tab-status" data-tab-status></p>
   </div>

   面板是预绘的 SVG，切换只切 hidden；data-status 的文案会写进底部状态栏。
   这样既保留了 SVG 的可放大能力，又不需要在浏览器里做坐标计算。
   ============================================================ */

(function () {
  function init(root) {
    var buttons = Array.prototype.slice.call(root.querySelectorAll("[data-tab]"));
    var panels = Array.prototype.slice.call(root.querySelectorAll("[data-panel]"));
    var status = root.querySelector("[data-tab-status]");
    if (!buttons.length || !panels.length) return;

    function panelById(id) {
      for (var i = 0; i < panels.length; i++) {
        if (panels[i].getAttribute("data-panel") === id) return panels[i];
      }
      return null;
    }

    function show(id) {
      buttons.forEach(function (button) {
        var active = button.getAttribute("data-tab") === id;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach(function (panel) {
        panel.hidden = panel.getAttribute("data-panel") !== id;
      });
      if (status) {
        var current = panelById(id);
        status.innerHTML = current ? (current.getAttribute("data-status") || "") : "";
      }
    }

    buttons.forEach(function (button) {
      button.setAttribute("role", "tab");
      button.addEventListener("click", function () {
        show(button.getAttribute("data-tab"));
      });
    });
    panels.forEach(function (panel) {
      panel.setAttribute("role", "tabpanel");
    });

    var initial = root.getAttribute("data-initial") || buttons[0].getAttribute("data-tab");
    show(initial);
  }

  document.querySelectorAll("[data-tabs]").forEach(init);
})();
