const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const origin = 'https://icourse.club';
const scriptPath = path.join(__dirname, '..', 'app', 'static', 'js', 'course-materials.js');
const teacherNames = { 101: '甲老师', 102: '乙老师', 103: '丙老师' };
const defaultReviews = {
    101: review(1, '<a href="/uploads/files/a.pdf">A 资料.pdf</a><a href="https://example.com/a">课程官网</a>'),
    102: review(2, '<a href="/uploads/files/b.pdf">B 资料.pdf</a><a href="https://example.com/b">B 参考</a>'),
    103: review(3, '<a href="/uploads/files/c.pdf">C 资料.pdf</a>'),
};

function review(id, content) {
    return `<div class="ud-pd-md dashed review" id="review-${id}"><div class="review-content ck-content" id="review-content-${id}"><p>${content}</p></div></div>`;
}

function courseHtml(id, reviews, anonymous, cacheScope) {
    const teachers = Object.keys(teacherNames)
        .map(Number)
        .filter(teacherId => teacherId !== id)
        .map(teacherId => `<div class="ud-pd-sm"><a href="/course/${teacherId}/">${teacherNames[teacherId]}</a></div>`)
        .join('');
    return `<!doctype html><html><head><meta charset="utf-8"><title>课程 ${id}</title>
        <style>body{min-height:1800px}.review-content{min-height:80px}</style></head><body>
        <main>
        <div class="showmore-text ck-content review-content" id="course-intro"><a href="/uploads/files/intro.pdf">简介附件.pdf</a><a href="https://example.com/intro">简介链接</a></div>
        <div class="showmore-text ck-content review-content" id="course-summary"><a href="https://example.com/summary">AI 总结链接</a></div>
        <div class="review-content"><a href="https://example.com/admin">管理员公告链接</a></div>
        ${reviews[id] || ''}
        </main>
        <div class="col-md-4 rl-pd-lg"><div class="ud-pd-md dashed"><h4 class="blue">其他老师的「示例课程」课</h4>${teachers}</div></div>
        ${anonymous ? '<div class="modal fade" id="signin"></div>' : ''}
        <script src="/static/js/course-materials.js" data-cache-scope="${cacheScope}"></script></body></html>`;
}

async function makeHarness(browser, options = {}) {
    const context = await browser.newContext({
        viewport: options.viewport || { width: 1280, height: 900 },
        reducedMotion: options.reducedMotion || 'no-preference',
    });
    const reviews = { ...defaultReviews, ...(options.reviews || {}) };
    const session = { cacheScope: options.cacheScope || (options.anonymous ? 'anonymous' : 'user:1:Student:0') };
    const served = [];
    const attempts = {};
    await context.route(`${origin}/**`, async route => {
        const url = new URL(route.request().url());
        if (url.pathname === '/static/js/course-materials.js') {
            await route.fulfill({
                contentType: 'application/javascript; charset=utf-8',
                body: fs.existsSync(scriptPath) ? fs.readFileSync(scriptPath, 'utf8') : '',
            });
            return;
        }
        const match = url.pathname.match(/^\/course\/(\d+)\/$/);
        if (!match) {
            await route.fulfill({ status: 404, body: 'not found' });
            return;
        }
        const id = Number(match[1]);
        served.push(id);
        attempts[id] = (attempts[id] || 0) + 1;
        if (options.failOnce === id && attempts[id] === 1) {
            await route.fulfill({ status: 500, body: 'forced failure' });
            return;
        }
        const filtered = url.searchParams.has('term') || url.searchParams.has('rating');
        const visibleReviews = filtered ? { ...reviews, ...(options.filteredReviews || {}) } : reviews;
        await route.fulfill({
            contentType: 'text/html; charset=utf-8',
            body: courseHtml(id, visibleReviews, options.anonymous, session.cacheScope),
        });
    });
    const page = await context.newPage();
    return { context, page, reviews, session, served, attempts };
}

async function openPanel(page, id = 101, query = '') {
    await page.goto(`${origin}/course/${id}/${query}`);
    await page.waitForSelector('#ustc-icourse-helper', { timeout: 2500 });
    await page.locator('#uih-tab').click();
    await page.locator('#uih-panel').waitFor({ state: 'visible' });
}

const tests = [];
function test(name, run) {
    tests.push({ name, run });
}

test('collects files and links only from real reviews', async browser => {
    const h = await makeHarness(browser);
    try {
        await openPanel(h.page);
        assert.deepEqual(await h.page.locator('.uih-link').allTextContents(), ['A 资料.pdf', '课程官网']);
        assert.deepEqual(await h.page.locator('[data-filter]').allTextContents(), ['全部 2', '文件 1', '链接 1']);
        assert.equal(await h.page.locator('.uih-link', { hasText: '简介附件.pdf' }).count(), 0);
        assert.equal(await h.page.locator('.uih-link', { hasText: 'AI 总结链接' }).count(), 0);
        assert.equal(await h.page.locator('.uih-link', { hasText: '管理员公告链接' }).count(), 0);
    } finally {
        await h.context.close();
    }
});

