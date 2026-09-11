/* Swedish note type - pull the "Svenska" section from sv.wiktionary.org
 * Injected into #wt-body. Toggled by #wt-btn.
 * Wiktionary sends Access-Control-Allow-Origin: *, so this works from the card
 * on desktop and mobile (online only). */
(function () {
  var SHOW_TRANSLATIONS = false;   // set true to keep the "Översättningar" blocks
  var API = 'https://sv.wiktionary.org/w/api.php?action=parse&prop=text&format=json&origin=*&page=';

  var btn = document.getElementById('wt-btn');
  var body = document.getElementById('wt-body');
  var hw = document.getElementById('hw');
  if (!btn || !body || !hw) return;

  var word = hw.textContent.trim();
  var loaded = false;

  function clean(node) {
    node.querySelectorAll('script, style, table, .mw-editsection, .navbox, .thumb, sup.reference')
        .forEach(function (n) { n.remove(); });
    node.querySelectorAll('a').forEach(function (a) {
      a.replaceWith(document.createTextNode(a.textContent));   // no dead links inside the card
    });
    return node;
  }

  function swedishSection(htmlText) {
    var doc = new DOMParser().parseFromString(htmlText, 'text/html');
    var heads = Array.prototype.slice.call(doc.querySelectorAll('h2'));
    var start = heads.find(function (h) { return /svenska/i.test(h.textContent); });
    if (!start) return null;

    var out = document.createElement('div');
    var n = start.nextElementSibling;
    while (n && n.tagName !== 'H2') {
      if (SHOW_TRANSLATIONS || !/översättningar/i.test(n.textContent || '')) {
        out.appendChild(n.cloneNode(true));
      }
      n = n.nextElementSibling;
    }
    return clean(out);
  }

  function load() {
    body.textContent = '…';
    fetch(API + encodeURIComponent(word))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.parse) throw new Error('no entry');
        var sec = swedishSection(d.parse.text['*']);
        body.textContent = '';
        if (sec) body.appendChild(sec);
        else body.textContent = 'Ingen svensk sektion.';
      })
      .catch(function () { body.textContent = '—'; });
  }

  btn.addEventListener('click', function () {
    var open = body.hasAttribute('hidden');
    if (open && !loaded) { loaded = true; load(); }
    if (open) body.removeAttribute('hidden'); else body.setAttribute('hidden', '');
    btn.classList.toggle('open', open);
  });
})();
