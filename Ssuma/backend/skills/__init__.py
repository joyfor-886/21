from core.skill_registry import SkillRegistry

from .qishu import BrainstormingSkill  # qishu
from .caiheng import CEOReviewSkill  # caiheng
from .zhenwei import EngReviewSkill  # zhenwei
from .design_review import DesignReviewSkill
from .ceshu import PlanWritingSkill  # ceshu
from .autoplan import AutoPlanSkill
from .ningmo import SpecGeneratorSkill  # ningmo
from .mindmap_generator import MindmapGeneratorSkill
from .powang import PowangSkill
from .jianyan import JianyanSkill
from .metacognition import MetacognitionSkill


def register_builtin_skills():
    SkillRegistry.register(BrainstormingSkill())     # qishu
    SkillRegistry.register(CEOReviewSkill())      # caiheng
    SkillRegistry.register(EngReviewSkill())        # zhenwei
    SkillRegistry.register(DesignReviewSkill())
    SkillRegistry.register(PlanWritingSkill())   # ceshu
    SkillRegistry.register(AutoPlanSkill())
    SkillRegistry.register(SpecGeneratorSkill())  # ningmo
    SkillRegistry.register(MindmapGeneratorSkill())
    SkillRegistry.register(PowangSkill())       # powang
    SkillRegistry.register(JianyanSkill())      # jianyan
    SkillRegistry.register(MetacognitionSkill())  # metacognition
