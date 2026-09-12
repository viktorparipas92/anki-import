/* Wires up the lookup panels around a headword: the WordReference and image
 * search links, and the Wiktionary frame. The word and the language come from #hw:
 *   <span id="hw" data-wr-lang-pair="fren" data-wikt-lang="French">chien</span>
 * Every link and panel says where it points, with {word} and {lang} replaced,
 * so the markup is the same in every note type.
 * A note type shared by several languages says data-key="{{text:Key}}" instead,
 * and the language follows from the [IT] or (ES) marker in the key.
 * Include the snippets a note type needs, then this file once. */
(function () {
  var LANGUAGES_BY_CODE = {
    ES: {wordreference: 'esen', wiktionary: 'Spanish', conjugation: 'esverbs'},
    IT: {wordreference: 'iten', wiktionary: 'Italian', conjugation: 'itverbs'}
  };
  var CODE_IN_KEY = /[\[(](IT|ES)[\])]/;

  var headword = document.getElementById('hw');
  if (!headword) return;

  var word = encodeURIComponent(headword.textContent.trim());
  var languages = readLanguages();

  function readLanguages() {
    var key = headword.getAttribute('data-key');
    var code = key && key.match(CODE_IN_KEY);
    if (code) return LANGUAGES_BY_CODE[code[1]];

    return {
      wordreference: headword.getAttribute('data-wr-lang-pair'),
      wiktionary: headword.getAttribute('data-wikt-lang'),
      conjugation: headword.getAttribute('data-wr-conj')
    };
  }

  function buildUrl(element, defaultLanguage) {
    var url = element.getAttribute('data-url');
    var named = element.getAttribute('data-lang');
    var language = named ? languages[named] : defaultLanguage;
    if (url.indexOf('{lang}') !== -1 && !language) return '';

    return url.replace('{word}', word).replace('{lang}', language);
  }

  document.querySelectorAll('a[data-url]').forEach(function (link) {
    var url = buildUrl(link, languages.wordreference);
    if (url) link.href = url;
    else link.hidden = true;
  });

  document.querySelectorAll('button[data-frame]').forEach(function (button) {
    var frame = document.getElementById(button.getAttribute('data-frame'));
    if (!frame) return;

    var url = buildUrl(button, languages.wiktionary);
    if (!url) {
      button.hidden = true;
      return;
    }

    button.addEventListener('click', function () {
      if (!frame.src) frame.src = url;

      frame.hidden = !frame.hidden;
      button.classList.toggle('open', !frame.hidden);
    });
  });
})();
