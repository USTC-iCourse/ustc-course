"""Unit tests for the normalization contract and the token streams.

These need no database and no index -- they pin down the invariant everything
else depends on: the index side and the query side agree.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.search import text as T  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_punctuation_becomes_a_run_boundary(self):
        self.assertEqual(T.normalize("数据结构、算法"), "数据结构 算法")
        self.assertEqual(T.normalize("微积分(B1)"), "微积分 b1")

    def test_script_change_is_a_run_boundary(self):
        # Without this, "微积分B" could not be a substring of "微积分(B1)".
        self.assertEqual(T.normalize("微积分B"), "微积分 b")
        self.assertIn(T.normalize("微积分B"), T.normalize("微积分(B1)"))

    def test_nfkc_folds_compatibility_forms(self):
        self.assertEqual(T.normalize("英语交流Ⅰ"), T.normalize("英语交流I"))
        self.assertEqual(T.normalize("ＰＹＴＨＯＮ"), "python")

    def test_traditional_folds_to_simplified(self):
        self.assertEqual(T.normalize("編譯原理"), T.normalize("编译原理"))

    def test_case_is_folded(self):
        self.assertEqual(T.normalize("Python"), T.normalize("PYTHON"))

    def test_empty_input(self):
        self.assertEqual(T.normalize(""), "")
        self.assertEqual(T.normalize(None), "")
        self.assertEqual(T.normalize("!!!???"), "")


class TestQueryNormalize(unittest.TestCase):
    def test_trailing_honorific_is_stripped(self):
        # Teacher records say 张三, users type 张三老师.
        self.assertEqual(T.normalize_query("张三老师"), "张三")
        self.assertEqual(T.normalize_query("王教授"), "王")

    def test_honorific_is_kept_when_it_is_the_whole_query(self):
        self.assertEqual(T.normalize_query("老师"), "老师")

    def test_honorific_characters_are_kept_mid_query(self):
        self.assertEqual(T.normalize_query("课程设计"), "课程设计")

    def test_honorific_is_reported_so_the_query_can_be_aimed(self):
        core, person = T.normalize_query_parts("张老师")
        self.assertEqual(core, "张")
        self.assertTrue(person, "the engine must know this named a person")
        core, person = T.normalize_query_parts("数学分析")
        self.assertEqual(core, "数学分析")
        self.assertFalse(person)


class TestGrams(unittest.TestCase):
    def test_cjk_run_yields_adjacent_bigrams(self):
        self.assertEqual(T.grams("数据结构"), ["数据", "据结", "结构"])

    def test_gapped_grams_absorb_one_character(self):
        # 编译原理与技术 vs 编译原理和技术 must share gapped grams, which is what
        # lets the fuzzy tier bridge them without a list of connectives.
        a = set(T.grams(T.normalize("编译原理与技术"), gap=2))
        b = set(T.grams(T.normalize("编译原理和技术"), gap=2))
        self.assertTrue(a & b)

    def test_single_character_run(self):
        self.assertEqual(T.grams("数"), ["数"])

    def test_latin_run_is_whole(self):
        self.assertEqual(T.grams(T.normalize("python 编程")), ["python", "编程"])

    def test_grams_do_not_cross_a_run_boundary(self):
        # "结构算法" does not occur in "数据结构、算法" and must not be findable.
        self.assertNotIn("构算", T.grams(T.normalize("数据结构、算法")))


class TestPinyin(unittest.TestCase):
    def test_homophones_share_pinyin_grams(self):
        target = set(T.pinyin_grams(T.normalize("自杀")))
        for variant in ("紫砂", "自鲨", "自沙"):
            self.assertTrue(
                target & set(T.pinyin_grams(T.normalize(variant))),
                "%s should share a pinyin gram with 自杀" % variant,
            )

    def test_whole_name_pinyin(self):
        self.assertIn("shuxuefenxi", T.pinyin_whole(T.normalize("数学分析")))

    def test_initials(self):
        self.assertIn("sxfx", T.pinyin_initials(T.normalize("数学分析")))

    def test_latin_is_ignored(self):
        self.assertEqual(T.pinyin_grams(T.normalize("python")), [])


class TestChars(unittest.TestCase):
    def test_chars_split_cjk_but_not_latin(self):
        self.assertEqual(T.chars(T.normalize("数分 cs")), ["数", "分", "cs"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