test('filters and searches collected materials', async browser => {
    const h = await makeHarness(browser);
    try {
        await openPanel(h.page);
        await h.page.locator('[data-filter="links"]').click();
        assert.deepEqual(await h.page.locator('.uih-link').allTextContents(), ['课程官网']);
        assert.equal(await h.page.locator('[data-filter="links"]').getAttribute('aria-pressed'), 'true');
        await h.page.locator('#uih-search').fill('不存在的资料');
        assert.equal(await h.page.locator('.uih-link').count(), 0);
        assert.equal(await h.page.locator('#uih-empty').isVisible(), true);
        await h.page.locator('#uih-clear').click();
        assert.deepEqual(await h.page.locator('.uih-link').allTextContents(), ['课程官网']);
        assert.equal(await h.page.locator('.uih-link').getAttribute('target'), '_blank');
        assert.match(await h.page.locator('.uih-link').getAttribute('rel'), /noopener/);
    } finally {
        await h.context.close();
    }
});

test('keeps anonymous attachments as login-required entries', async browser => {
    const h = await makeHarness(browser, {
        anonymous: true,
        reviews: {
            101: review(1, '<a href="#" data-toggle="modal" data-target="#signin">匿名资料.pdf</a><a href="#" data-toggle="modal" data-target="#signin">匿名表格.numbers</a><a href="#" data-toggle="modal" data-target="#signin">Please login to download the attachment</a><a href="#" data-toggle="modal" data-target="#signin">Please login to download the attachment</a><a href="#" data-toggle="modal" data-target="#signin">下载附件</a><a href="https://example.com/a">课程官网</a>'),
        },
    });
    try {
        await openPanel(h.page);
        const attachment = h.page.locator('.uih-link', { hasText: '匿名资料.pdf' });
        assert.equal(await attachment.getAttribute('data-target'), '#signin');
        assert.match(await attachment.locator('..').textContent(), /登录后下载/);
        assert.deepEqual(await h.page.locator('.uih-link').allTextContents(), [
            '匿名资料.pdf',
            '匿名表格.numbers',
            'Please login to download the attachment',
            'Please login to download the attachment',
            '下载附件',
            '课程官网',
        ]);
        await attachment.click();
        await h.page.locator('#uih-panel').waitFor({ state: 'hidden' });
        assert.equal(await h.page.locator('#uih-tab').getAttribute('aria-expanded'), 'false');
    } finally {
        await h.context.close();
    }
});

test('classifies absolute same-origin attachments and external links by parsed URL', async browser => {
    const h = await makeHarness(browser, {
        reviews: {
            101: review(1, '<a href="https://icourse.club/uploads/files/absolute.pdf">绝对附件.pdf</a><a href="https://example.com/uploads/files/mirror.pdf">外部镜像</a><a href="//example.com/protocol-relative">协议相对链接</a><a href="httpx://example.com/bad">无效协议</a>'),
        },
    });
    try {
        await openPanel(h.page);
        const attachment = h.page.locator('.uih-link', { hasText: '绝对附件.pdf' });
        assert.equal(await attachment.getAttribute('href'), '/uploads/files/absolute.pdf');
        assert.equal(await h.page.locator('.uih-link', { hasText: '外部镜像' }).getAttribute('href'), 'https://example.com/uploads/files/mirror.pdf');
        assert.equal(await h.page.locator('.uih-link', { hasText: '协议相对链接' }).getAttribute('href'), 'https://example.com/protocol-relative');
        assert.equal(await h.page.locator('.uih-link', { hasText: '无效协议' }).count(), 0);
        assert.deepEqual(await h.page.locator('[data-filter]').allTextContents(), ['全部 3', '文件 1', '链接 2']);
    } finally {
        await h.context.close();
    }
});

