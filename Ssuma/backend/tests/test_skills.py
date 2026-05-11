import pytest
from skills.powang import PowangSkill
from skills.jianyan import JianyanSkill


class TestSkills:

    def test_powang_skill_properties(self):
        assert PowangSkill.name == "powang"
        assert "破妄" in PowangSkill.description
        assert PowangSkill.trigger == "检查需求"

    def test_jianyan_skill_properties(self):
        assert JianyanSkill.name == "jianyan"
        assert "渐衍" in JianyanSkill.description
        assert JianyanSkill.trigger == "分阶段"