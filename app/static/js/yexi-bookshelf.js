(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.YexiBookshelf = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var SITE_BASE = 'https://twinjades.github.io/USTC_Study_Materials_Navigation/';
  var INDEX_URL = SITE_BASE + 'data/agent/index.json';
  var CACHE_KEY = 'icourse:yexi-bookshelf-index:v1';
  var CACHE_TTL_MS = 6 * 60 * 60 * 1000;
  var STALE_FALLBACK_MS = 7 * 24 * 60 * 60 * 1000;
  var FETCH_TIMEOUT_MS = 8000;

  /**
   * Extract deduplicated, trimmed course codes that have resources from index.json.
   */
  function extractResourceCodes(payload) {
    if (!payload || !Array.isArray(payload.courses)) {
      return [];
    }
    var seen = Object.create(null);
    var codes = [];
    for (var i = 0; i < payload.courses.length; i++) {
      var item = payload.courses[i];
      if (!item || item.has_resources !== true || typeof item.code !== 'string') {
        continue;
      }
      var trimmed = item.code.trim();
      if (!trimmed) {
        continue;
      }
      var upper = trimmed.toUpperCase();
      if (!seen[upper]) {
        seen[upper] = true;
        codes.push(trimmed);
      }
    }
    return codes;
  }

  /**
   * Build an uppercase-keyed lookup map preserving each canonical course code.
   */
  function buildCodeMap(codes) {
    var map = new Map();
    if (!Array.isArray(codes)) {
      return map;
    }
    for (var i = 0; i < codes.length; i++) {
      if (typeof codes[i] !== 'string') {
        continue;
      }
      var trimmed = codes[i].trim();
      if (!trimmed) {
        continue;
      }
      var upper = trimmed.toUpperCase();
      if (!map.has(upper)) {
        map.set(upper, trimmed);
      }
    }
    return map;
  }

  /**
   * Match a course's short code or courseries (e.g. STAT200202, CS1001A.01, PHYS1008B+01)
   * against the canonical resource code map.
   */
  function resolveCourseCode(codeMap, rawCode, rawSeries) {
    if (!codeMap || typeof codeMap.get !== 'function') {
      return null;
    }

    var candidates = [];
    if (typeof rawCode === 'string' && rawCode.trim()) {
      candidates.push(rawCode.trim());
    }
    if (typeof rawSeries === 'string' && rawSeries.trim()) {
      var series = rawSeries.trim();
      candidates.push(series);
      var dotStripped = series.replace(/\.[0-9A-Za-z]+$/, '');
      if (dotStripped !== series) {
        candidates.push(dotStripped);
      }
      var twoDigitStripped = series.replace(/\d{2}$/, '');
      if (twoDigitStripped !== series) {
        candidates.push(twoDigitStripped);
      }
      var threeDigitStripped = series.replace(/\d{3}$/, '');
      if (threeDigitStripped !== series) {
        candidates.push(threeDigitStripped);
      }
    }

    for (var i = 0; i < candidates.length; i++) {
      var hit = codeMap.get(candidates[i].toUpperCase());
      if (hit) {
        return hit;
      }
    }
    return null;
  }

  function buildCourseUrl(code) {
    return SITE_BASE + 'course.html?code=' + encodeURIComponent(code);
  }

  function clearElement(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  /**
   * Populate and reveal a course slot element using safe DOM APIs.
   */
  function renderSlot(slotEl, matchedCode, doc) {
    if (!slotEl || !matchedCode || !doc) {
      return false;
    }
    var kind = slotEl.getAttribute('data-yexi-course-slot');
    var href = buildCourseUrl(matchedCode);

    if (kind === 'detail') {
      clearElement(slotEl);
      var label = doc.createElement('strong');
      label.textContent = '课程资料';
      slotEl.appendChild(label);
      slotEl.appendChild(doc.createTextNode('：'));

      var link = doc.createElement('a');
      link.setAttribute('href', href);
      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener noreferrer');

      var bookIcon = doc.createElement('span');
      bookIcon.setAttribute('class', 'glyphicon glyphicon-book');
      bookIcon.setAttribute('aria-hidden', 'true');
      link.appendChild(bookIcon);

      link.appendChild(doc.createTextNode(' 前往也西书架查看该课程学习资料 '));

      var extIcon = doc.createElement('span');
      extIcon.setAttribute('class', 'glyphicon glyphicon-new-window');
      extIcon.setAttribute('aria-hidden', 'true');
      link.appendChild(extIcon);

      slotEl.appendChild(link);
      slotEl.style.display = '';
      return true;
    }

    if (kind === 'list') {
      clearElement(slotEl);
      var badge = doc.createElement('a');
      badge.setAttribute('class', 'label label-primary');
      badge.setAttribute('href', href);
      badge.setAttribute('target', '_blank');
      badge.setAttribute('rel', 'noopener noreferrer');
      badge.setAttribute('title', '在也西书架查看该课程学习资料');
      badge.setAttribute('style', 'text-decoration:none');
      badge.textContent = '课程资料';

      slotEl.appendChild(badge);
      slotEl.style.display = '';
      return true;
    }

    return false;
  }

  function renderAllSlots(doc, codeMap) {
    if (!doc || typeof doc.querySelectorAll !== 'function') {
      return 0;
    }
    var slots = doc.querySelectorAll('[data-yexi-course-slot]');
    var rendered = 0;
    for (var i = 0; i < slots.length; i++) {
      var slot = slots[i];
      var code = resolveCourseCode(
        codeMap,
        slot.getAttribute('data-course-code'),
        slot.getAttribute('data-course-series')
      );
      if (code && renderSlot(slot, code, doc)) {
        rendered++;
      }
    }
    return rendered;
  }

  function readCache(storage, now) {
    if (!storage || typeof storage.getItem !== 'function') {
      return null;
    }
    try {
      var raw = storage.getItem(CACHE_KEY);
      if (!raw) {
        return null;
      }
      var parsed = JSON.parse(raw);
      if (
        !parsed ||
        typeof parsed.fetchedAt !== 'number' ||
        !Array.isArray(parsed.codes)
      ) {
        return null;
      }
      var age = now - parsed.fetchedAt;
      if (age < 0 || age > STALE_FALLBACK_MS) {
        return null;
      }
      return {
        codes: parsed.codes,
        isFresh: age < CACHE_TTL_MS,
      };
    } catch (e) {
      return null;
    }
  }

  function writeCache(storage, codes, now) {
    if (!storage || typeof storage.setItem !== 'function') {
      return;
    }
    try {
      storage.setItem(CACHE_KEY, JSON.stringify({ fetchedAt: now, codes: codes }));
    } catch (e) {
      // Ignore quota / privacy-mode storage errors.
    }
  }

  function fetchJsonWithTimeout(fetchFn, url, timeoutMs) {
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = null;
    var options = {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
    };
    if (controller) {
      options.signal = controller.signal;
      timer = setTimeout(function () {
        controller.abort();
      }, timeoutMs);
    }
    return Promise.resolve()
      .then(function () {
        return fetchFn(url, options);
      })
      .then(function (res) {
        if (!res || !res.ok) {
          throw new Error('Failed to load Yexi Bookshelf index');
        }
        return res.json();
      })
      .finally(function () {
        if (timer !== null) {
          clearTimeout(timer);
        }
      });
  }

  /**
   * Load resource course codes from localStorage cache or network, with stale-cache fallback.
   */
  function loadResourceCodes(options) {
    var opts = options || {};
    var now = typeof opts.now === 'function' ? opts.now() : Date.now();
    var storage =
      'storage' in opts
        ? opts.storage
        : typeof window !== 'undefined'
          ? window.localStorage
          : null;
    var fetchFn =
      'fetch' in opts
        ? opts.fetch
        : typeof fetch === 'function'
          ? fetch
          : null;
    var indexUrl = opts.indexUrl || INDEX_URL;
    var timeoutMs = typeof opts.timeoutMs === 'number' ? opts.timeoutMs : FETCH_TIMEOUT_MS;

    var cached = readCache(storage, now);
    if (cached && cached.isFresh) {
      return Promise.resolve(cached.codes);
    }

    if (typeof fetchFn !== 'function') {
      return Promise.resolve(cached ? cached.codes : []);
    }

    return fetchJsonWithTimeout(fetchFn, indexUrl, timeoutMs)
      .then(function (payload) {
        var codes = extractResourceCodes(payload);
        writeCache(storage, codes, now);
        return codes;
      })
      .catch(function () {
        return cached ? cached.codes : [];
      });
  }

  function initYexiBookshelf(doc, options) {
    var targetDoc = doc || (typeof document !== 'undefined' ? document : null);
    if (!targetDoc || typeof targetDoc.querySelectorAll !== 'function') {
      return Promise.resolve(0);
    }
    var slots = targetDoc.querySelectorAll('[data-yexi-course-slot]');
    if (!slots || slots.length === 0) {
      return Promise.resolve(0);
    }
    return loadResourceCodes(options)
      .then(function (codes) {
        if (!codes || codes.length === 0) {
          return 0;
        }
        return renderAllSlots(targetDoc, buildCodeMap(codes));
      })
      .catch(function () {
        return 0;
      });
  }

  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        initYexiBookshelf(document);
      });
    } else {
      initYexiBookshelf(document);
    }
  }

  return {
    SITE_BASE: SITE_BASE,
    INDEX_URL: INDEX_URL,
    CACHE_KEY: CACHE_KEY,
    CACHE_TTL_MS: CACHE_TTL_MS,
    STALE_FALLBACK_MS: STALE_FALLBACK_MS,
    extractResourceCodes: extractResourceCodes,
    buildCodeMap: buildCodeMap,
    resolveCourseCode: resolveCourseCode,
    buildCourseUrl: buildCourseUrl,
    renderSlot: renderSlot,
    renderAllSlots: renderAllSlots,
    loadResourceCodes: loadResourceCodes,
    initYexiBookshelf: initYexiBookshelf,
  };
});
