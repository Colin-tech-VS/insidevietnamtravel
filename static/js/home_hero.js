(function () {
  var showcase = document.getElementById('hero-showcase');
  var slidesRoot = document.getElementById('hero-slides');
  if (!showcase || !slidesRoot) return;

  var panels = showcase.querySelectorAll('[data-hero-panel]');
  var slides = slidesRoot.querySelectorAll('[data-hero-slide]');
  var thumbs = showcase.querySelectorAll('[data-hero-go]');
  var progressBar = showcase.querySelector('.hero-showcase__progress-bar');
  var interval = parseInt(showcase.dataset.interval || '6500', 10);
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var current = 0;
  var timer = null;

  if (!panels.length) return;

  function goTo(i) {
    i = ((i % panels.length) + panels.length) % panels.length;
    current = i;
    panels.forEach(function (panel, idx) {
      var active = idx === i;
      panel.classList.toggle('is-active', active);
      panel.setAttribute('aria-hidden', active ? 'false' : 'true');
    });
    slides.forEach(function (slide, idx) {
      slide.classList.toggle('is-active', idx === i);
    });
    thumbs.forEach(function (thumb, idx) {
      var active = idx === i;
      thumb.classList.toggle('is-active', active);
      thumb.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    restartProgress();
  }

  function restartProgress() {
    if (!progressBar || reduced || panels.length < 2) return;
    progressBar.style.transition = 'none';
    progressBar.style.width = '0%';
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        progressBar.style.transition = 'width ' + interval + 'ms linear';
        progressBar.style.width = '100%';
      });
    });
  }

  function next() {
    goTo(current + 1);
  }

  function startAutoplay() {
    stopAutoplay();
    if (reduced || panels.length < 2) return;
    restartProgress();
    timer = setInterval(next, interval);
  }

  function stopAutoplay() {
    if (timer) clearInterval(timer);
    timer = null;
    if (progressBar) {
      progressBar.style.transition = 'none';
      progressBar.style.width = progressBar.style.width || '0%';
    }
  }

  thumbs.forEach(function (btn) {
    btn.addEventListener('click', function () {
      goTo(parseInt(btn.getAttribute('data-hero-go'), 10));
      startAutoplay();
    });
  });

  showcase.addEventListener('mouseenter', stopAutoplay);
  showcase.addEventListener('mouseleave', startAutoplay);
  showcase.addEventListener('focusin', stopAutoplay);
  showcase.addEventListener('focusout', function (e) {
    if (!showcase.contains(e.relatedTarget)) startAutoplay();
  });

  goTo(0);
  startAutoplay();
})();
