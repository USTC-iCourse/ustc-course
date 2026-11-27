'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const yexi = require('../app/static/js/yexi-bookshelf.js');

function createFakeElement(tagName) {
  const attrs = Object.create(null);
  const children = [];
  const style = {};
  let text = '';
  return {
    tagName: tagName.toUpperCase(),
    children,
    style,
    get firstChild() {
      return children[0] || null;
    },
    get textContent() {
      if (children.length === 0) {
        return text;
      }
      return text + children.map((c) => c.textContent || '').join('');
    },
    set textContent(val) {
      text = String(val);
    },
    setAttribute(name, value) {
      attrs[name] = String(value);
    },
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
    },
    appendChild(node) {
      children.push(node);
      return node;
    },
    removeChild(node) {
      const idx = children.indexOf(node);
      if (idx >= 0) {
        children.splice(idx, 1);
      }
      return node;
    },
  };
}

function createFakeDocument(slots) {
  return {
    createElement(tag) {
      return createFakeElement(tag);
    },
    createTextNode(str) {
      return { nodeType: 3, textContent: String(str) };
    },
    querySelectorAll(selector) {
      assert.equal(selector, '[data-yexi-course-slot]');
      return slots;
    },
  };
}

function createSlot(kind, code, series) {
  const el = createFakeElement(kind === 'detail' ? 'div' : 'span');
  el.style.display = 'none';
  el.setAttribute('data-yexi-course-slot', kind);
  el.setAttribute('data-course-code', code || '');
  el.setAttribute('data-course-series', series || '');
  return el;
}

function createMemoryStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    dump() {
      return Object.fromEntries(map.entries());
    },
  };
}

test('extractResourceCodes filters has_resources=true and deduplicates', () => {
  const codes = yexi.extractResourceCodes({
    schema_version: 1,
    courses: [
      { code: '001046', name: '数值分析', has_resources: true },
      { code: '001046 ', name: 'dup', has_resources: true },
      { code: 'NOPE001', name: '未收录', has_resources: false },
      { code: ' ', has_resources: true },
      null,
      { code: 'PHYS1008B+', name: '力学', has_resources: true },
    ],
  });
  assert.deepEqual(codes, ['001046', 'PHYS1008B+']);
});

test('extractResourceCount handles valid, empty, and malformed payloads', () => {
  assert.equal(yexi.extractResourceCount({ resources: [{ id: 1 }, { id: 2 }] }), 2);
  assert.equal(yexi.extractResourceCount({ resources: [] }), null);
  assert.equal(yexi.extractResourceCount({}), null);
  assert.equal(yexi.extractResourceCount(null), null);
});

test('resolveCourseCode matches short code and courseries variants', () => {
  const codeMap = yexi.buildCodeMap(['001046', 'STAT2002', 'CS1001A', 'PHYS1008B+']);

  assert.equal(yexi.resolveCourseCode(codeMap, 'cs1001a', 'CS1001A.01'), 'CS1001A');
  assert.equal(yexi.resolveCourseCode(codeMap, '', '00104601'), '001046');
  assert.equal(yexi.resolveCourseCode(codeMap, '', 'stat200202'), 'STAT2002');
  assert.equal(yexi.resolveCourseCode(codeMap, '', 'CS1001A.03'), 'CS1001A');
  assert.equal(yexi.resolveCourseCode(codeMap, '', 'PHYS1008B+01'), 'PHYS1008B+');
  assert.equal(yexi.resolveCourseCode(codeMap, '', 'UNKNOWN01'), null);
});

test('buildCourseUrl and buildCourseDataUrl encode special characters properly', () => {
  assert.equal(
    yexi.buildCourseUrl('PHYS1008B+'),
    'https://twinjades.github.io/USTC_Study_Materials_Navigation/course.html?code=PHYS1008B%2B'
  );
  assert.equal(
    yexi.buildCourseDataUrl('001046'),
    'https://twinjades.github.io/USTC_Study_Materials_Navigation/data/agent/courses/001046.json'
  );
  assert.equal(
    yexi.buildCourseDataUrl('PHYS1008B+'),
    'https://twinjades.github.io/USTC_Study_Materials_Navigation/data/agent/courses/PHYS1008B%252B.json'
  );
});

