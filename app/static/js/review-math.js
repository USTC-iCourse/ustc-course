/*
 * review-math.js
 *
 * Makes multi-line / display LaTeX equations render inside course reviews and
 * comments, for BOTH existing (already-stored) reviews and new ones — without
 * touching the editor or re-processing the database.
 *
 * The rich editor stores an inline formula as a single node,
 *   <span class="math-tex">\( ... \)</span>
 * which MathJax already renders fine. The problem is *display* math written on
 * its own lines, e.g.
 *
 *     \[
 *     m_{H}^{2} \leq m_{H}^{2}(\Lambda) - \frac{3}{2\pi^{2}v^{2}}(...)\Lambda^{2}
 *     \]
 *
 * When this is typed/pasted into the editor the three lines become three
 * separate <p> blocks, so the stored HTML is roughly
 *     <p>\[</p><p>m_{H}^{2} \leq ...</p><p>\]</p>
 * MathJax v3 will NOT pair a \[ in one block with a \] in another block, so the
 * equation never renders.
 *
 * normalizeReviewMath() walks each review/comment container, finds every
 * display region ( \[ ... \] or $$ ... $$ ) that may span several block
 * elements, and flattens it into a single uninterrupted delimiter that MathJax
 * can pick up. Inline \( ... \) formulas are left untouched.
 */
(function () {
  'use strict';

  // A display region may have block tags in the middle (the split paragraphs).
  // Turn those back into plain text so the equation is one contiguous string.
  // Only tags are removed — the LaTeX source (including "\\" row separators for
  // align/aligned environments) is preserved verbatim.
  function flattenMathBody(body) {
    return body
      .replace(/<\s*br\s*\/?\s*>/gi, '\n')            // <br>        -> newline
      .replace(/<\/\s*(?:p|div|h[1-6])\s*>/gi, '\n')  // end of block -> newline
      .replace(/<\s*(?:p|div|h[1-6])[^>]*>/gi, '')    // start of block -> drop
      .replace(/<[^>]+>/g, '')                         // any stray tag -> drop
      .replace(/&nbsp;/gi, ' ');
  }

  function isEmpty(s) {
    return s.replace(/\s| /g, '').length === 0;
  }

  // "Bare bracket" display math: a line that is only "[", one or more non-empty
  // lines, then a line that is only "]".  Some authors use this instead of
  // \[ ... \].  Because the brackets must sit ALONE on their own line (their own
  // <p> block, or between <br> breaks), this does not fire on ordinary text that
  // merely contains brackets.
  //
  //   ws  = optional whitespace / &nbsp;
  //   the [ and ] must be the entire content of their line.
  function convertBareBracket(html, state) {
    var ws = '(?:\\s|&nbsp;)*';

    // Form A: each bracket is its own <p>/<div> block:  <p>[</p> ... <p>]</p>
    var blockForm = new RegExp(
      '<(?:p|div)[^>]*>' + ws + '\\[' + ws + '</(?:p|div)>' +
      '([\\s\\S]*?)' +
      '<(?:p|div)[^>]*>' + ws + '\\]' + ws + '</(?:p|div)>',
      'gi'
    );
    html = html.replace(blockForm, function (m, inner) {
      var body = flattenMathBody(inner);
      if (isEmpty(body)) { return m; }   // need at least one non-empty line
      state.changed = true;
      return '<span class="math-display">\\[' + body + '\\]</span>';
    });

    // Form B: brackets sit alone on <br>-separated lines within one block:
    //   [<br> ... <br>]   bounded by a block edge or another <br>.
    var brForm = new RegExp(
      '(<p[^>]*>|<div[^>]*>|<br\\s*/?>|^)' + ws + '\\[' + ws + '<br\\s*/?>' +
      '([\\s\\S]*?)' +
      '<br\\s*/?>' + ws + '\\]' + ws +
      '(?=</p>|</div>|<br\\s*/?>|$)',
      'gi'
    );
    html = html.replace(brForm, function (m, lead, inner) {
      var body = flattenMathBody(inner);
      if (isEmpty(body)) { return m; }
      state.changed = true;
      return lead + '<span class="math-display">\\[' + body + '\\]</span>';
    });

    return html;
  }

  function normalize(root) {
    var scope = (root && root.querySelectorAll) ? root : document;
    var containers = scope.querySelectorAll('.review-content, .ck-content');

    for (var i = 0; i < containers.length; i++) {
      var el = containers[i];
      var html = el.innerHTML;

      // Fast bail-out: nothing that looks like display math.
      if (html.indexOf('[') === -1 && html.indexOf('$$') === -1) {
        continue;
      }

      var state = { changed: false };

      // \[ ... \]  (non-greedy so adjacent equations don't merge)
      html = html.replace(/\\\[([\s\S]*?)\\\]/g, function (_m, inner) {
        state.changed = true;
        return '<span class="math-display">\\[' + flattenMathBody(inner) + '\\]</span>';
      });

      // $$ ... $$
      html = html.replace(/\$\$([\s\S]*?)\$\$/g, function (_m, inner) {
        state.changed = true;
        return '<span class="math-display">$$' + flattenMathBody(inner) + '$$</span>';
      });

      // Bare-bracket display math ( [ / ] alone on their own lines ).
      // Runs last: it emits \[ ... \] spans that must not be re-processed above.
      html = convertBareBracket(html, state);

      if (state.changed) {
        el.innerHTML = html;
      }
    }
  }

  // Normalize the whole page. Called from MathJax's pageReady (see layout.html)
  // before the initial typeset.
  window.normalizeReviewMath = normalize;

  // Normalize + (re)typeset a freshly inserted subtree, e.g. AJAX-loaded
  // comments. Safe to call before MathJax has finished loading.
  window.typesetReviewMath = function (root) {
    normalize(root);
    if (window.MathJax && window.MathJax.typesetPromise) {
      var nodes = (root && root.nodeType) ? [root] : undefined;
      return window.MathJax.typesetPromise(nodes).catch(function (e) {
        console.error('MathJax typeset failed', e);
      });
    }
  };
})();
