// Run in the loaded stats page's browser context; no packages or recorded-data writes.
(() => {
  const assert = (ok, message) => { if (!ok) throw new Error(message); };
  const event = {kind:"llm", t:100, dur:10, model:'<img src=x onerror="alert(1)">',
    role:"code", provider:"consumer", tokens:12, priced:false, ok:true};
  const root = document.createElement("div");
  root.innerHTML = traceTimeline({start:100, dur:20, title:"x".repeat(150), l:[
    event, {...event, t:105}, {kind:"tool", t:119, dur:1, tool:"test", ok:false, error:"<script>bad()</script>"},
  ]});
  assert(!root.querySelector("img,script"), "Untrusted trace strings must remain text");
  assert(root.querySelector(".tl-input").textContent === "x".repeat(100) + "…", "Input preview must be truncated");
  const spans = root.querySelectorAll(".tl-model");
  assert(spans[0].style.width === "50%" && spans[1].style.width === "50%", "Bars must preserve recorded duration");
  assert(spans[1].style.left.includes("25%"), "Bars must preserve start offset");
  assert(spans[0].style.top !== spans[1].style.top, "Concurrent calls must occupy separate lanes");
  assert(root.querySelector(".tl-error").style.left.includes("100%"), "Failure must mark completion, not start");
  assert(spans[0].title.includes("Unpriced"), "Missing prices must not appear free");
  root.innerHTML = traceTimeline({start:100, dur:0, title:"", l:[{kind:"tool", t:100, dur:0, tool:"instant", ok:false}]});
  assert(!/NaN|Infinity/.test(root.innerHTML), "Instant-only runs must have finite geometry");
  assert(root.querySelector(".tl-error") && root.querySelector(".tl-tool"), "Instant failures must retain the tool and error marker");
  return "Timeline checks passed: escaping, preview, duration, offset, concurrency, failure endpoint, unpriced and instant spans";
})();
