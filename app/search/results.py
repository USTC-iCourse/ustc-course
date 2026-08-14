"""The object a search returns.

Interface-compatible with the pagination object the templates already consume,
plus the two things the old engine could never report: how much the query had
to be relaxed to find anything, and what -- if anything -- was left out.
"""

from typing import Optional, Sequence

from .retrieve import MatchQuality

#: Shown above the results when the engine had to widen the query.  Silence
#: here is meaningful: it means the results are what was asked for.
_QUALITY_NOTE = {
    MatchQuality.EXACT: None,
    MatchQuality.STRONG: None,
    MatchQuality.RELATED: "没有找到完全匹配的结果，以下是相关内容。",
    MatchQuality.FUZZY: "没有找到完全匹配的结果，以下是读音或写法相近的内容。",
    MatchQuality.PARTIAL: "没有找到完全匹配的结果，以下是部分匹配的内容。",
}


class SearchResults(object):
    def __init__(
        self,
        page: int,
        per_page: int,
        total: int,
        items: Sequence,
        quality: MatchQuality = MatchQuality.EXACT,
        tier: str = "",
        dropped: Sequence[str] = (),
        stale: bool = False,
        truncated: bool = False,
    ):
        #: The query exceeded the length bound and only its prefix was searched.
        self.truncated = truncated
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = list(items)
        self.quality = quality
        self.tier = tier
        self.dropped = list(dropped)
        #: The index is older than its rebuild interval allows for.  Results are
        #: still correct -- the overlay guarantees that -- but slower.
        self.stale = stale

    @property
    def pages(self) -> int:
        if not self.per_page:
            return 0
        return int((self.total + self.per_page - 1) / self.per_page)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    # review-list.html and list-courses.html build their «/» links from these.
    # Jinja renders a missing attribute as the empty string rather than
    # failing, so omitting them turned both arrows into links back to page 1.
    @property
    def prev_num(self) -> int:
        return max(self.page - 1, 1)

    @property
    def next_num(self) -> int:
        return self.page + 1

    @property
    def note(self) -> Optional[str]:
        # Nothing was found, so nothing was relaxed into -- the caller renders
        # its own "no results" copy and a caveat here would only confuse.
        if not self.total:
            return None
        note = _QUALITY_NOTE.get(self.quality)
        if note and self.dropped:
            note += "（已忽略：%s）" % "、".join(self.dropped)
        if self.truncated:
            prefix = "搜索词过长，仅使用了开头的部分。"
            return prefix + note if note else prefix
        return note

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (num > self.page - left_current - 1 and num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num

    @staticmethod
    def empty(page: int = 1, per_page: int = 10) -> "SearchResults":
        return SearchResults(page, per_page, 0, [])