test('fetches other teachers only on demand and retries failures with cached data preserved', async browser => {
    const h = await makeHarness(browser, { failOnce: 103 });
    try {
        await openPanel(h.page);
        await h.page.waitForLoadState('networkidle');
        assert.deepEqual(h.served, [101]);
        h.served.length = 0;
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-more').textContent.startsWith('重试失败'));
        assert.equal(h.attempts[102], 1);
        assert.equal(h.attempts[103], 1);
        assert.equal(await h.page.locator('.uih-link', { hasText: 'B 资料.pdf' }).count(), 1);
        assert.equal(await h.page.locator('.uih-link', { hasText: 'C 资料.pdf' }).count(), 0);
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-more').textContent === '搜集完成');
        assert.equal(await h.page.locator('.uih-link', { hasText: 'C 资料.pdf' }).count(), 1);
        const cachedPages = await h.page.evaluate(() => JSON.parse(localStorage.getItem('ustc-icourse-xc:101:user:1:Student:0')).pages.map(page => page.href).sort());
        assert.deepEqual(cachedPages, ['/course/101/', '/course/102/', '/course/103/']);
        await h.page.reload();
        await h.page.waitForSelector('#ustc-icourse-helper');
        await h.page.locator('#uih-tab').click();
        h.served.length = 0;
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-status').textContent.includes('今日缓存'));
        assert.deepEqual(h.served, []);
    } finally {
        await h.context.close();
    }
});

test('does not restore collected materials across different user scopes', async browser => {
    const h = await makeHarness(browser, {
        reviews: {
            102: review(2, '<a href="/uploads/files/private.pdf">账号一私密资料.pdf</a>'),
        },
    });
    try {
        await openPanel(h.page);
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-more').textContent === '搜集完成');
        assert.equal(await h.page.locator('.uih-link', { hasText: '账号一私密资料.pdf' }).count(), 1);

        h.reviews[102] = review(2, '<a href="/uploads/files/public.pdf">账号二公开资料.pdf</a>');
        h.session.cacheScope = 'user:2:Student:0';
        await openPanel(h.page);
        h.served.length = 0;
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-more').textContent === '搜集完成');
        assert.equal(await h.page.locator('.uih-link', { hasText: '账号一私密资料.pdf' }).count(), 0);
        assert.equal(await h.page.locator('.uih-link', { hasText: '账号二公开资料.pdf' }).count(), 1);
        assert.equal(h.attempts[102], 2);
        assert.equal(h.attempts[103], 2);
    } finally {
        await h.context.close();
    }
});

test('does not treat a filtered source page as a complete cached course page', async browser => {
    const h = await makeHarness(browser, {
        reviews: {
            101: review(1, '<a href="/uploads/files/a-1.pdf">A 完整资料 1.pdf</a>') +
                review(11, '<a href="/uploads/files/a-2.pdf">A 完整资料 2.pdf</a>'),
        },
        filteredReviews: {
            101: review(1, '<a href="/uploads/files/a-1.pdf">A 完整资料 1.pdf</a>'),
        },
    });
    try {
        await openPanel(h.page, 101, '?term=2026');
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-more').textContent === '搜集完成');
        const opened = h.context.waitForEvent('page');
        await h.page.locator('.uih-item', { hasText: 'B 资料.pdf' }).locator('.uih-loc').click();
        const target = await opened;
        await target.waitForLoadState('load');
        await target.waitForSelector('#ustc-icourse-helper');
        await target.locator('#uih-panel').waitFor({ state: 'visible' });
        assert.equal(await target.locator('#uih-more').textContent(), '继续搜集其余 1 位老师');
        assert.equal(await target.locator('#uih-more').isEnabled(), true);
        await target.locator('#uih-more').click();
        await target.waitForFunction(() => document.querySelector('#uih-more').textContent === '搜集完成');
        assert.equal(await target.locator('.uih-item', { hasText: 'A 完整资料 2.pdf' }).count(), 1);
        assert.equal(await target.locator('.uih-item', { hasText: 'C 资料.pdf' }).count(), 1);
    } finally {
        await h.context.close();
    }
});

