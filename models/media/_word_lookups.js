/* Wires up the lookup panels around a headword: the WordReference and image
 * search links, and the Wiktionary frame. The word and the language come from #hw:
 *   <span id="hw" data-wr-lang-pair="fren" data-wikt-lang="French">chien</span>
 * Every link and panel says where it points, with {word} and {lang} replaced,
 * so the markup is the same in every note type.
 * A note type shared by several languages says data-deck="{{Deck}}" instead,
 * and the language follows from the deck the card is in.
 * Include the snippets a note type needs, then this file once. */
(function () {
  var LANGUAGES_BY_DECK = {
    Spanish: {
      wordreference: 'esen', wiktionary: 'Spanish', conjugation: 'esverbs'
    },
    Italian: {
      wordreference: 'iten', wiktionary: 'Italian', conjugation: 'itverbs'
    }
  };

  var headword = document.getElementById('hw');
  if (!headword) return;

  var word = encodeURIComponent(headword.textContent.trim());
  var languages = readLanguages();

  function readLanguages() {
    var deck = headword.getAttribute('data-deck');
    for (var language in LANGUAGES_BY_DECK) {
      if (deck && deck.indexOf(language) !== -1) return LANGUAGES_BY_DECK[language];
    }

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
    return url.replace('{word}', word).replace('{lang}', language);
  }

  document.querySelectorAll('a[data-url]').forEach(function (link) {
    link.href = buildUrl(link, languages.wordreference);
  });

  document.querySelectorAll('button[data-frame]').forEach(function (button) {
    var frame = document.getElementById(button.getAttribute('data-frame'));
    if (!frame) return;

    button.addEventListener('click', function () {
      if (!frame.src)
        frame.src = buildUrl(button, languages.wiktionary);

      frame.hidden = !frame.hidden;
      button.classList.toggle('open', !frame.hidden);
    });
  });
})();
