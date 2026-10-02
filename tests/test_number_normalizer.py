import pytest
from voiceinput.engine.normalizers import number_normalizer


@pytest.mark.parametrize("source,target", [("一百", "100"), ("十二点五", "12.5"), ("百分之十二点五", "12.5%"), ("四百五十到五百摄氏度", "450～500摄氏度"), ("温度五百度", "温度500度"), ("一起去一号实验室", "一起去一号实验室"), ("二氧化碳", "二氧化碳"), ("一百毫升每分钟", "100毫升每分钟")])
def test_numbers(source, target):
    assert number_normalizer(source) == target
