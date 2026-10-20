/* ============================================================
   quiz.js — Git 教学工作区通用互动练习组件
   来源：Japanese-Travel/assets/quiz.js
   所有 lessons/*.html 通过 <script src="../assets/quiz.js"></script> 引入。

   用法：
   1. 每题一个 .quiz 卡片（data-quiz 从 0 开始编号）：
      <div class="quiz" data-quiz="0">
        <h3>练习 1</h3>
        <p class="quiz-scene">场景描述……</p>
        <div class="quiz-options">
          <button data-choice="a">选项一</button>
          <button data-choice="b">选项二</button>
        </div>
        <p class="quiz-feedback"></p>
      </div>
   2. 页面底部定义每题配置（顺序对应题目编号），再初始化：
      var QUIZ_CONFIG = [
        { correct: "b", okMsg: "答对时的解释", errMsg: "答错时的解释" }
      ];
      initQuizzes(QUIZ_CONFIG, "score");   // 第二参数是计分元素 id，可省略
   ============================================================ */

function initQuizzes(config, scoreId) {
  var answered = {};   // 记录每题是否已作答（对象当字典用：键是题目编号）
  var score = 0;

  // 语法糖注释：forEach 是数组/节点列表自带的遍历方法，
  // 等价于 for (var i = 0; i < list.length; i++) { 对 list[i] 做…… }
  document.querySelectorAll(".quiz").forEach(function (quiz) {
    var quizId = Number(quiz.dataset.quiz);
    var buttons = quiz.querySelectorAll("button");
    var feedback = quiz.querySelector(".quiz-feedback");
    var answer = config[quizId];

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        if (answered[quizId]) return;      // 答过就锁题，不允许刷分
        answered[quizId] = true;

        var picked = button.dataset.choice;
        var isRight = (picked === answer.correct);

        // 判定后禁用全部按钮，高亮正误
        buttons.forEach(function (b) { b.disabled = true; });
        if (isRight) {
          button.classList.add("correct");
          score = score + 1;
        } else {
          button.classList.add("wrong");
          // 把正确选项也标出来，让学习者看到差距
          buttons.forEach(function (b) {
            if (b.dataset.choice === answer.correct) b.classList.add("correct");
          });
        }

        feedback.textContent = (isRight ? "✔ " : "✘ ") + (isRight ? answer.okMsg : answer.errMsg);
        feedback.classList.add(isRight ? "ok" : "err");

        if (scoreId) updateScore();
      });
    });
  });

  function updateScore() {
    var el = document.getElementById(scoreId);
    if (!el) return;
    var total = config.length;
    el.textContent = "本轮得分：" + score + " / " + total +
      (score === total ? " —— 全对。去沙箱里把这一步敲一遍。" : "");
  }
}
