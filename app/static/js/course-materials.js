/*
 * USTC Icourse Helper v1.5.3, adapted for native course pages on 2026-11-16.
 * Source: https://github.com/quantai1314/ustc-icourse-helper (f7c7e3c)
 * Based on PRO's USTC Helper (GPL-3.0) icourse module.
 * SPDX-License-Identifier: GPL-3.0-only
 * See licenses/ustc-icourse-helper-GPL-3.0.txt. Combination with the
 * AGPLv3 application is permitted by GPL-3.0 section 13.
 */
(function () {
    'use strict';

    const sideBar = document.querySelector('div.col-md-4.rl-pd-lg');
    const courseId = (location.pathname.match(/^\/course\/(\d+)\/?$/) || [])[1];
    if (!courseId || !sideBar || document.getElementById('ustc-icourse-helper')) return;

    const reviewSel = 'div.review div.review-content';

    function dedupe(items) {
        const seen = new Set();
        return items.filter(it => {
            if (it.href === null) return true;
            const key = it.href || it.name;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    function collectFromDoc(doc, withEle) {
        const files = [];
        const links = [];
        for (const a of doc.querySelectorAll(`${reviewSel} a[href]`)) {
            if (a.getAttribute('data-target') === '#signin') {
                files.push({ name: a.textContent.trim(), href: null, ele: withEle ? a : null });
                continue;
            }
            const rawHref = a.getAttribute('href');
            let url;
            try {
                url = new URL(rawHref, location.origin);
            } catch (e) {
                continue;
            }
            if (url.protocol !== 'http:' && url.protocol !== 'https:') continue;
            if (url.origin !== 'null' && url.origin === location.origin && url.pathname.startsWith('/uploads/files/')) {
                files.push({
                    name: a.textContent.trim(),
                    href: url.pathname + url.search + url.hash,
                    ele: withEle ? a : null,
                });
            } else if (/^https?:\/\//i.test(rawHref) || url.origin !== location.origin) {
                links.push({ name: a.textContent.trim() || url.href, href: url.href, ele: withEle ? a : null });
            }
        }
        return { files: dedupe(files), links: dedupe(links) };
    }

    const local = collectFromDoc(document, true);
    const otherBlockTitle = Array.from(sideBar.querySelectorAll('h4'))
        .find(h => h.textContent.includes('其他老师'));
    const teachers = otherBlockTitle ? Array.from(new Map(
        Array.from(otherBlockTitle.parentElement.querySelectorAll('a[href^="/course/"]'))
            .filter(a => a.getAttribute('href').replace(/\/$/, '') !== `/course/${courseId}`)
            .map(a => [a.getAttribute('href'), { name: a.textContent.trim(), href: a.getAttribute('href') }])
    ).values()) : [];

    function flash(ele) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        ele.animate([
            { backgroundColor: '#fff0ad' }, { backgroundColor: 'transparent' }
        ], { duration: 1600 });
    }

    const style = document.head.appendChild(document.createElement('style'));
    style.id = 'ustc-icourse-helper-style';
    style.textContent = `
#ustc-icourse-helper { --uih-blue: #28679c; --uih-muted: #596b7a; --uih-line: #dce5ed; position: fixed; right: 0; top: 40%; z-index: 10000; color: #243746; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; text-align: left; }
#ustc-icourse-helper :where(dialog, header, footer, div, ul, li, a, button, input, p, h2, span) { box-sizing: border-box; }
#ustc-icourse-helper [hidden] { display: none !important; }
#ustc-icourse-helper button { font: inherit; cursor: pointer; min-height: 34px; border: 1px solid var(--uih-line); border-radius: 6px; background: #fff; color: var(--uih-blue); padding: 5px 10px; }
#ustc-icourse-helper button:hover:not(:disabled) { background: #edf4fa; }
#ustc-icourse-helper :is(a, button, input):focus-visible { outline: 2px solid var(--uih-blue); outline-offset: 2px; }
#ustc-icourse-helper #uih-tab { width: 42px; padding: 10px 5px; border: 0; border-radius: 8px 0 0 8px; background: var(--uih-blue); color: #fff; box-shadow: 0 2px 8px #20364d26; }
#uih-tab span { display: block; font-size: 12px; margin-top: 4px; }
#uih-hint { position: absolute; right: 52px; top: 0; width: max-content; margin: 0; padding: 8px 12px; background: #fff; border: 1px solid var(--uih-line); border-radius: 8px; box-shadow: 0 2px 8px #20364d20; color: var(--uih-blue); }
#uih-panel { position: fixed; right: 54px; left: auto; top: 50%; transform: translateY(-50%); width: 368px; max-width: calc(100vw - 68px); max-height: min(720px, calc(100vh - 32px)); max-height: min(720px, calc(100dvh - 32px)); margin: 0; padding: 0; flex-direction: column; background: #fff; color: #243746; border: 1px solid var(--uih-line); border-radius: 12px; box-shadow: 0 8px 32px #20364d26; overflow: hidden; }
#uih-panel[open] { display: flex; }
#uih-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px 8px; flex: none; }
#uih-title { margin: 0; font-family: inherit; font-size: 17px; font-weight: 600; line-height: 1.5; color: #243746; }
#ustc-icourse-helper #uih-close { min-width: 36px; min-height: 36px; padding: 0; font-size: 22px; color: var(--uih-muted); border-color: transparent; }
#uih-tools { padding: 0 14px 10px; flex: none; border-bottom: 1px solid var(--uih-line); }
#uih-filters { display: flex; gap: 6px; margin-bottom: 10px; }
#uih-filters button { flex: 1; padding-inline: 4px; white-space: nowrap; }
#uih-filters button[aria-pressed="true"] { background: #eaf3fb; border-color: var(--uih-blue); font-weight: 600; }
#uih-search-row { display: flex; gap: 6px; align-items: center; }
#uih-search { width: 100%; min-width: 0; height: 36px; border: 1px solid #aebfcd; border-radius: 6px; padding: 6px 9px; background: #fff; color: #243746; font: inherit; }
#uih-search::placeholder { color: var(--uih-muted); }
#uih-clear { flex: none; }
#uih-summary { margin: 7px 0 0; color: var(--uih-muted); font-size: 12px; }
#uih-body { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 0 14px; }
#uih-list { margin: 0; padding: 0; list-style: none; }
#uih-list .uih-item { padding: 11px 0; }
#uih-list .uih-item + .uih-item { border-top: 1px solid #edf1f5; }
#uih-list .uih-link { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; overflow-wrap: anywhere; color: var(--uih-blue); text-decoration: none; line-height: 1.55; min-height: 24px; }
#uih-list a:hover { text-decoration: underline; }
#uih-list .uih-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; margin-top: 5px; color: var(--uih-muted); font-size: 12px; }
#uih-list .uih-kind { background: #f0f4f7; border-radius: 4px; padding: 1px 5px; }
#uih-list .uih-teacher { color: var(--uih-muted); min-height: 24px; display: inline-flex; align-items: center; overflow-wrap: anywhere; }
#uih-list .uih-loc { margin-left: auto; font-size: 12px; min-height: 32px; padding: 3px 9px; }
#uih-empty { margin: 0; padding: 28px 4px; color: var(--uih-muted); text-align: center; }
#uih-foot { padding: 10px 14px 12px; flex: none; border-top: 1px solid var(--uih-line); background: #f8fafc; }
#uih-status { margin: 0; color: var(--uih-muted); font-size: 12px; overflow-wrap: anywhere; }
#uih-status.uih-warning { color: #92520a; }
#ustc-icourse-helper #uih-more { width: 100%; margin-top: 8px; border-color: var(--uih-blue); background: var(--uih-blue); color: #fff; }
#ustc-icourse-helper #uih-more:hover:not(:disabled) { background: #205580; }
#ustc-icourse-helper #uih-more:disabled { background: #e9eef3; border-color: #dce5ed; color: #596b7a; cursor: default; }
#ustc-icourse-helper .uih-sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
@media (max-width: 480px) {
    #uih-panel { right: 12px; left: 12px; width: auto; max-width: none; max-height: calc(100vh - 24px); max-height: calc(100dvh - 24px); }
    #ustc-icourse-helper.uih-open #uih-tab { visibility: hidden; }
}
@media (pointer: coarse) {
    #ustc-icourse-helper :is(button, #uih-close, #uih-search, .uih-loc, .uih-teacher, .uih-link) { min-height: 44px; }
}
`;

    const root = document.body.appendChild(document.createElement('div'));
    root.id = 'ustc-icourse-helper';
    root.innerHTML =
        `<button id="uih-tab" type="button" aria-expanded="false" aria-controls="uih-panel">资料<span>0</span></button>` +
        `<p id="uih-hint" hidden>课程资料在这里</p>` +
        `<dialog id="uih-panel" aria-labelledby="uih-title">` +
        `<header id="uih-head"><h2 id="uih-title">课程资料</h2><button id="uih-close" type="button" aria-label="收起课程资料" title="收起（Esc）">×</button></header>` +
        `<div id="uih-tools"><div id="uih-filters" role="group" aria-label="资料类型">` +
        `<button type="button" data-filter="all" aria-pressed="true">全部 0</button>` +
        `<button type="button" data-filter="files" aria-pressed="false">文件 0</button>` +
        `<button type="button" data-filter="links" aria-pressed="false">链接 0</button></div>` +
        `<div id="uih-search-row"><label class="uih-sr-only" for="uih-search">搜索文件名或链接</label>` +
        `<input id="uih-search" type="search" placeholder="搜索文件名或链接" autocomplete="off">` +
        `<button id="uih-clear" type="button" hidden>清空</button></div><p id="uih-summary"></p></div>` +
        `<div id="uih-body"><ul id="uih-list" role="list"></ul><p id="uih-empty" hidden></p></div>` +
        `<footer id="uih-foot"><p id="uih-status" role="status" aria-live="polite" aria-atomic="true"></p>` +
        `<button id="uih-more" type="button">搜集其他老师资料</button></footer></dialog>`;

    const tab = root.querySelector('#uih-tab');
    const panel = root.querySelector('#uih-panel');
    const closeBtn = root.querySelector('#uih-close');
    const search = root.querySelector('#uih-search');
    const clearBtn = root.querySelector('#uih-clear');
    const list = root.querySelector('#uih-list');
    const empty = root.querySelector('#uih-empty');
    const status = root.querySelector('#uih-status');
    const moreBtn = root.querySelector('#uih-more');
    const state = { files: [...local.files], links: [...local.links], filter: 'all' };
    const itemRows = new WeakMap();

    function addRow(item, downloadable) {
        const row = document.createElement('li');
        itemRows.set(item, row);
        row.className = 'uih-item';
        const a = row.appendChild(document.createElement('a'));
        a.className = 'uih-link';
        a.textContent = item.name;
        if (item.href) {
            a.href = item.href;
            a.target = '_blank';
            a.rel = 'noopener';
            a.title = item.name;
            if (downloadable) {
                const ext = item.href.split('.').pop();
                if (item.name.toLowerCase().endsWith(ext.toLowerCase())) a.download = item.name;
            }
        } else {
            a.href = '#';
            a.setAttribute('data-toggle', 'modal');
            a.setAttribute('data-target', '#signin');
            a.title = item.name + '（登录后可下载）';
            a.addEventListener('click', () => setOpen(false, false));
        }
        const meta = row.appendChild(document.createElement('div'));
        meta.className = 'uih-meta';
        const kind = meta.appendChild(document.createElement('span'));
        kind.className = 'uih-kind';
        kind.textContent = downloadable ? ((item.name.match(/\.([a-z0-9]{1,8})$/i) || [])[1] || '文件').toUpperCase() : '链接';
        if (!item.href) {
            const note = meta.appendChild(document.createElement('span'));
            note.textContent = '登录后下载';
        }
        if (item.teacher) {
            const t = meta.appendChild(document.createElement('a'));
            t.className = 'uih-teacher';
            t.textContent = item.teacher;
            t.href = item.teacherHref;
            t.target = '_blank';
            t.rel = 'noopener';
            t.title = `前往 ${item.teacher} 老师的课程页`;
        } else {
            meta.appendChild(document.createElement('span')).textContent = '本页点评';
        }
        if (item.ele || item.teacherHref) {
            const loc = meta.appendChild(document.createElement('button'));
            loc.type = 'button';
            loc.className = 'uih-loc';
            loc.textContent = '定位';
            loc.title = item.ele ? '定位到原点评' : `前往 ${item.teacher} 老师的课程页定位原点评`;
            loc.setAttribute('aria-label', `定位：${item.name}`);
            loc.addEventListener('click', () => {
                if (item.ele) {
                    if (window.matchMedia('(max-width: 480px)').matches) setOpen(false);
                    item.ele.scrollIntoView({ block: 'center' });
                    setTimeout(() => flash(item.ele), 300);
                    return;
                }
                const url = new URL(item.teacherHref, location.href);
                url.hash = new URLSearchParams({
                    'uih-locate': downloadable ? 'files' : 'links',
                    'uih-name': item.name,
                    'uih-href': item.href || '',
                    'uih-source': courseId,
                    'uih-filter': state.filter,
                    'uih-query': search.value,
                });
                window.open(url.href, '_blank', 'noopener');
            });
        }
        return row;
    }

    function render(locateTarget = null) {
        const total = state.files.length + state.links.length;
        tab.querySelector('span').textContent = total;
        tab.setAttribute('aria-label', `课程资料，共 ${total} 项`);
        const labels = { all: `全部 ${total}`, files: `文件 ${state.files.length}`, links: `链接 ${state.links.length}` };
        root.querySelectorAll('[data-filter]').forEach(btn => {
            btn.textContent = labels[btn.dataset.filter];
            btn.setAttribute('aria-pressed', String(btn.dataset.filter === state.filter));
        });
        const query = search.value.trim().toLocaleLowerCase();
        const fragment = document.createDocumentFragment();
        let count = 0;
        for (const type of ['files', 'links']) {
            if (state.filter !== 'all' && state.filter !== type) continue;
            for (const item of state[type]) {
                if (item !== locateTarget && query && !`${item.name} ${item.teacher || '本页点评'} ${item.href || ''}`.toLocaleLowerCase().includes(query)) continue;
                fragment.appendChild(addRow(item, type === 'files'));
                count++;
            }
        }
        list.replaceChildren(fragment);
        clearBtn.hidden = !search.value;
        empty.hidden = count > 0;
        empty.textContent = query ? '没有匹配的资料，试试其他关键词或清空搜索。' :
            !total ? (teachers.length ? '本页暂无资料，可以搜集其他老师的同课程资料。' : '本页暂未发现文件或链接。') :
            state.filter === 'files' ? '暂无文件，可以切换到链接或搜集其他老师资料。' : '暂无链接，可以切换到文件查看资料。';
        root.querySelector('#uih-summary').textContent = query ? `找到 ${count} 项 · 共 ${total} 项资料` : `显示 ${count} 项资料`;
    }

    root.querySelectorAll('[data-filter]').forEach(btn => btn.addEventListener('click', () => {
        state.filter = btn.dataset.filter;
        render();
        root.querySelector('#uih-body').scrollTop = 0;
    }));
    search.addEventListener('input', render);
    clearBtn.addEventListener('click', () => {
        search.value = '';
        render();
        search.focus();
    });
    render();

    let restoreCollected = () => {};
    if (!teachers.length) {
        moreBtn.hidden = true;
        status.textContent = '本页未列出其他老师的同课程页面。';
    } else {
        status.textContent = `还可搜集 ${teachers.length} 位老师的同课程资料。`;
        const cacheScope = document.currentScript?.dataset.cacheScope || 'anonymous';
        const cacheKey = `ustc-icourse-xc:${courseId}:${cacheScope}`;
        const collected = new Map();
        let loadedCache = false;
        let busy = false;
        const pageQuery = new URLSearchParams(location.search);
        const hasReviewFilter = pageQuery.has('term') || pageQuery.has('rating');
        const normHref = href => href.replace(/\/$/, '');
        const plain = items => items.map(({ name, href }) => ({ name, href }));
        function readCache(key = cacheKey) {
            try {
                const c = JSON.parse(localStorage.getItem(key));
                if (c?.version !== 3 || c.date !== new Date().toDateString() || !Array.isArray(c.pages)) return;
                for (const page of c.pages) {
                    const teacher = teachers.find(t => normHref(t.href) === normHref(page.href));
                    if (!teacher || !Array.isArray(page.files) || !Array.isArray(page.links)) continue;
                    const validFile = f => f && typeof f.name === 'string' && (f.href === null || (typeof f.href === 'string' && f.href.startsWith('/uploads/files/')));
                    const validLink = l => l && typeof l.name === 'string' && typeof l.href === 'string' && /^https?:\/\//i.test(l.href);
                    if (page.files.every(validFile) && page.links.every(validLink)) {
                        collected.set(teacher.href, { href: teacher.href, files: plain(page.files), links: plain(page.links) });
                    }
                }
            } catch (e) { /* damaged cache is ignored */ }
        }

        function merge() {
            state.files = [...local.files];
            state.links = [...local.links];
            for (const teacher of teachers) {
                const page = collected.get(teacher.href);
                if (!page) continue;
                for (const type of ['files', 'links']) {
                    state[type].push(...page[type].map(item => ({ ...item, teacher: teacher.name, teacherHref: teacher.href })));
                }
            }
            render();
        }

        function loadCache(key = cacheKey) {
            readCache(key);
            loadedCache = true;
            merge();
        }
        function writeCache() {
            try {
                const pages = [...collected.values()].filter(p => normHref(p.href) !== `/course/${courseId}`);
                if (!hasReviewFilter) {
                    pages.push({ href: `/course/${courseId}/`, files: plain(local.files), links: plain(local.links) });
                }
                localStorage.setItem(cacheKey, JSON.stringify({ version: 3, date: new Date().toDateString(), pages }));
            } catch (e) { /* collection remains usable when storage is unavailable */ }
        }
        restoreCollected = sourceCourseId => {
            readCache(`ustc-icourse-xc:${sourceCourseId}:${cacheScope}`);
            merge();
            search.placeholder = '搜索文件名、链接或老师';
            root.querySelector('label[for="uih-search"]').textContent = search.placeholder;
            const remaining = teachers.length - collected.size;
            if (collected.size) {
                writeCache();
                moreBtn.textContent = remaining ? `继续搜集其余 ${remaining} 位老师` : '搜集完成';
                moreBtn.disabled = !remaining;
                status.textContent = '已恢复来源页的今日缓存，未重新搜集。';
            } else {
                moreBtn.textContent = '搜集其他老师资料';
                moreBtn.disabled = false;
                status.textContent = '来源页暂无可恢复的今日缓存，可点击搜集。';
            }
        };

        moreBtn.addEventListener('click', async () => {
            if (busy) return;
            busy = true;
            search.placeholder = '搜索文件名、链接或老师';
            root.querySelector('label[for="uih-search"]').textContent = search.placeholder;
            moreBtn.disabled = true;
            moreBtn.textContent = '正在搜集…';
            status.classList.remove('uih-warning');
            if (!loadedCache) loadCache();
            const queue = teachers.filter(t => !collected.has(t.href));
            const fromCache = !queue.length;
            let done = collected.size;
            status.textContent = `已检查 ${done}/${teachers.length} 位老师…`;
            const run = async teacher => {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 15000);
                try {
                    const response = await fetch(teacher.href, { signal: controller.signal });
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
                    if (!doc.querySelector('div.col-md-4.rl-pd-lg')) throw new Error('not a course page');
                    const data = collectFromDoc(doc, false);
                    collected.set(teacher.href, { href: teacher.href, files: data.files, links: data.links });
                } catch (e) {
                    // The summary identifies failed teachers and offers an explicit retry.
                } finally {
                    clearTimeout(timeout);
                    status.textContent = `已检查 ${++done}/${teachers.length} 位老师…`;
                }
            };
            try {
                await Promise.all(Array.from({ length: Math.min(4, queue.length) }, async () => {
                    while (queue.length) await run(queue.shift());
                }));
            } finally {
                busy = false;
                merge();
                const failed = teachers.length - collected.size;
                const files = state.files.length - local.files.length;
                const links = state.links.length - local.links.length;
                status.classList.toggle('uih-warning', failed > 0);
                status.textContent = failed ? `已获取 ${collected.size} 位老师的资料，${failed} 位未成功。已找到 ${files} 个文件、${links} 个链接。` :
                    `已检查 ${teachers.length} 位老师，${files + links ? `找到 ${files} 个文件、${links} 个链接。` : '暂未发现其他资料。'}${fromCache ? '（今日缓存）' : ''}`;
                moreBtn.textContent = failed ? `重试失败的 ${failed} 位老师` : '搜集完成';
                moreBtn.disabled = !failed;
                writeCache();
            }
        });
    }

    function setOpen(open, focus = true) {
        if (open !== panel.open) {
            if (open) panel.show();
            else panel.close();
        }
        root.classList.toggle('uih-open', open);
        tab.setAttribute('aria-expanded', String(open));
        root.querySelector('#uih-hint').hidden = true;
        if (focus) (open ? closeBtn : tab).focus({ preventScroll: true });
    }
    tab.addEventListener('click', () => setOpen(!panel.open));
    closeBtn.addEventListener('click', () => setOpen(false));
    root.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !event.isComposing && panel.open) {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
        }
    });

    const locateParams = new URLSearchParams(location.hash.slice(1));
    const locateType = locateParams.get('uih-locate');
    if (locateType === 'files' || locateType === 'links') {
        history.replaceState(null, '', location.pathname + location.search);
        const sourceCourseId = locateParams.get('uih-source');
        if (/^\d+$/.test(sourceCourseId || '')) restoreCollected(sourceCourseId);
        const filter = locateParams.get('uih-filter');
        if (['all', 'files', 'links'].includes(filter)) state.filter = filter;
        search.value = locateParams.get('uih-query') || '';
        const name = locateParams.get('uih-name');
        const href = locateParams.get('uih-href') || '';
        const target = state[locateType].find(item => item.name === name && (item.href || '') === href);
        render(target);
        setOpen(true, false);
        if (target?.ele) {
            const targetRow = itemRows.get(target);
            if (targetRow?.isConnected) {
                targetRow.scrollIntoView({ behavior: 'instant', block: 'center' });
                flash(targetRow);
            }
            target.ele.scrollIntoView({ block: 'center' });
            setTimeout(() => flash(target.ele), 300);
        } else {
            status.classList.add('uih-warning');
            status.textContent = '未找到要定位的原点评，页面内容可能已更新。';
        }
    }

    try {
        if (!localStorage.getItem('ustc-icourse-hint-seen')) {
            root.querySelector('#uih-hint').hidden = false;
            localStorage.setItem('ustc-icourse-hint-seen', '1');
            setTimeout(() => { root.querySelector('#uih-hint').hidden = true; }, 6000);
        }
    } catch (e) { /* storage is optional */ }
})();
