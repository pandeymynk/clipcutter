// ClipCutter site: nav, scroll reveals, rotating words, demo tabs, typing terminal, count-ups, captions demo.
(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // nav: background after scroll, mobile menu
  const nav = $(".nav");
  const onScroll = () => nav && nav.classList.toggle("scrolled", scrollY > 10);
  addEventListener("scroll", onScroll, { passive: true }); onScroll();
  $(".burger")?.addEventListener("click", () => nav.classList.toggle("open"));
  $$(".menu a").forEach(a => a.addEventListener("click", () => nav.classList.remove("open")));

  // reveal on scroll
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { threshold: 0.15, rootMargin: "0px 0px -40px" });
  $$(".rv, .window").forEach(el => io.observe(el));

  // rotating headline words
  $$(".rot").forEach(r => {
    const w = $$("span", r); let i = 0;
    w[0].classList.add("on");
    if (calm || w.length < 2) return;
    setInterval(() => {
      w[i].classList.remove("on"); w[i].classList.add("out");
      const prev = i; setTimeout(() => w[prev].classList.remove("out"), 650);
      i = (i + 1) % w.length; w[i].classList.add("on");
    }, 2200);
  });

  // autoplay videos only while visible (saves data on phones)
  const vio = new IntersectionObserver(es => es.forEach(e => {
    const v = e.target;
    if (e.isIntersecting) { v.play().catch(() => {}); } else { v.pause(); }
  }), { threshold: 0.25 });
  $$("video[data-auto]").forEach(v => vio.observe(v));

  // demo tabs: each tab plays its own recording, progress bar follows the video
  const tabs = $$(".tab"), screen = $(".screen video"), label = $(".screen .label");
  if (tabs.length && screen) {
    let cur = 0, manual = false;
    const show = i => {
      cur = i;
      tabs.forEach((t, k) => { t.classList.toggle("on", k === i); $(".prog", t).style.width = "0"; });
      screen.style.opacity = 0;
      setTimeout(() => {
        screen.src = tabs[i].dataset.src; screen.poster = tabs[i].dataset.poster || "";
        if (label) label.textContent = tabs[i].dataset.label || "Real screen recording";
        screen.play().catch(() => {}); screen.style.opacity = 1;
      }, 250);
    };
    tabs.forEach((t, k) => t.addEventListener("click", () => { manual = true; show(k); }));
    screen.addEventListener("timeupdate", () => {
      if (screen.duration) $(".prog", tabs[cur]).style.width = (100 * screen.currentTime / screen.duration) + "%";
    });
    screen.addEventListener("ended", () => show((cur + 1) % tabs.length));
    show(0);
  }

  // typing terminal (the "free GitHub repo" pain)
  $$("[data-type]").forEach(el => {
    const lines = JSON.parse(el.dataset.type); let started = false;
    const run = async () => {
      if (started) return; started = true;
      el.innerHTML = "";
      for (const [cls, text] of lines) {
        const row = document.createElement("div"); row.className = cls; el.appendChild(row);
        for (const ch of text) { row.textContent += ch; if (!calm) await new Promise(r => setTimeout(r, cls === "cmd" ? 28 : 9)); }
        if (!calm) await new Promise(r => setTimeout(r, 260));
      }
      const c = document.createElement("span"); c.className = "cur"; el.appendChild(c);
    };
    new IntersectionObserver((es, o) => es.forEach(e => { if (e.isIntersecting) { run(); o.disconnect(); } }), { threshold: .4 }).observe(el);
  });

  // count-up numbers
  $$("[data-count]").forEach(el => {
    const end = parseFloat(el.dataset.count), pre = el.dataset.pre || "", suf = el.dataset.suf || "";
    new IntersectionObserver((es, o) => es.forEach(e => {
      if (!e.isIntersecting) return; o.disconnect();
      const t0 = performance.now(), d = calm ? 1 : 1400;
      const step = t => { const k = Math.min(1, (t - t0) / d), v = end * (1 - Math.pow(1 - k, 3));
        el.textContent = pre + (Number.isInteger(end) ? Math.round(v) : v.toFixed(1)) + suf; if (k < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    }), { threshold: .5 }).observe(el);
  });

  // word-by-word caption demo
  $$(".capdemo").forEach(el => {
    const ws = $$("span", el); let i = 0;
    if (calm) return;
    setInterval(() => { ws.forEach(w => w.classList.remove("on")); ws[i].classList.add("on"); i = (i + 1) % ws.length; }, 420);
  });

  // cursor glow on feature cards
  $$(".feat").forEach(c => c.addEventListener("pointermove", e => {
    const r = c.getBoundingClientRect(); c.style.setProperty("--mx", (e.clientX - r.left) + "px"); c.style.setProperty("--my", (e.clientY - r.top) + "px");
  }));

  // reel sound toggle
  $$(".snd").forEach(b => b.addEventListener("click", () => {
    const v = b.parentElement.querySelector("video"); v.muted = !v.muted; if (!v.muted) v.play();
    b.innerHTML = v.muted ? b.dataset.off : b.dataset.on;
  }));

  // highlight the visitor's platform on download cards
  const ua = navigator.userAgent;
  const os = /Android/i.test(ua) ? "android" : /Mac/i.test(ua) ? "mac" : /Win/i.test(ua) ? "win" : "";
  if (os) $$(`.plat[data-os="${os}"]`).forEach(p => p.classList.add("you"));
  $$("[data-year]").forEach(e => e.textContent = new Date().getFullYear());
})();