test('initYexiBookshelf exits without fetching when page has no slots', async () => {
  let fetchCalls = 0;
  const doc = createFakeDocument([]);
  const count = await yexi.initYexiBookshelf(doc, {
    storage: createMemoryStorage(),
    fetch: async () => {
      fetchCalls++;
      throw new Error('should not fetch');
    },
  });
  assert.equal(count, 0);
  assert.equal(fetchCalls, 0);
});

test('initYexiBookshelf renders detail with count from fresh caches without network', async () => {
  const now = 1_700_000_000_000;
  const storage = createMemoryStorage({
    [yexi.CACHE_KEY]: JSON.stringify({
      fetchedAt: now - 1000,
      codes: ['001046', 'PHYS1008B+'],
    }),
    [yexi.COUNT_CACHE_KEY]: JSON.stringify({
      '001046': { count: 7, fetchedAt: now - 1000 },
    }),
  });
  const detailHit = createSlot('detail', '', '00104601');
  const listHit = createSlot('list', '', 'PHYS1008B+01');
  const listMiss = createSlot('list', '', 'NOPE99901');
  const doc = createFakeDocument([detailHit, listHit, listMiss]);

  let fetchCalls = 0;
  const rendered = await yexi.initYexiBookshelf(doc, {
    now: () => now,
    storage,
    fetch: async () => {
      fetchCalls++;
      throw new Error('should not fetch on fresh cache');
    },
  });

  assert.equal(fetchCalls, 0);
  assert.equal(rendered, 2);

  assert.equal(detailHit.style.display, '');
  const detailLink = detailHit.children.find((c) => c.tagName === 'A');
  assert.ok(detailLink);
  assert.equal(detailLink.textContent.trim(), '也西书架（7）');
  assert.equal(
    detailLink.getAttribute('href'),
    'https://twinjades.github.io/USTC_Study_Materials_Navigation/course.html?code=001046'
  );
  assert.equal(detailLink.getAttribute('target'), '_blank');
  assert.equal(detailLink.getAttribute('rel'), 'noopener noreferrer');

  assert.equal(listHit.style.display, '');
  const listLink = listHit.children.find((c) => c.tagName === 'A');
  assert.ok(listLink);
  assert.equal(listLink.textContent, '课程资料');
  assert.equal(
    listLink.getAttribute('href'),
    'https://twinjades.github.io/USTC_Study_Materials_Navigation/course.html?code=PHYS1008B%2B'
  );

  assert.equal(listMiss.style.display, 'none');
  assert.equal(listMiss.children.length, 0);
});

