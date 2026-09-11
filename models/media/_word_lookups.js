/* Wires up the lookup panels around a headword: the WordReference and image
 * search links, and the Wiktionary frame. The word and the language come from #hw:
 *   <span id="hw" data-wr-lang-pair="fren" data-wikt-lang="French">chien</span>
 * Every link and panel says where it points, with {word} and {lang} replaced,
 * so the markup is the same in every note type.
 * Include the snippets a note type needs, then this file once. */
(function () {
  var headword = document.getElementById('hw');
  if (!headword) return;

  var word = encodeURIComponent(headword.textContent.trim());

  function buildUrl(element, language) {
    var url = element.getAttribute('data-url');
    return url.replace('{word}', word).replace('{lang}', language);
  }

  document.querySelectorAll('a[data-url]').forEach(function (link) {
    link.href = buildUrl(link, headword.getAttribute('data-wr-lang-pair'));
  });

  document.querySelectorAll('button[data-frame]').forEach(function (button) {
    var frame = document.getElementById(button.getAttribute('data-frame'));
    if (!frame) return;

    button.addEventListener('click', function () {
      if (!frame.src)
        frame.src = buildUrl(button, headword.getAttribute('data-wikt-lang'));

      frame.hidden = !frame.hidden;
      button.classList.toggle('open', !frame.hidden);
    });
  });
})();