test('restores cross-page results and locates both the material row and original review', async browser => {
    const bFiles = Array.from({ length: 30 }, (_, index) => ({
        name: `B 资料 ${String(index + 1).padStart(2, '0')}`,
        href: `/uploads/files/b-${index + 1}.pdf`,
    }));
    const cFiles = Array.from({ length: 30 }, (_, index) => ({
        name: `C 资料 ${String(index + 1).padStart(2, '0')}`,
        href: `/uploads/files/c-${index + 1}.pdf`,
    }));
    const h = await makeHarness(browser, {
        reviews: {
            102: bFiles.map((item, index) => review(200 + index, `<a href="${item.href}">${item.name}</a>`)).join(''),
            103: cFiles.map((item, index) => review(300 + index, `<a href="${item.href}">${item.name}</a>`)).join(''),
        },
    });
    try {
        await h.page.goto(`${origin}/course/101/`);
        await h.page.evaluate(({ bFiles, cFiles }) => {
            localStorage.setItem('ustc-icourse-hint-seen', '1');
            localStorage.setItem('ustc-icourse-xc:101:user:1:Student:0', JSON.stringify({
                version: 3,
                date: new Date().toDateString(),
                pages: [
                    { href: '/course/102/', files: bFiles, links: [] },
                    { href: '/course/103/', files: cFiles, links: [] },
                ],
            }));
        }, { bFiles, cFiles });
        await h.page.reload();
        await h.page.waitForSelector('#ustc-icourse-helper', { timeout: 2500 });
        await h.page.locator('#uih-tab').click();
        await h.page.locator('#uih-more').click();
        await h.page.waitForFunction(() => document.querySelector('#uih-more').textContent === '搜集完成');
        await h.page.locator('[data-filter="files"]').click();
        await h.page.locator('#uih-search').fill('资料');
        h.served.length = 0;
        const opened = h.context.waitForEvent('page');
        await h.page.locator('.uih-item', { hasText: 'B 资料 20' }).locator('.uih-loc').click();
        const target = await opened;
        await target.waitForLoadState('load');
        await target.waitForSelector('#ustc-icourse-helper', { timeout: 2500 });
        await target.locator('#uih-panel').waitFor({ state: 'visible' });
        const restored = await target.evaluate(() => {
            const row = Array.from(document.querySelectorAll('.uih-item')).find(item => item.textContent.includes('B 资料 20') && item.textContent.includes('本页点评'));
            const original = Array.from(document.querySelectorAll('.review .review-content a')).find(a => a.textContent === 'B 资料 20');
            const bodyBox = document.querySelector('#uih-body').getBoundingClientRect();
            const rowBox = row.getBoundingClientRect();
            const originalBox = original.getBoundingClientRect();
            return {
                query: document.querySelector('#uih-search').value,
                filter: document.querySelector('[data-filter="files"]').getAttribute('aria-pressed'),
                rowOffset: Math.abs(rowBox.top + rowBox.height / 2 - bodyBox.top - bodyBox.height / 2),
                rowAnimations: row.getAnimations().length,
                originalOffset: Math.abs(originalBox.top + originalBox.height / 2 - innerHeight / 2),
                cachedRows: Array.from(document.querySelectorAll('.uih-item')).filter(item => item.textContent.includes('C 资料 01')).length,
                status: document.querySelector('#uih-status').textContent,
            };
        });
        assert.equal(restored.query, '资料');
        assert.equal(restored.filter, 'true');
        assert.ok(restored.rowOffset <= 1, `row offset: ${restored.rowOffset}`);
        assert.ok(restored.rowAnimations > 0);
        assert.ok(restored.originalOffset <= 1, `original offset: ${restored.originalOffset}`);
        assert.equal(restored.cachedRows, 1);
        assert.match(restored.status, /已恢复/);
        assert.deepEqual(h.served, [102]);
    } finally {
        await h.context.close();
    }
});

test('keeps disclosure state and keyboard focus synchronized', async browser => {
    const h = await makeHarness(browser);
    try {
        await openPanel(h.page);
        assert.equal(await h.page.locator('#uih-tab').getAttribute('aria-expanded'), 'true');
        assert.equal(await h.page.evaluate(() => document.activeElement.id), 'uih-close');
        await h.page.keyboard.press('Escape');
        await h.page.locator('#uih-panel').waitFor({ state: 'hidden' });
        assert.equal(await h.page.locator('#uih-tab').getAttribute('aria-expanded'), 'false');
        assert.equal(await h.page.evaluate(() => document.activeElement.id), 'uih-tab');
        await h.page.keyboard.press('Enter');
        await h.page.locator('#uih-panel').waitFor({ state: 'visible' });
        assert.equal(await h.page.locator('#uih-tab').getAttribute('aria-expanded'), 'true');
    } finally {
        await h.context.close();
    }
});

test('fits a narrow viewport and honors reduced motion when locating a review', async browser => {
    const h = await makeHarness(browser, {
        viewport: { width: 375, height: 740 },
        reducedMotion: 'reduce',
    });
    try {
        await openPanel(h.page);
        const box = await h.page.locator('#uih-panel').boundingBox();
        assert.ok(box.x >= 0 && box.y >= 0);
        assert.ok(box.x + box.width <= 375.5, `right edge: ${box.x + box.width}`);
        assert.ok(box.y + box.height <= 740.5, `bottom edge: ${box.y + box.height}`);
        await h.page.locator('.uih-loc').first().click();
        await h.page.locator('#uih-panel').waitFor({ state: 'hidden' });
        assert.equal(await h.page.locator("#review-content-1 a[href='/uploads/files/a.pdf']").evaluate(element => element.getAnimations().length), 0);
    } finally {
        await h.context.close();
    }
});

(async () => {
    const browser = await chromium.launch({
        headless: true,
        executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
    });
    let failures = 0;
    for (const { name, run } of tests) {
        try {
            await run(browser);
            console.log(`ok - ${name}`);
        } catch (error) {
            failures++;
            console.error(`not ok - ${name}\n${error.stack}`);
        }
    }
    await browser.close();
    if (failures) process.exitCode = 1;
})();
