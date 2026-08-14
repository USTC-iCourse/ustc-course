"""The on-disk index segment: a writer, and an mmap-backed reader.

A segment is one immutable file holding, for one collection, every postings
list plus the normalized text of every document.  Workers ``mmap`` it and read
straight out of the page cache, so the whole gunicorn pool shares one physical
copy.  That sharing is the reason for the format: the same index held as Python
dicts measured 44 MB per worker, which across 32 workers would be well over a
gigabyte; as a mapped file it is one copy no matter how many workers there are,
and it costs nothing to fork.

Layout::

    magic | u32 header length | JSON header | pad to 64 | arrays...

The header records, for every array, its dtype, shape and byte offset, so the
reader is a handful of ``np.frombuffer`` views over the mapping -- no parsing
and no allocation at open time.

A field's postings are four parallel arrays: ``keys`` (sorted term hashes),
``ptr`` (start offset of each term's run, plus a final sentinel), ``docs``
(document indices, ascending within a term) and ``tf`` (term frequency, capped
at 255 -- BM25 saturates long before that).

Terms are stored as 64-bit BLAKE2b digests rather than strings, which keeps
lookup to one ``np.searchsorted`` and keeps the key array a flat integer block.
With ~350k distinct terms the collision probability is ~1e-8; a collision can
only admit a spurious *candidate*, which the verification tiers then reject.
"""

import json
import mmap
import os
from array import array
from datetime import datetime
from hashlib import blake2b
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

MAGIC = b"ICSEG\x03"
_ALIGN = 64

#: tf is stored in a byte.  BM25's saturation curve is flat well before this.
MAX_TF = 255


def term_hash(term: str) -> int:
    """Stable 64-bit hash.  Must not be Python's ``hash()``: that is salted per
    process, so a builder and a worker would disagree."""
    return int.from_bytes(blake2b(term.encode("utf-8"), digest_size=8).digest(), "big")


def term_hashes(terms: Sequence[str]) -> np.ndarray:
    return np.fromiter((term_hash(t) for t in terms), dtype=np.uint64, count=len(terms))


