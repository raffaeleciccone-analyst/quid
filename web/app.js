// QUID: la pagina. I testi vengono da testi.json (IT/EN), le frasi delle risposte le scrive il server.
// Tutto quello che arriva dal file o dal server entra come testo (textContent), mai come HTML.
(function () {
  "use strict";
  var T = {}, lingua = "it", tipoFile = null, modo = { esce: true };
  var salvata = null;
  try { salvata = localStorage.getItem("quid-lingua"); } catch (e) { /* senza memoria: si usa la lingua del browser */ }
  lingua = salvata || ((navigator.language || "it").slice(0, 2) === "en" ? "en" : "it");

  function t(k, v) {
    var s = (T[k] || {})[lingua] || k;
    return s.replace(/\{(\w+)\}/g, function (_, n) { return v && n in v ? v[n] : "{" + n + "}"; });
  }
  function el(tag, attr, figli) {
    var e = document.createElement(tag);
    Object.keys(attr || {}).forEach(function (k) { if (k === "testo") e.textContent = attr[k]; else e.setAttribute(k, attr[k]); });
    (figli || []).forEach(function (f) { if (f) e.appendChild(typeof f === "string" ? document.createTextNode(f) : f); });
    return e;
  }
  function $(id) { return document.getElementById(id); }
  function euro(x) {
    var s = Math.abs(x).toLocaleString(lingua === "it" ? "it-IT" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return lingua === "it" ? s + " €" : "€" + s;
  }
  var MESI = { it: ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"],
               en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] };
  function mese(m, conAnno) { var p = String(m).split("-"); return p.length === 2 ? MESI[lingua][+p[1] - 1] + (conAnno ? " " + p[0] : "") : m; }
  function data(d) { var p = String(d).split("-"); return p.length === 3 ? p[2] + "/" + p[1] + "/" + p[0] : d; }
  function post(url, corpo) {
    var opz = { method: "POST", credentials: "same-origin" };
    if (corpo instanceof FormData) opz.body = corpo;
    else { opz.headers = { "content-type": "application/json" }; opz.body = JSON.stringify(corpo || {}); }
    return fetch(url, opz).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); });
  }

  // ---- lingua e testi fissi ----
  function traduci() {
    document.documentElement.lang = lingua;
    document.querySelectorAll("[data-t]").forEach(function (e) { e.textContent = t(e.dataset.t); });
    document.querySelectorAll("[data-lingua]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.lingua === lingua); });
    $("domanda").placeholder = t("segnaposto");
    $("modo").textContent = t(modo.esce ? "modo_online" : "modo_pc");
    esempi();
  }
  function esempi() {
    var box = $("esempi"); box.innerHTML = "";
    if (!tipoFile || tipoFile === "altro") return;
    [1, 2, 3].forEach(function (i) {
      var testo = t("es_" + tipoFile + "_" + i);
      var b = el("button", { type: "button", testo: testo });
      b.addEventListener("click", function () { chiedi(testo); });
      box.appendChild(b);
    });
  }

  // ---- il file ----
  function carica(file, nome) {
    var fd = new FormData(); fd.append("file", file, nome);
    $("errore-file").hidden = true;
    $("carica").querySelector("h1").textContent = t("attendi");
    post("/api/file", fd).then(function (r) {
      $("carica").querySelector("h1").textContent = t("carica_titolo");
      if (!r.ok) return erroreFile(r.j);
      tipoFile = r.j.tipo;
      schedaFile(r.j);
      $("carica").hidden = true; $("barra").hidden = false; $("risposte").innerHTML = "";
      esempi(); $("domanda").focus();
    }).catch(function () { erroreFile({ errore: "rete" }); });
  }
  function erroreFile(j) {
    var d = j.dettagli || {}, v = {};
    Object.keys(d).forEach(function (k) { v[k] = typeof d[k] === "number" ? euro(d[k]) : d[k]; });
    $("errore-file").textContent = t("e_" + j.errore, v);
    $("errore-file").hidden = false;
    $("carica").hidden = false; $("scheda-file").hidden = true; $("barra").hidden = true;
  }
  function schedaFile(f) {
    var box = $("scheda-file"); box.innerHTML = ""; box.hidden = false;
    var cambia = el("button", { type: "button", "class": "cambia", testo: t("cambia_file") });
    cambia.addEventListener("click", function () { $("carica").hidden = false; box.hidden = true; $("barra").hidden = true; });
    box.appendChild(el("div", { "class": "riga1" }, [el("span", { "class": "doc", testo: f.nome }),
      el("span", { "class": "tipo", testo: t("tipo_" + f.tipo, { n: f.righe }) }), cambia]));
    if (f.sistemato.length) {
      box.appendChild(el("p", { "class": "nota", testo: t("sistemato", { cose: f.sistemato.map(function (s) { return t("s_" + s.chiave, { n: s.n }); }).join(", ") }) }));
    }
    if (f.saldi) box.appendChild(el("p", { "class": "nota", testo: t("saldi_ok", { a: euro(f.saldi[0]), b: euro(f.saldi[1]) }) }));
    if (modo.esce) {
      var lista = el("ul", {}, f.anteprima.testi.map(function (x) { return el("li", {}, [el("code", { testo: x })]); }));
      box.appendChild(el("details", { "class": "esce" }, [el("summary", { testo: t("esce_online", { n: f.anteprima.testi.length }) }), lista]));
    } else {
      box.appendChild(el("p", { "class": "nota", testo: t("esce_pc") }));
    }
  }

  // ---- domande e risposte ----
  function chiedi(testo) {
    testo = (testo || "").trim(); if (!testo) return;
    $("domanda").value = "";
    var box = nuovaRisposta(testo);
    post("/api/domanda", { testo: testo, lingua: lingua }).then(function (r) { mostra(box, r); })
      .catch(function () { mostra(box, { ok: false, j: { errore: "rete" } }); });
  }
  function nuovaRisposta(titolo) {
    var box = el("div", { "class": "risposta" }, [el("p", { "class": "pensa", testo: t("pensa") })]);
    var q = el("div", { "class": "q" }, [el("p", { "class": "domanda", testo: titolo }), box]);
    $("risposte").appendChild(q);
    q.scrollIntoView({ behavior: "smooth", block: "start" });
    return box;
  }
  function mostra(box, r) {
    box.innerHTML = "";
    if (!r.ok) { box.className = "risposta no"; box.appendChild(el("p", { "class": "frase", testo: t("e_" + r.j.errore) })); return; }
    var x = r.j;
    box.className = "risposta" + (x.numero === null || x.numero === undefined ? " no" : "");
    if (x.ho_capito) box.appendChild(el("p", { "class": "capito" }, [t("ho_capito") + " ", el("b", { testo: x.ho_capito })]));
    box.appendChild(frase(x));
    if (x.domanda_indietro) return scelte(box, x.domanda_indietro);
    if (x.grafico) box.appendChild(grafico(x));
    if (x.righe && x.righe.length && x.grafico) {
      box.appendChild(el("details", { "class": "come" }, [el("summary", { testo: t("mostra_righe", { n: x.righe.length }) }), tabella(x)]));
    } else if (x.righe && x.righe.length) box.appendChild(tabella(x));
    if (x.righe && x.righe.length && !x.grafico && x.numero !== null && sommaRighe(x) !== null) box.appendChild(el("span", { "class": "torna", testo: t("torna") }));
    if (x.incerte && x.incerte.length) {
      box.appendChild(el("div", { "class": "incerte" }, [el("b", { testo: t("incerte") + " " }),
        x.incerte.map(function (r) { return data(r.data) + " " + r.descrizione + " " + euro(r.importo); }).join(" · ")]));
    }
    if (x.come) {
      box.appendChild(el("details", { "class": "come" }, [el("summary", { testo: t("come") }),
        el("p", { testo: x.come.parole }), el("code", { testo: x.come.pandas })]));
    }
  }
  function frase(x) {
    // il numero in verde: il server dice esattamente come è scritto nella frase ("187,40 €"), non si indovina
    var p = el("p", { "class": "frase" }), f = x.frase, n = x.numero_testo, i = n ? f.indexOf(n) : -1;
    if (i >= 0) {
      p.appendChild(document.createTextNode(f.slice(0, i)));
      p.appendChild(el("strong", { testo: n }));
      p.appendChild(document.createTextNode(f.slice(i + n.length)));
    } else p.textContent = f;
    return p;
  }
  function scelte(box, q) {
    var riga = el("div", { "class": "scelte" });
    q.anni.slice().reverse().forEach(function (a) {
      var b = el("button", { type: "button", testo: String(a) });
      b.addEventListener("click", function () {
        var nuovo = nuovaRisposta(String(a));
        post("/api/anno", { anno: a, lingua: lingua }).then(function (r) { mostra(nuovo, r); });
      });
      riga.appendChild(b);
    });
    box.appendChild(riga);
  }
  var SOLDI = { importo: 1, prezzo: 1 };
  function sommaRighe(x) { return x.righe[0] && "importo" in x.righe[0] ? x.righe.reduce(function (s, r) { return s + (r.importo || 0); }, 0) : null; }
  function tabella(x) {
    var cols = Object.keys(x.righe[0]), max = 50;
    var corpo = x.righe.slice(0, max).map(function (r) {
      return el("tr", {}, cols.map(function (c) {
        var v = r[c], num = typeof v === "number";
        return el("td", { "class": num ? "n" : "", testo: c === "data" ? data(v) : c === "mese" ? mese(v, true) : num ? (SOLDI[c] ? euro(v) : v.toLocaleString(lingua === "it" ? "it-IT" : "en-GB")) : v });
      }));
    });
    var figli = [el("thead", {}, [el("tr", {}, cols.map(function (c) { return el("th", { "class": typeof x.righe[0][c] === "number" ? "n" : "", testo: c }); }))]), el("tbody", {}, corpo)];
    var tot = sommaRighe(x);
    if (tot !== null && !x.grafico) {
      figli.push(el("tfoot", {}, [el("tr", {}, cols.map(function (c, i) { return el("td", { "class": c === "importo" ? "n" : "", testo: c === "importo" ? euro(tot) : i === cols.length - 2 ? t("totale_righe") : "" }); }))]));
    }
    var box = el("div", { "class": "tabella" }, [el("table", {}, figli)]);
    if (x.righe.length > max) box.appendChild(el("p", { "class": "nota", testo: t("altre_righe", { n: x.righe.length - max }) }));
    return box;
  }
  function grafico(x) {
    var ns = "http://www.w3.org/2000/svg", chiave = Object.keys(x.righe[0])[0], misura = Object.keys(x.righe[0])[1];
    var v = x.righe.map(function (r) { return Math.abs(r[misura]); }), mx = Math.max.apply(null, v.concat([1])) * 1.15;
    var W = 700, H = 180, n = v.length, xpos = function (i) { return 40 + i * (W - 60) / Math.max(1, n - 1); }, y = function (a) { return H - 26 - (H - 44) * a / mx; };
    var s = document.createElementNS(ns, "svg");
    s.setAttribute("viewBox", "0 0 " + W + " " + H); s.setAttribute("class", "grafico"); s.setAttribute("preserveAspectRatio", "none");
    s.setAttribute("role", "img"); s.setAttribute("aria-label", x.frase);
    function f(tag, a, testo) { var e = document.createElementNS(ns, tag); Object.keys(a).forEach(function (k) { e.setAttribute(k, a[k]); }); if (testo) e.textContent = testo; s.appendChild(e); }
    f("line", { "class": "ax", x1: 30, x2: W - 10, y1: H - 26, y2: H - 26 });
    if (x.grafico === "linea") {
      f("polyline", { "class": "l", points: v.map(function (a, i) { return xpos(i) + "," + y(a); }).join(" ") });
      v.forEach(function (a, i) { f("circle", { "class": "p", cx: xpos(i), cy: y(a), r: 3.5 }); });
    } else {
      var w = (W - 60) / n * 0.6;
      v.forEach(function (a, i) { var cx = 40 + (i + 0.5) * (W - 60) / n; f("rect", { "class": "b", x: cx - w / 2, y: y(a), width: w, height: H - 26 - y(a), rx: 3 }); });
    }
    var passo = Math.ceil(n / 8);
    x.righe.forEach(function (r, i) {
      if (i % passo) return;
      var cx = x.grafico === "linea" ? xpos(i) : 40 + (i + 0.5) * (W - 60) / n;
      f("text", { x: cx, y: H - 8, "text-anchor": "middle" }, chiave === "mese" ? mese(r[chiave]) : String(r[chiave]).slice(0, 12));
    });
    return s;
  }

  // ---- avvio ----
  document.querySelectorAll("[data-lingua]").forEach(function (b) {
    b.addEventListener("click", function () { lingua = b.dataset.lingua; try { localStorage.setItem("quid-lingua", lingua); } catch (e) { /* niente */ } traduci(); });
  });
  $("file").addEventListener("change", function (e) { var f = e.target.files[0]; if (f) carica(f, f.name); e.target.value = ""; });
  document.querySelectorAll("[data-esempio]").forEach(function (b) {
    b.addEventListener("click", function () {
      fetch("esempi/" + b.dataset.esempio).then(function (r) { return r.blob(); }).then(function (blob) { carica(blob, b.dataset.esempio); });
    });
  });
  $("barra").addEventListener("submit", function (e) { e.preventDefault(); chiedi($("domanda").value); });
  $("nuova").addEventListener("click", function () { post("/api/nuova"); $("risposte").innerHTML = ""; $("domanda").focus(); });
  Promise.all([fetch("testi.json").then(function (r) { return r.json(); }), fetch("/api/modo").then(function (r) { return r.json(); })])
    .then(function (x) { T = x[0]; modo = x[1]; traduci(); });
})();