test('initYexiBookshelf fetches index and course resource count on cache miss', async () => {
  const now = 1_700_000_000_000;
  const storage = createMemoryStorage();
  const detailSlot = createSlot('detail', '', 'STAT200202');
  const doc = createFakeDocument([detailSlot]);

  const requestedUrls = [];
  const rendered = await yexi.initYexiBookshelf(doc, {
    now: () => now,
    storage,
    fetch: async (url, init) => {
      requestedUrls.push(url);
      assert.equal(init.credentials, 'omit');
      if (url === yexi.INDEX_URL) {
        return {
          ok: true,
          json: async () => ({
            schema_version: 1,
            courses: [
              { code: 'STAT2002', name: '概率论与数理统计', has_resources: true },
              { code: 'EMPTY01', name: '无资料', has_resources: false },
            ],
          }),
        };
      }
      if (url === yexi.buildCourseDataUrl('STAT2002')) {
        return {
          ok: true,
          json: async () => ({
            schema_version: 1,
            code: 'STAT2002',
            resources: new Array(62).fill({ id: 'x' }),
          }),
        };
      }
      throw new Error('unexpected url: ' + url);
    },
  });

  assert.deepEqual(requestedUrls, [yexi.INDEX_URL, yexi.buildCourseDataUrl('STAT2002')]);
  assert.equal(rendered, 1);
  assert.equal(detailSlot.style.display, '');
  const detailLink = detailSlot.children.find((c) => c.tagName === 'A');
  assert.equal(detailLink.textContent.trim(), '也西书架（62）');

  const cachedIndex = JSON.parse(storage.getItem(yexi.CACHE_KEY));
  assert.deepEqual(cachedIndex, { fetchedAt: now, codes: ['STAT2002'] });
  const cachedCounts = JSON.parse(storage.getItem(yexi.COUNT_CACHE_KEY));
  assert.deepEqual(cachedCounts, { STAT2002: { count: 62, fetchedAt: now } });
});

test('initYexiBookshelf does not fetch per-course JSON for list-only pages', async () => {
  const now = 1_700_000_000_000;
  const storage = createMemoryStorage({
    [yexi.CACHE_KEY]: JSON.stringify({
      fetchedAt: now - 1000,
      codes: ['001046', 'STAT2002'],
    }),
  });
  const doc = createFakeDocument([
    createSlot('list', '', '00104601'),
    createSlot('list', '', 'STAT200202'),
  ]);
  let fetchCalls = 0;
  const rendered = await yexi.initYexiBookshelf(doc, {
    now: () => now,
    storage,
    fetch: async () => {
      fetchCalls++;
      throw new Error('list slots should not fetch per-course JSON');
    },
  });
  assert.equal(rendered, 2);
  assert.equal(fetchCalls, 0);
});

test('initYexiBookshelf keeps detail link without count when count fetch fails', async () => {
  const now = 1_700_000_000_000;
  const storage = createMemoryStorage({
    [yexi.CACHE_KEY]: JSON.stringify({
      fetchedAt: now - 1000,
      codes: ['001046'],
    }),
  });
  const detailSlot = createSlot('detail', '', '00104601');
  const rendered = await yexi.initYexiBookshelf(createFakeDocument([detailSlot]), {
    now: () => now,
    storage,
    fetch: async () => ({ ok: false, status: 503 }),
  });
  assert.equal(rendered, 1);
  assert.equal(detailSlot.style.display, '');
  const detailLink = detailSlot.children.find((c) => c.tagName === 'A');
  assert.equal(detailLink.textContent.trim(), '也西书架');
  assert.equal(detailLink.getAttribute('target'), '_blank');
  assert.equal(detailLink.getAttribute('rel'), 'noopener noreferrer');
});

test('initYexiBookshelf falls back to stale cache or degrades silently on index fetch failure', async () => {
  const now = 1_700_000_000_000;
  const staleStorage = createMemoryStorage({
    [yexi.CACHE_KEY]: JSON.stringify({
      fetchedAt: now - (yexi.CACHE_TTL_MS + 60_000),
      codes: ['001046'],
    }),
  });
  const staleSlot = createSlot('list', '', '00104601');
  const staleCount = await yexi.initYexiBookshelf(createFakeDocument([staleSlot]), {
    now: () => now,
    storage: staleStorage,
    fetch: async () => {
      throw new Error('network down');
    },
  });
  assert.equal(staleCount, 1);
  assert.equal(staleSlot.style.display, '');

  const emptySlot = createSlot('detail', '', '00104601');
  const emptyCount = await yexi.initYexiBookshelf(createFakeDocument([emptySlot]), {
    now: () => now,
    storage: createMemoryStorage(),
    fetch: async () => ({ ok: false, status: 503 }),
  });
  assert.equal(emptyCount, 0);
  assert.equal(emptySlot.style.display, 'none');
});
