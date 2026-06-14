(function initPhrasesAudio() {
  const buttons = document.querySelectorAll('.phrases-speak');
  if (!buttons.length) return;

  const cfg = window.ivtPhrasesAudio || {};
  const listenLabel = cfg.listen || 'Listen';
  const stopLabel = cfg.stop || 'Stop';
  const ttsBase = cfg.ttsUrl || '/api/phrases/tts';

  const synth = window.speechSynthesis;
  let voices = [];
  let activeBtn = null;
  let activeAudio = null;
  let synthStarted = false;

  function loadVoices() {
    if (!synth) return;
    voices = synth.getVoices();
  }

  function hasViVoice() {
    loadVoices();
    return voices.some((v) => (v.lang || '').toLowerCase().startsWith('vi'));
  }

  function pickViVoice() {
    return voices.find((v) => v.lang === 'vi-VN')
      || voices.find((v) => (v.lang || '').toLowerCase().startsWith('vi'))
      || null;
  }

  function stopAll() {
    if (synth) synth.cancel();
    if (activeAudio) {
      activeAudio.pause();
      activeAudio.src = '';
      activeAudio = null;
    }
    synthStarted = false;
  }

  function setSpeaking(btn, on) {
    if (activeBtn && activeBtn !== btn) {
      activeBtn.classList.remove('is-speaking', 'is-error');
      activeBtn.setAttribute('aria-label', listenLabel);
    }
    activeBtn = on ? btn : null;
    if (!btn) return;
    btn.classList.toggle('is-speaking', on);
    btn.classList.remove('is-error');
    btn.setAttribute('aria-label', on ? stopLabel : listenLabel);
  }

  function showError(btn) {
    btn.classList.remove('is-speaking');
    btn.classList.add('is-error');
    window.setTimeout(() => btn.classList.remove('is-error'), 2200);
    setSpeaking(btn, false);
  }

  function ttsUrl(text) {
    return `${ttsBase}?q=${encodeURIComponent(text)}`;
  }

  function speakWithAudio(text, btn) {
    stopAll();
    const audio = new Audio(ttsUrl(text));
    activeAudio = audio;
    setSpeaking(btn, true);

    const cleanup = () => {
      if (activeAudio === audio) activeAudio = null;
      setSpeaking(btn, false);
    };

    audio.addEventListener('ended', cleanup);
    audio.addEventListener('error', () => {
      cleanup();
      showError(btn);
    });

    audio.play().catch(() => {
      cleanup();
      showError(btn);
    });
  }

  function speakWithSynth(text, btn) {
    if (!synth) {
      speakWithAudio(text, btn);
      return;
    }

    stopAll();
    loadVoices();

    window.setTimeout(() => {
      synthStarted = false;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'vi-VN';
      const voice = pickViVoice();
      if (voice) utterance.voice = voice;
      utterance.rate = 0.88;

      utterance.onstart = () => { synthStarted = true; };
      utterance.onend = () => setSpeaking(btn, false);
      utterance.onerror = () => speakWithAudio(text, btn);

      setSpeaking(btn, true);
      synth.speak(utterance);

      window.setTimeout(() => {
        if (!synthStarted && btn.classList.contains('is-speaking')) {
          synth.cancel();
          speakWithAudio(text, btn);
        }
      }, 700);
    }, 60);
  }

  function speak(text, btn) {
    if (!hasViVoice()) {
      speakWithAudio(text, btn);
      return;
    }
    speakWithSynth(text, btn);
  }

  if (synth) {
    loadVoices();
    synth.addEventListener('voiceschanged', loadVoices);
  }

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const text = (btn.dataset.speak || '').trim();
      if (!text) return;

      if (btn.classList.contains('is-speaking')) {
        stopAll();
        setSpeaking(btn, false);
        return;
      }

      speak(text, btn);
    });
  });
})();
