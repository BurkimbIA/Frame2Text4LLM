from frame2text4llm.language import written_in


def test_written_in_by_function_words():
    assert written_in("Je ne sais pas ce que tu veux dire") == "french"
    assert written_in("I don't know what you mean") == "english"
    assert written_in("Ne y windga") == "other"


def test_a_tie_is_other():
    assert written_in("le the") == "other"
