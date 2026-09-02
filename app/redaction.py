'''Partial redaction of review text -- the "black marker" an admin draws over a
few offending characters instead of blocking the whole review.

The design has one central decision: **a redaction is stored as the selected
string, not as a character offset.**  Matching by text is immune to every edit
that does not touch the string itself -- the author can prepend a paragraph,
fix a typo, or bold a character (``史<strong>中</strong>史``) and the mask still
lands in the right place, because there is no position to invalidate.

An offset is still kept (``anchor_pos``), but only as a snapshot used for two
narrow jobs:

* picking *which* occurrence to cover when the redaction is scoped to one, and
* diagnosing what happened when the quote disappears after an edit.

That second job is what ``diff_match_patch`` is for, and it is the reason a
plain "is the string still there?" check is not enough.  When the quote is
gone, the two cases look identical from the new text alone:

* the author deleted the offending words  -> nothing left to hide
* the author obfuscated them (史中史 -> 史*中*史) -> an evasion attempt

Diffing the old text against the new one separates them: a span whose
characters were *all* deleted is the first case; a span that survived in pieces
with something spliced into it is the second.  Both mail the admins either way
-- this module only labels what happened, it never hides anything by itself.

Offsets live in **plain-text** coordinates: the concatenation of the text nodes
in document order, which is what ``html_to_text`` produces here and what a
``TreeWalker(SHOW_TEXT)`` produces in ``static/js/review-redact.js``.  Diffing
the HTML source instead would drown in noise the moment CKEditor rewrote a tag.
'''

import lxml.html

from diff_match_patch import diff_match_patch

# A selection longer than this is almost certainly the admin meaning to block
# the whole review rather than mask a word, and the column is sized to match.
MAX_QUOTE_LENGTH = 200

# Subtrees whose text a browser would not show.  ``sanitize()`` already strips
# both, so this only matters for content stored before that was tightened -- but
# the JS skips the same two tags, and the two sides have to agree exactly.
_SKIPPED_TAGS = ('script', 'style')

# Verdicts returned by ``remap``.
INTACT = 'intact'        # every character survived, nothing spliced in
DELETED = 'deleted'      # the whole span is gone from the new text
TAMPERED = 'tampered'    # part of it survived, or something was inserted inside


# The reason an admin has to pick before a redaction is saved.  A fixed list
# rather than free text so the rows stay countable, and because being made to
# name the rule is the cheapest guard against masking a criticism one dislikes.
REASONS = (
    ('abuse', '人身攻击'),
    ('profanity', '侮辱性用语'),
    ('privacy', '隐私信息'),
    ('other', '其他'),
)

REASON_LABELS = dict(REASONS)


def html_to_text(html):
    '''Concatenate the text nodes of an HTML fragment in document order.

    Matches ``TreeWalker(NodeFilter.SHOW_TEXT)`` in the browser: no separators
    are inserted between nodes, entities are decoded, and comments contribute
    nothing.  Both sides must agree character for character or the offsets
    stored here would not address the same text the JS walks.
    '''
    if not html:
        return ''
    # create_parent so a multi-element fragment ("<p>a</p><p>b</p>") parses
    # without lxml picking the first element as the root and dropping the rest.
    fragment = lxml.html.fragment_fromstring(html, create_parent='div')
    for tag in _SKIPPED_TAGS:
        for element in fragment.iter(tag):
            element.drop_tree()
    return fragment.text_content()


def find_occurrences(text, quote):
    '''Every start offset of ``quote`` in ``text``, left to right.'''
    if not quote or not text:
        return []
    found = []
    start = text.find(quote)
    while start >= 0:
        found.append(start)
        # Overlapping matches are intentional: masking "aa" in "aaa" should
        # cover all three characters, not leave a bare one behind.
        start = text.find(quote, start + 1)
    return found


