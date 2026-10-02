from voiceinput.feedback.engine import suggest


def test_short_context():
    assert suggest("树据分析在500 ℃测试。", "数据分析在500 ℃测试。") == ("树据分析", "数据分析")
    assert suggest("测试", "测试") is None
    assert suggest("甲" * 40, "乙" * 40) is None
