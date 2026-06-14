(function initPhrasesAudio() {
  const synth = window.speechSynthesis;
  if (!synth) return;

  const buttons = document.querySelectorAll('.phrases-speak');
  if (!buttons.length) return;

  const labels = window.ivtPhrasesAudio || {};
  const listenLabel = labels.listen || 'Listen';
  const stopLabel = labels.stop || 'Stop';

  let voices = [];
  let activeBtn = null;

  function loadVoices() {
    voices = synth.getVoices();
  }

  function pickViVoice() {
    return voices.find((v) => v.lang === 'vi-VN')
      || voices.find((v) => v.lang.startsWith('vi'))
      || null;
  }

  function setSpeaking(btn, on) {
    if (activeBtn && activeBtn !== btn) {
      activeBtn.classList.remove('is-speaking');
      activeBtn.setAttribute('aria-label', listenLabel);
    }
    activeBtn = on ? btn : null;
    if (!btn) return;
    btn.classList.toggle('is-speaking', on);
    btn.setAttribute('aria-label', on ? stopLabel : listenLabel);
  }

  loadVoices();
  synth.addEventListener('voiceschanged', loadVoices);

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const text = (btn.dataset.speak || '').trim();
      if (!text) return;

      if (btn.classList.contains('is-speaking')) {
        synth.cancel();
        setSpeaking(btn, false);
        return;
      }

      synth.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'vi-VN';
      const voice = pickViVoice();
      if (voice) utterance.voice = voice;
      utterance.rate = 0.88;
      utterance.onend = () => setSpeaking(btn, false);
      utterance.onerror = () => setSpeaking(btn, false);

      setSpeaking(btn, true);
      synth.speak(utterance);
    });
  });
})();