def nearest_occurrence(text, quote, anchor_pos):
    '''The occurrence of ``quote`` closest to ``anchor_pos``, or None.

    Used for a redaction scoped to a single occurrence.  "Closest" rather than
    "exactly at" because the anchor is only refreshed when the review is
    edited through the normal path, and an approximate anchor still picks the
    right one of two occurrences a paragraph apart.
    '''
    found = find_occurrences(text, quote)
    if not found:
        return None
    if anchor_pos is None:
        return found[0]
    return min(found, key=lambda start: abs(start - anchor_pos))


def remap(old_text, new_text, start, end):
    '''Follow the span ``[start, end)`` of ``old_text`` into ``new_text``.

    Returns ``(new_start, new_end, verdict)``.  ``new_start``/``new_end`` are
    None when nothing of the span survived; ``verdict`` is one of ``INTACT``,
    ``DELETED`` or ``TAMPERED``.

    Text inserted *between* two surviving pieces of the span needs no special
    handling to be covered: the bounds come from the first and last surviving
    pieces, so anything spliced in between falls inside them automatically.
    '''
    if start is None or end is None or end <= start:
        return None, None, DELETED

    dmp = diff_match_patch()
    dmp.Diff_Timeout = 1.0
    diffs = dmp.diff_main(old_text, new_text)
    dmp.diff_cleanupSemantic(diffs)

    old_cursor = 0
    new_cursor = 0
    new_start = None
    new_end = None
    kept = 0
    inserted_inside = 0

    for op, chunk in diffs:
        length = len(chunk)
        if op == 0:  # EQUAL -- both cursors advance over the same characters
            overlap_start = max(old_cursor, start)
            overlap_end = min(old_cursor + length, end)
            if overlap_start < overlap_end:
                if new_start is None:
                    new_start = new_cursor + (overlap_start - old_cursor)
                new_end = new_cursor + (overlap_end - old_cursor)
                kept += overlap_end - overlap_start
            old_cursor += length
            new_cursor += length
        elif op == -1:  # DELETE -- consumed from the old text only
            old_cursor += length
        else:  # INSERT -- appears in the new text only
            # Strictly inside: an insertion flush against either boundary is
            # the author writing next to the span, not into it.
            if start < old_cursor < end:
                inserted_inside += length
            new_cursor += length

    if kept == 0:
        return None, None, DELETED
    if kept == end - start and inserted_inside == 0:
        return new_start, new_end, INTACT
    return new_start, new_end, TAMPERED


MASK_CHAR = '█'

# A trailing fragment shorter than this is more likely a coincidence than a
# truncated quote, so it is left alone.  Mirrors MIN_PARTIAL_TAIL in
# static/js/review-redact.js.
MIN_PARTIAL_TAIL = 2


def mask_text(text, quotes):
    '''Cover every quoted stretch of a plain-text string with block characters.

    Only the RSS feed needs this.  Every HTML page paints its masks in the
    browser, where the reader's own text is walked; a feed reader runs no
    JavaScript, so without this the words would reach subscribers untouched.

    Mirrors the matching rules in ``static/js/review-redact.js``, including the
    trailing partial: an abstract is cut to a fixed length and can slice a quote
    in half, and the readable half must not be what survives.
    '''
    if not text or not quotes:
        return text
    for quote in quotes:
        if not quote:
            continue
        text = text.replace(quote, MASK_CHAR * len(quote))
        for length in range(len(quote) - 1, MIN_PARTIAL_TAIL - 1, -1):
            if text.endswith(quote[:length]):
                text = text[:-length] + MASK_CHAR * length
                break
    return text


def normalize_quote(quote):
    '''Trim a selection down to what should actually be masked.

    Dragging a mouse across a few characters routinely picks up a leading or
    trailing space; masking those would black out more than the admin saw in
    the confirmation dialog.  Returns None if nothing is left.
    '''
    if not quote:
        return None
    quote = quote.strip()
    if not quote or len(quote) > MAX_QUOTE_LENGTH:
        return None
    return quote
