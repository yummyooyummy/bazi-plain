import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from paipan import from_pillars
from synastry import compare


def test_two_chart_facts_preserve_roles_without_fortune_score():
    a=from_pillars(['戊辰','戊午','戊申','己未'])
    b=from_pillars(['壬子','辛亥','癸丑','壬子'])
    result=compare(a,b)
    assert result['scope']=='facts_only'
    assert result['B_day_stem_relative_to_A']=='正财'
    assert result['A_day_stem_relative_to_B']=='正官'
    assert result['not_a_compatibility_score']
    assert result['relations_between_charts']


def test_boundary_alternative_cannot_be_silently_dropped_for_synastry():
    a=from_pillars(['戊辰','戊午','戊申','己未'])
    b=from_pillars(['壬子','辛亥','癸丑','壬子'])
    a['alternative_charts']=[{'four_pillars':['戊辰','戊午','戊申','庚申']}]
    with pytest.raises(ValueError,match='备选'):compare(a,b)
