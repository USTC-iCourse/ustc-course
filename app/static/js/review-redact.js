/*
 * Paint the admin-drawn black marker over a review.
 *
 * Everyone sees the same thing, admins included -- moderation happens on
 * /review/<id>/redact/, never on the page people read.  So this file has one
 * job and no branches: find the quoted strings and cover them.
 *
 * Matching is by text, not by offset.  A redaction stores the string an admin
 * highlighted, so the mask keeps landing correctly after the author prepends a
 * paragraph, fixes a typo, or bolds a character mid-word -- there is no
 * position for an edit to invalidate.  The plain text walked here is the
 * concatenation of the text nodes in document order, which is exactly what
 * app/redaction.py's html_to_text() produces on the server; the two have to
 * agree for the offsets stored alongside a redaction to mean anything.
 *
 * Containers carrying a redaction render hidden (.review-redact-pending) and
 * are revealed once masked.  That fails closed: with JavaScript off, or if this
 * file throws, a redacted review stays blank rather than showing what an admin
 * covered.
 */
(function () {
  'use strict';

  var MASK_CHAR = '█';
  var MASK_TITLE = '本点评存在违反社区规范的内容，予以部分屏蔽';
  // Below this length a trailing partial match is more likely a coincidence
  // than a truncated quote, so leave short tails alone.
  var MIN_PARTIAL_TAIL = 2;

  function collectTextNodes(root) {
    // Skip what a reader would not see.  sanitize() already strips both tags,
    // but html_to_text() drops them too and the two walks must not diverge.
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var parent = node.parentNode;
        if (parent && (parent.nodeName === 'SCRIPT' || parent.nodeName === 'STYLE')) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    }, false);

    var nodes = [];
    var text = '';
    var node;
    while ((node = walker.nextNode())) {
      nodes.push({ node: node, start: text.length });
      text += node.data;
    }
    return { nodes: nodes, text: text };
  }

  function occurrencesOf(text, quote) {
    var found = [];
    var index = text.indexOf(quote);
    while (index >= 0) {
      found.push(index);
      // Step by one rather than by the quote length: masking "aa" inside "aaa"
      // should cover all three characters, not leave a bare one behind.
      index = text.indexOf(quote, index + 1);
    }
    return found;
  }

  function rangesFor(text, redactions) {
    var ranges = [];

    redactions.forEach(function (redaction) {
      var quote = redaction && redaction.quote;
      if (!quote) {
        return;
      }

      var found = occurrencesOf(text, quote);
      if (found.length && redaction.scope === 'once' && typeof redaction.pos === 'number') {
        var nearest = found[0];
        found.forEach(function (start) {
          if (Math.abs(start - redaction.pos) < Math.abs(nearest - redaction.pos)) {
            nearest = start;
          }
        });
        found = [nearest];
      }
      found.forEach(function (start) {
        ranges.push([start, start + quote.length]);
      });

      // The list pages show an abstract cut to a fixed length, which can slice
      // a quote in half.  Cover the surviving head so the fragment left on
      // screen is not the readable part of what an admin blacked out.
      for (var length = quote.length - 1; length >= MIN_PARTIAL_TAIL; length--) {
        if (text.slice(-length) === quote.slice(0, length)) {
          ranges.push([text.length - length, text.length]);
          break;
        }
      }
    });

    return mergeRanges(ranges);
  }

  function mergeRanges(ranges) {
    if (ranges.length < 2) {
      return ranges;
    }
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [ranges[0]];
    for (var i = 1; i < ranges.length; i++) {
      var last = merged[merged.length - 1];
      if (ranges[i][0] <= last[1]) {
        last[1] = Math.max(last[1], ranges[i][1]);
      } else {
        merged.push(ranges[i]);
      }
    }
    return merged;
  }

  function maskedSpan(length) {
    var span = document.createElement('span');
    span.className = 'review-redacted';
    span.setAttribute('title', MASK_TITLE);
    // Replace the characters rather than recolour them, so selecting the
    // review and copying it does not carry the original text away.
    span.textContent = new Array(length + 1).join(MASK_CHAR);
    return span;
  }

  function applyRanges(nodes, ranges) {
    // Each text node is rebuilt in one shot and swapped out whole.  Splitting
    // in place would shift the offsets of everything after it mid-pass.
    nodes.forEach(function (entry) {
      var node = entry.node;
      var data = node.data;
      var nodeStart = entry.start;
      var nodeEnd = nodeStart + data.length;
      var pieces = [];
      var cursor = 0;

      ranges.forEach(function (range) {
        var from = Math.max(range[0], nodeStart);
        var to = Math.min(range[1], nodeEnd);
        if (from >= to) {
          return;
        }
        var localFrom = from - nodeStart;
        var localTo = to - nodeStart;
        if (localFrom > cursor) {
          pieces.push({ text: data.slice(cursor, localFrom), masked: false });
        }
        pieces.push({ text: data.slice(localFrom, localTo), masked: true });
        cursor = localTo;
      });

      if (!pieces.length) {
        return;
      }
      if (cursor < data.length) {
        pieces.push({ text: data.slice(cursor), masked: false });
      }

      var fragment = document.createDocumentFragment();
      pieces.forEach(function (piece) {
        fragment.appendChild(piece.masked
          ? maskedSpan(piece.text.length)
          : document.createTextNode(piece.text));
      });
      node.parentNode.replaceChild(fragment, node);
    });
  }

  function redactContainer(container, redactions) {
    var collected = collectTextNodes(container);
    var ranges = rangesFor(collected.text, redactions);
    if (ranges.length) {
      applyRanges(collected.nodes, ranges);
    }
  }

  function run() {
    var blobs = document.querySelectorAll('script.review-redaction-data');
    Array.prototype.forEach.call(blobs, function (blob) {
      var reviewId = blob.getAttribute('data-review-id');
      var redactions;
      try {
        redactions = JSON.parse(blob.textContent || '[]');
      } catch (error) {
        // Leave the containers hidden: showing the review unmasked would
        // publish exactly what an admin covered.
        console.error('review-redact: bad payload for review ' + reviewId, error);
        return;
      }

      var targets = document.querySelectorAll('[data-redact-target="' + reviewId + '"]');
      Array.prototype.forEach.call(targets, function (target) {
        try {
          redactContainer(target, redactions);
          target.classList.remove('review-redact-pending');
        } catch (error) {
          console.error('review-redact: failed on review ' + reviewId, error);
        }
      });
    });
  }

  // The masks have to be in place before the reader sees anything, and the
  // containers stay hidden until they are, so run at the first moment the
  // review markup exists rather than waiting for images and stylesheets.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
}());