class SegmentWriter:
    """Accumulates documents, then writes one segment file atomically."""

    def __init__(self, collection: str, fields: Sequence[str], meta: Optional[dict] = None):
        self.collection = collection
        self.fields = list(fields)
        self.meta = dict(meta or {})
        self._doc_ids = array("i")
        self._texts: List[bytes] = []
        self._lengths = array("i")
        self._priors: Dict[str, array] = {}
        # Per field, three flat parallel columns of (term id, doc index, tf).
        # ``array`` rather than ``list``: a review index reaches ~5.5M postings
        # per field, and boxed Python ints would cost several hundred megabytes
        # more than the finished segment.
        self._term_ids: Dict[str, array] = {f: array("l") for f in self.fields}
        self._doc_idx: Dict[str, array] = {f: array("i") for f in self.fields}
        self._tf: Dict[str, array] = {f: array("B") for f in self.fields}
        self._vocab: Dict[str, int] = {}
        self._vocab_terms: List[str] = []

    def _term_id(self, term: str) -> int:
        tid = self._vocab.get(term)
        if tid is None:
            tid = len(self._vocab_terms)
            self._vocab[term] = tid
            self._vocab_terms.append(term)
        return tid

    def add_doc(
        self,
        doc_id: int,
        norm_text: str,
        streams: Dict[str, Sequence[str]],
        priors: Dict[str, float],
    ) -> None:
        doc_idx = len(self._doc_ids)
        self._doc_ids.append(doc_id)
        encoded = norm_text.encode("utf-8")
        self._texts.append(encoded)
        # Document length for BM25 is measured in gram tokens, the unit the
        # scoring actually runs over -- not characters and not bytes.
        self._lengths.append(max(1, len(streams.get(self.fields[0], ()))))

        for name, value in priors.items():
            self._priors.setdefault(name, array("d")).append(value)

        for field in self.fields:
            tokens = streams.get(field) or ()
            if not tokens:
                continue
            counts: Dict[str, int] = {}
            for tok in tokens:
                counts[tok] = counts.get(tok, 0) + 1
            tids = self._term_ids[field]
            didx = self._doc_idx[field]
            tfs = self._tf[field]
            for term, tf in counts.items():
                tids.append(self._term_id(term))
                didx.append(doc_idx)
                tfs.append(tf if tf < MAX_TF else MAX_TF)

    def _pack_field(self, field: str) -> Dict[str, np.ndarray]:
        tids = np.frombuffer(self._term_ids[field], dtype=np.int64)
        docs = np.frombuffer(self._doc_idx[field], dtype=np.int32)
        tf = np.frombuffer(self._tf[field], dtype=np.uint8)
        if tids.size == 0:
            return {
                "keys": np.zeros(0, dtype=np.uint64),
                "ptr": np.zeros(1, dtype=np.int64),
                "docs": np.zeros(0, dtype=np.int32),
                "tf": np.zeros(0, dtype=np.uint8),
            }
        vocab_hashes = term_hashes(self._vocab_terms)
        hashed = vocab_hashes[tids]
        # Sort by term, and by document within each term, so a postings list is
        # a contiguous ascending run -- which is what makes intersection a
        # searchsorted rather than a set operation.
        order = np.lexsort((docs, hashed))
        hashed, docs, tf = hashed[order], docs[order], tf[order]
        keys, starts = np.unique(hashed, return_index=True)
        ptr = np.append(starts, hashed.size).astype(np.int64)
        return {"keys": keys, "ptr": ptr, "docs": docs, "tf": tf}

    def write(self, path: str) -> None:
        arrays: Dict[str, np.ndarray] = {}
        for field in self.fields:
            for suffix, arr in self._pack_field(field).items():
                arrays["%s.%s" % (field, suffix)] = arr
            # Release as we go; a full review index holds several million
            # postings per field and the builder is memory-bound, not CPU-bound.
            self._term_ids[field] = array("l")
            self._doc_idx[field] = array("i")
            self._tf[field] = array("B")

        text_ptr = np.zeros(len(self._texts) + 1, dtype=np.int64)
        if self._texts:
            text_ptr[1:] = np.cumsum(
                np.fromiter((len(t) for t in self._texts), dtype=np.int64, count=len(self._texts))
            )
        arrays["text.ptr"] = text_ptr
        arrays["text.blob"] = np.frombuffer(b"".join(self._texts), dtype=np.uint8)
        arrays["doc.id"] = np.frombuffer(self._doc_ids, dtype=np.int32)
        arrays["doc.len"] = np.frombuffer(self._lengths, dtype=np.int32)
        for name, values in self._priors.items():
            if len(values) != len(self._doc_ids):
                raise ValueError(
                    "prior %r covers %d of %d documents; every document must "
                    "emit every prior or the arrays stop being parallel"
                    % (name, len(values), len(self._doc_ids))
                )
            arrays["prior." + name] = np.frombuffer(values, dtype=np.float64)

        header = {
            "collection": self.collection,
            "fields": self.fields,
            "doc_count": len(self._doc_ids),
            "priors": sorted(self._priors),
            "arrays": {},
        }
        header.update(self.meta)
        offset = 0
        for name, arr in arrays.items():
            offset = _align(offset)
            header["arrays"][name] = {
                "dtype": arr.dtype.str,
                "shape": list(arr.shape),
                "offset": offset,  # relative to the body; made absolute below
                "nbytes": int(arr.nbytes),
            }
            offset += arr.nbytes

        # Array offsets are absolute, but they live inside the header whose own
        # length they therefore depend on.  Reserve a padded header region so
        # rewriting the offsets cannot change where the body starts.
        draft = json.dumps(header, ensure_ascii=False).encode("utf-8")
        region = _align(len(MAGIC) + 4 + len(draft) + 256)
        for meta in header["arrays"].values():
            meta["offset"] += region
        blob = json.dumps(header, ensure_ascii=False).encode("utf-8")
        pad = region - len(MAGIC) - 4 - len(blob)
        if pad < 0:
            raise RuntimeError("segment header outgrew its reserved region")
        blob += b" " * pad  # json.loads tolerates trailing whitespace

        tmp = path + ".tmp"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(tmp, "wb") as fh:
            fh.write(MAGIC)
            fh.write(len(blob).to_bytes(4, "little"))
            fh.write(blob)
            for name, arr in arrays.items():
                meta = header["arrays"][name]
                pad = meta["offset"] - fh.tell()
                if pad:
                    fh.write(b"\0" * pad)
                fh.write(arr.tobytes())
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)


def _align(offset: int) -> int:
    return (offset + _ALIGN - 1) // _ALIGN * _ALIGN


