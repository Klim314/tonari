from app.utils.sentence_splitter import GreedySentenceSplitter


def test_splitter_keeps_mixed_terminators_with_prior_sentence():
    splitter = GreedySentenceSplitter()

    spans = splitter.split("何だ！？ 次だ。")

    assert [(span.span_start, span.span_end, span.text) for span in spans] == [
        (0, 5, "何だ！？ "),
        (5, 8, "次だ。"),
    ]


def test_splitter_greedily_groups_terminator_runs():
    splitter = GreedySentenceSplitter()

    spans = splitter.split("何だ？！ 次だ！！ 終わり…。")

    assert [span.text for span in spans] == [
        "何だ？！ ",
        "次だ！！ ",
        "終わり…。",
    ]


def test_splitter_returns_remainder_without_terminator():
    splitter = GreedySentenceSplitter()

    spans = splitter.split("彼は歩く。途中")

    assert [span.text for span in spans] == ["彼は歩く。", "途中"]
