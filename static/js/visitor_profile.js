(function initVisitorProfile(global) {
  'use strict';

  var COOKIE_NAME = 'ivt_vp';
  var CONSENT_KEY = 'ivt_cookie_consent';
  var MAX_AGE_DAYS = 395;
  var PROFILE_VERSION = 2;
  var SYNC_DEBOUNCE_MS = 4000;
  var lastSync = 0;

  var DEST_SLUGS = [
    'hanoi', 'halong', 'sapa', 'hue', 'da-nang', 'hoi-an',
    'ho-chi-minh-city', 'delta-du-mekong', 'phu-quoc',
  ];

  var PATH_RULES = [
    [/visa|e-?visa/i, 'visa'],
    [/securite|travel-safety|safety/i, 'safety'],
    [/coutumes|customs|etiquette/i, 'customs'],
    [/phrases|vietnamese-phrases/i, 'phrases'],
    [/quand-partir|best-time|season/i, 'season'],
    [/budget|estimer/i, 'budget'],
    [/preparer|plan-my-trip|prepare/i, 'prepare'],
    [/applications|useful-apps|apps/i, 'apps'],
    [/essentiels|essentials|esim|assurance/i, 'essentials'],
    [/blog\//i, 'blog'],
    [/itineraire|itinerary/i, 'itinerary'],
  ];

  function readConsent() {
    try {
      var raw = localStorage.getItem(CONSENT_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function personalizationEnabled() {
    var c = readConsent();
    return !!(c && c.personalization);
  }

  function uuid() {
    if (global.crypto && crypto.randomUUID) return crypto.randomUUID().slice(0, 12);
    return ('v' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)).slice(0, 12);
  }

  function getCookie(name) {
    var parts = ('; ' + document.cookie).split('; ' + name + '=');
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
    return '';
  }

  function setCookie(name, value, days) {
    var maxAge = (days || MAX_AGE_DAYS) * 24 * 3600;
    var secure = global.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = name + '=' + encodeURIComponent(value)
      + '; Path=/; Max-Age=' + maxAge + '; SameSite=Lax' + secure;
  }

  function deleteCookie(name) {
    document.cookie = name + '=; Path=/; Max-Age=0; SameSite=Lax';
  }

  function compactList(arr, limit) {
    var out = [];
    var seen = {};
    (arr || []).forEach(function (x) {
      if (!x || seen[x]) return;
      seen[x] = true;
      out.push(x);
    });
    return out.slice(0, limit || 16);
  }

  function normalizeProfile(data) {
    data = data || {};
    var profile = {
      v: PROFILE_VERSION,
      id: String(data.id || uuid()).slice(0, 36),
      l: (document.documentElement.lang || 'fr').slice(0, 2) === 'en' ? 'en' : 'fr',
      g: data.g || null,
      s: data.s || null,
      d: data.d || null,
      c: compactList((data.c || []).filter(function (s) { return DEST_SLUGS.indexOf(s) >= 0; }), 8),
      i: compactList(data.i || [], 16),
      p: Array.isArray(data.p) ? data.p.slice(0, 10) : [],
      u: compactList(data.u || [], 8),
      t: data.t || Math.floor(Date.now() / 1000),
    };
    return profile;
  }

  function loadProfile() {
    if (!personalizationEnabled()) return null;
    var raw = getCookie(COOKIE_NAME);
    if (!raw) return null;
    try {
      var data = JSON.parse(raw);
      if (data.v !== PROFILE_VERSION) return null;
      return normalizeProfile(data);
    } catch (e) {
      return null;
    }
  }

  function saveProfile(profile) {
    if (!personalizationEnabled()) return null;
    profile = normalizeProfile(profile);
    profile.t = Math.floor(Date.now() / 1000);
    profile.l = (document.documentElement.lang || 'fr').slice(0, 2) === 'en' ? 'en' : 'fr';
    setCookie(COOKIE_NAME, JSON.stringify(profile), MAX_AGE_DAYS);
    scheduleSync(profile);
    global.dispatchEvent(new CustomEvent('ivt:profile-updated', { detail: profile }));
    return profile;
  }

  function mergeProfile(updates) {
    var base = loadProfile() || normalizeProfile({ id: uuid() });
    ['g', 's', 'd', 'l'].forEach(function (k) {
      if (updates[k] !== undefined && updates[k] !== null) base[k] = updates[k];
    });
    if (updates.c) base.c = compactList(base.c.concat(updates.c), 8);
    if (updates.i) base.i = compactList(base.i.concat(updates.i), 16);
    if (updates.u) base.u = compactList(base.u.concat(updates.u), 8);
    if (updates.p) {
      var pages = {};
      (base.p || []).forEach(function (entry) {
        pages[entry[0]] = entry[1];
      });
      updates.p.forEach(function (entry) {
        pages[entry[0]] = (pages[entry[0]] || 0) + entry[1];
      });
      base.p = Object.keys(pages).map(function (p) { return [p, pages[p]]; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 10);
    }
    return saveProfile(base);
  }

  function pathTags(path) {
    var tags = [];
    PATH_RULES.forEach(function (rule) {
      if (rule[0].test(path)) tags.push(rule[1]);
    });
    DEST_SLUGS.forEach(function (slug) {
      if (path.indexOf('/' + slug) >= 0) tags.push('dest:' + slug);
    });
    return tags;
  }

  function trackPage(path) {
    if (!personalizationEnabled()) return;
    path = path || global.location.pathname || '/';
    if (path.indexOf('/admin') === 0 || path.indexOf('/static') === 0) return;
    mergeProfile({ i: pathTags(path), p: [[path, 1]] });
  }

  function trackTool(toolKey) {
    if (!personalizationEnabled() || !toolKey) return;
    mergeProfile({ u: [toolKey] });
  }

  function saveTripPrefs(prefs) {
    if (!personalizationEnabled() || !prefs) return null;
    const patch = {
      g: prefs.group || prefs.g,
      s: prefs.style || prefs.s,
      d: prefs.duration || prefs.d,
      c: prefs.cities || prefs.c || [],
      u: ['prepare'],
    };
    const persons = prefs.persons != null ? prefs.persons : prefs.n;
    if (persons != null) patch.n = Number(persons) || 1;
    return mergeProfile(patch);
  }

  function clearProfile() {
    deleteCookie(COOKIE_NAME);
    global.dispatchEvent(new CustomEvent('ivt:profile-cleared'));
  }

  function hasSignal(profile) {
    if (!profile) return false;
    return !!(profile.g || profile.s || profile.d
      || (profile.c && profile.c.length)
      || (profile.i && profile.i.length)
      || (profile.u && profile.u.length));
  }

  function scheduleSync(profile) {
    var syncUrl = (document.body && document.body.dataset.profileSync) || '';
    if (!syncUrl || !profile || !profile.id) return;
    var now = Date.now();
    if (now - lastSync < SYNC_DEBOUNCE_MS) return;
    lastSync = now;

    var payload = {
      id: profile.id,
      g: profile.g,
      s: profile.s,
      d: profile.d,
      c: profile.c,
      i: profile.i,
      path: global.location.pathname,
    };

    if (navigator.sendBeacon) {
      try {
        navigator.sendBeacon(syncUrl, new Blob([JSON.stringify(payload)], { type: 'application/json' }));
        return;
      } catch (e) { /* fetch fallback */ }
    }
    fetch(syncUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
      credentials: 'same-origin',
    }).catch(function () {});
  }

  function onConsentChange() {
    if (!personalizationEnabled()) {
      clearProfile();
      return;
    }
    if (!loadProfile()) saveProfile(normalizeProfile({ id: uuid() }));
    trackPage(global.location.pathname);
  }

  global.addEventListener('ivt:consent-updated', onConsentChange);

  global.ivtProfile = {
    enabled: personalizationEnabled,
    load: loadProfile,
    save: saveProfile,
    merge: mergeProfile,
    trackPage: trackPage,
    trackTool: trackTool,
    saveTripPrefs: saveTripPrefs,
    clear: clearProfile,
    hasSignal: hasSignal,
    toJSON: function () { return loadProfile(); },
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (!personalizationEnabled()) return;
    if (!loadProfile()) saveProfile(normalizeProfile({ id: uuid() }));
    trackPage(global.location.pathname);
  });
})(window);