class Segment:
    """Read-only mmap view of a segment file."""

    def __init__(self, path: str):
        self.path = path
        self._fh = open(path, "rb")
        self._mm = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        if self._mm[: len(MAGIC)] != MAGIC:
            raise ValueError("not a search segment: %s" % path)
        hlen = int.from_bytes(self._mm[len(MAGIC) : len(MAGIC) + 4], "little")
        start = len(MAGIC) + 4
        self.header = json.loads(bytes(self._mm[start : start + hlen]).decode("utf-8"))
        self.collection = self.header["collection"]
        self.fields = self.header["fields"]
        self.doc_count = self.header["doc_count"]
        #: Watermark for the freshness overlay: rows modified at or after this
        #: instant are re-read from the database instead of trusted here.
        #: Naive UTC, matching the columns it is compared against.
        stamp = self.header.get("built_at_utc")
        self.built_at = datetime.fromisoformat(stamp) if stamp else datetime(1970, 1, 1)
        self.mtime = os.stat(path).st_mtime
        self._arrays: Dict[str, np.ndarray] = {}
        #: Scratch space for values derived once per segment (corpus-wide
        #: statistics the ranker needs).  Safe to share: a segment is immutable.
        self.cache: Dict[str, object] = {}
        self._text_base = self.header["arrays"]["text.blob"]["offset"]

        self.doc_ids = self.array("doc.id")
        self.doc_len = self.array("doc.len")
        self._text_ptr = self.array("text.ptr")
        self.avg_doc_len = float(self.doc_len.mean()) if self.doc_count else 1.0
        # Document id -> index, for the delta overlay to mask stale rows.
        self._id_order = np.argsort(self.doc_ids)
        self._sorted_ids = self.doc_ids[self._id_order]

    def array(self, name: str) -> np.ndarray:
        arr = self._arrays.get(name)
        if arr is None:
            meta = self.header["arrays"][name]
            arr = np.frombuffer(
                self._mm,
                dtype=np.dtype(meta["dtype"]),
                count=int(np.prod(meta["shape"])) if meta["shape"] else 0,
                offset=meta["offset"],
            )
            self._arrays[name] = arr
        return arr

    def prior(self, name: str) -> np.ndarray:
        return self.array("prior." + name)

    def has_prior(self, name: str) -> bool:
        return ("prior." + name) in self.header["arrays"]

    def postings(self, field: str, term: str) -> Tuple[np.ndarray, np.ndarray]:
        """Documents and term frequencies for one term, or empty arrays."""
        keys = self.array(field + ".keys")
        if keys.size == 0:
            return _EMPTY_I32, _EMPTY_U8
        h = np.uint64(term_hash(term))
        pos = int(np.searchsorted(keys, h))
        if pos >= keys.size or keys[pos] != h:
            return _EMPTY_I32, _EMPTY_U8
        ptr = self.array(field + ".ptr")
        lo, hi = int(ptr[pos]), int(ptr[pos + 1])
        return self.array(field + ".docs")[lo:hi], self.array(field + ".tf")[lo:hi]

    def doc_freq(self, field: str, term: str) -> int:
        keys = self.array(field + ".keys")
        if keys.size == 0:
            return 0
        h = np.uint64(term_hash(term))
        pos = int(np.searchsorted(keys, h))
        if pos >= keys.size or keys[pos] != h:
            return 0
        ptr = self.array(field + ".ptr")
        return int(ptr[pos + 1]) - int(ptr[pos])

    def find(self, doc_idx: int, needle: bytes, start: int = 0) -> int:
        """Offset of ``needle`` within a document's normalized text, or -1.

        Both ``start`` and the return value are relative to the start of the
        document, so callers can compare a hit against the zone offsets a
        document records without knowing where it sits in the blob.

        UTF-8 is self-synchronizing, so a byte-level search cannot report a
        match straddling a character boundary.  ``mmap.find`` runs in C against
        the mapping, so verification never decodes or copies text.
        """
        base = self._text_base + int(self._text_ptr[doc_idx])
        hi = self._text_base + int(self._text_ptr[doc_idx + 1])
        if not needle:
            return 0
        found = self._mm.find(needle, min(base + start, hi), hi)
        return -1 if found < 0 else found - base

    def text(self, doc_idx: int) -> str:
        lo = self._text_base + int(self._text_ptr[doc_idx])
        hi = self._text_base + int(self._text_ptr[doc_idx + 1])
        return bytes(self._mm[lo:hi]).decode("utf-8", "replace")

    def index_of(self, doc_id: int) -> int:
        pos = int(np.searchsorted(self._sorted_ids, doc_id))
        if pos >= self._sorted_ids.size or self._sorted_ids[pos] != doc_id:
            return -1
        return int(self._id_order[pos])

    def mask_ids(self, doc_ids: Sequence[int]) -> np.ndarray:
        """Indices of the given document ids that exist in this segment."""
        if len(doc_ids) == 0 or self._sorted_ids.size == 0:
            return _EMPTY_I32
        wanted = np.asarray(sorted(doc_ids), dtype=np.int32)
        pos = np.clip(np.searchsorted(self._sorted_ids, wanted), 0, self._sorted_ids.size - 1)
        hit = self._sorted_ids[pos] == wanted
        return self._id_order[pos[hit]].astype(np.int32)

    def close(self) -> None:
        """Release the mapping, as far as anything still using it allows.

        Every array handed out is a zero-copy ``frombuffer`` view, and a live
        view is a buffer export that ``mmap.close`` refuses to invalidate --
        rightly, since freeing it under a reader would be a segfault rather
        than an exception.  Dropping our own references is therefore the most
        that can be promised here; the mapping goes away when the last view
        does.
        """
        self._arrays.clear()
        self.cache.clear()
        self.doc_ids = self.doc_len = self._text_ptr = None
        try:
            self._mm.close()
        except BufferError:
            pass
        finally:
            self._fh.close()


_EMPTY_I32 = np.zeros(0, dtype=np.int32)
_EMPTY_U8 = np.zeros(0, dtype=np.uint8)
