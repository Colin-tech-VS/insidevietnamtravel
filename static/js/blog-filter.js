(function () {
  var nav = document.getElementById('blog-filter');
  var grid = document.getElementById('blog-grid');
  var empty = document.getElementById('blog-empty');
  if (!nav || !grid) return;

  var chips = nav.querySelectorAll('[data-filter]');
  var items = grid.querySelectorAll('.blog-item');

  function apply(filter) {
    var shown = 0;
    items.forEach(function (item) {
      var match = filter === 'all' || item.dataset.category === filter;
      item.hidden = !match;
      if (match) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function (e) {
      // Progressive enhancement: without JS the links go to category pages.
      e.preventDefault();
      chips.forEach(function (c) { c.classList.remove('is-active'); });
      chip.classList.add('is-active');
      apply(chip.dataset.filter);
    });
  });
})();
