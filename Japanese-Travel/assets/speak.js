/* ============================================================
   speak.js — 日语发音按钮组件（基于浏览器 Web Speech API）
   所有 lessons/*.html 通过 <script src="../assets/speak.js"></script> 引入。

   用法：<button class="speak" data-say="すみません">▶ 听发音</button>
   浏览器需装有日语语音（Windows：设置 → 时间和语言 → 语音 → 添加日语 ja-JP）；
   没有日语语音时按钮会给出提示，不影响页面其他功能。
   ============================================================ */

(function () {
  // 部分浏览器的语音列表是异步加载的：getVoices() 一开始可能返回空数组，
  // 要等 voiceschanged 事件触发后才拿得到。首次点击时若为空，会重试一次。
  var retried = false;

  function pickJapaneseVoice() {
    if (!("speechSynthesis" in window)) return null;
    var voices = speechSynthesis.getVoices();
    for (var i = 0; i < voices.length; i++) {
      // lang 形如 "ja-JP"；indexOf("ja") === 0 表示以 ja 开头
      if (voices[i].lang && voices[i].lang.indexOf("ja") === 0) return voices[i];
    }
    return null;
  }

  document.querySelectorAll(".speak").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.dataset.say;

      if (!("speechSynthesis" in window)) {
        btn.textContent = "浏览器不支持语音合成，请跟读参考表";
        return;
      }

      var voice = pickJapaneseVoice();
      if (!voice && !retried) {
        // 语音列表可能还没加载完，250ms 后重试一次再下结论
        retried = true;
        setTimeout(function () { btn.click(); }, 250);
        return;
      }
      if (!voice) {
        btn.textContent = "无日语语音包，请照读音跟读";
        // 语法糖注释：setTimeout 是延时执行，等价于"等 1500 毫秒后再做这件事"
        setTimeout(function () { btn.textContent = "▶ 听发音"; }, 1500);
        return;
      }

      var utter = new SpeechSynthesisUtterance(text);
      utter.lang = "ja-JP";
      utter.rate = 0.8;            // 放慢 20%，方便跟读
      utter.voice = voice;
      speechSynthesis.cancel();     // 打断上一句，避免排队
      speechSynthesis.speak(utter);

      btn.classList.add("playing");
      utter.onend = function () { btn.classList.remove("playing"); };
    });
  });
})();
