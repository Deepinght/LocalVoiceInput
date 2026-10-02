import pytest
from voiceinput.engine.normalizers import unit_normalizer


@pytest.mark.parametrize("source,target", [("450～500摄氏度", "450～500 ℃"), ("100标方每小时", "100 Nm³/h"), ("12.5毫升每分钟", "12.5 mL/min"), ("温度500度", "温度500 ℃"), ("500 ℃到600 ℃", "500～600 ℃"), ("90度角", "90度角")])
def test_units(source, target):
    assert unit_normalizer(source) == target
