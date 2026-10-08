/* Wires up the lookup panels around a headword: the WordReference and image
 * search links, and the Wiktionary frame. The word and the language come from #hw:
 *   <span id="hw" data-wr-lang-pair="fren" data-wikt-lang="French">chien</span>
 * Every link and panel says where it points, with {word} and {lang} replaced,
 * so the markup is the same in every note type.
 * A note type shared by several languages says data-key="{{text:Key}}" instead,
 * and the language follows from the [IT] or (ES) marker in the key.
 * A Wiktionary button with data-section="Conjugation" opens that section of the
 * language. Wiktionary numbers repeated headings across languages (Conjugation_6),
 * so the anchor is looked up in its API, falling back to the language's section.
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

    var section = button.getAttribute('data-section');
    var isRequested = false;
    button.addEventListener('click', function () {
      if (!isRequested) {
        isRequested = true;
        if (section) openSection(frame, url, section);
        else frame.src = url;
      }

      frame.hidden = !frame.hidden;
      button.classList.toggle('open', !frame.hidden);
    });
  });

  function openSection(frame, url, section) {
    findWiktionaryAnchor(section, function (anchor) {
      var page = url.split('#')[0];
      frame.src = anchor ? page + '#' + anchor : url;
    });
  }

  function findWiktionaryAnchor(section, callback) {
    var api = 'https://en.wiktionary.org/w/api.php?action=parse&prop=sections' +
      '&format=json&origin=*&page=' + word;
    fetch(api)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        callback(pickAnchor(data.parse.sections, section));
      })
      .catch(function () { callback(''); });
  }

  function pickAnchor(sections, section) {
    var language = '';
    for (var index = 0; index < sections.length; index++) {
      var entry = sections[index];
      if (entry.toclevel === 1) language = entry.line;
      else if (language === languages.wiktionary && entry.line === section) return entry.anchor;
    }

    return '';
  }
})();
