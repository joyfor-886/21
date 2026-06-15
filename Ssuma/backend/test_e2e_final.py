"""枢墨七艺框架回归测试 - 最终版"""
import asyncio, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.sqlite import Database
from core.llm_factory import LLMFactory
from core.skill_registry import SkillRegistry
from skills.qishu import BrainstormingSkill
from skills.caiheng import CEOReviewSkill
from skills.zhenwei import EngReviewSkill
from skills.powang import PowangSkill
from skills.ceshu import PlanWritingSkill
from skills.ningmo import SpecGeneratorSkill
from skills.jianyan import JianyanSkill
from services.flow.service import FlowService
from services.flow.router import FlowPhase, FlowRouter, CHANNEL_PHASES
from services.flow.service import get_flow_service
from services.phase_gates import PhaseCompletionGate
from services.intent_analyzer import IntentAnalyzer, IntentAnalysisResult, UserIntent, ClarityLevel

for cls in [BrainstormingSkill, CEOReviewSkill, EngReviewSkill, PowangSkill,
            PlanWritingSkill, SpecGeneratorSkill, JianyanSkill]:
    if cls.name not in SkillRegistry._skills:
        SkillRegistry.register(cls())

db = Database()
db._init_db()
results = []

def record(name, ok, detail=''):
    results.append((name, ok, detail))
    s = "✅" if ok else "❌"
    d = f' → {detail[:120]}' if detail and not ok else ''
    print(f'  {s} {name}{d}', flush=True)


async def run():
    total_t0 = time.time()

    # ===== 1. LLM 连接 =====
    print('\n📡 1. LLM 连接', flush=True)
    try:
        provider = LLMFactory.get_provider()
        resp = await provider.chat(
            [{"role": "user", "content": "你好，简短回复"}],
            max_tokens=30, temperature=0.1
        )
        ok = bool(resp and len(resp.strip()) > 0)
        record('LM Studio + reasoning_content 回退', ok,
               f'响应: {repr(resp[:50])}' if resp else '空响应')
    except Exception as e:
        record('LM Studio 连接', False, str(e)[:100])

    # ===== 2. 技能注册 =====
    print('\n🔧 2. 技能注册', flush=True)
    for s in ['qishu', 'caiheng', 'zhenwei', 'powang', 'ceshu', 'ningmo', 'jianyan']:
        record(f'注册: {s}', s in SkillRegistry._skills)
    for msg, exp in [('我想做', 'qishu'), ('生成方案', 'ningmo')]:
        det = SkillRegistry.detect_skill(msg)
        record(f'触发: "{msg}"', det == exp, f'实际={det}')

    # ===== 3. Phase Gates =====
    print('\n🚧 3. Phase Gates', flush=True)
    for phase, content in [
        ('qishu', '我想做小程序记账，用户痛点是花钱没概念，最小切入点是花销记录，目标用户是年轻上班族'),
        ('caiheng', '裁衡：范围决策保持，风险有竞品多，价值主张让每分钱有归属'),
        ('zhenwei', '技术评审：架构用小程序+云开发，数据模型有User/Transaction'),
        ('ceshu', '执行计划：Task1创建项目，文件path:app.js，测试用例assert:记录功能'),
        ('ningmo', '方案：产品定义有核心问题，架构设计有数据模型'),
    ]:
        r = PhaseCompletionGate.evaluate(phase, content, 2)
        record(f'{phase}', r.score > 0, f'score={r.score:.2f} advance={r.should_advance}')

    # ===== 4. 防跳跃路由 =====
    print('\n🔒 4. 防跳跃路由', flush=True)
    pid = f'aj_{int(time.time())}'
    db.execute('INSERT INTO projects (id,name,description) VALUES (?,?,?)', (pid, 'AJ', 'test'))
    svc = get_flow_service()
    fs = svc._get_or_create_flow_state(pid)
    svc._current_flows[pid] = FlowPhase.QISHU
    intent = IntentAnalysisResult(
        intent=UserIntent.CAIHENG, clarity=ClarityLevel.CLEAR,
        confidence=0.9, reasoning='', recommended_workflow='caiheng', next_action=''
    )

    fs.phase_completion['qishu'] = 0.2
    fs.channel = 'standard'
    svc._channel_assignments[pid] = 'standard'
    router = FlowRouter()
    np = router.determine_next_phase(FlowPhase.QISHU, intent, None, 'standard', fs.phase_completion)
    record('低完成度不前进', np == FlowPhase.QISHU, f'实际={np.value}')

    fs.phase_completion['qishu'] = 0.8
    np = router.determine_next_phase(FlowPhase.QISHU, intent, None, 'standard', fs.phase_completion)
    record('standard→tanyin', np == FlowPhase.TANYIN, f'实际={np.value}')

    fs.channel = 'fast'
    svc._channel_assignments[pid] = 'fast'
    np = router.determine_next_phase(FlowPhase.QISHU, intent, None, 'fast', fs.phase_completion)
    record('fast→caiheng', np == FlowPhase.CAIHENG, f'实际={np.value}')

    np = router.determine_next_phase(FlowPhase.QISHU, intent, 'ningmo', 'fast', fs.phase_completion)
    record('强制→ningmo', np == FlowPhase.NINGMO, f'实际={np.value}')

    svc.reset_flow(pid)
    db.execute('DELETE FROM projects WHERE id=?', (pid,))

    # ===== 5. 通道系统 =====
    print('\n🛤️ 5. 通道系统', flush=True)
    record('fast(3)<standard(5)<deep(7)',
           len(CHANNEL_PHASES['fast']) == 3 and
           len(CHANNEL_PHASES['standard']) == 5 and
           len(CHANNEL_PHASES['deep']) == 7)

    # ===== 6. 启枢 (不调LLM) =====
    print('\n🎭 6. 启枢技能', flush=True)
    skill = SkillRegistry.get_skill('qishu')
    r = await skill.run('我想做小程序记账')
    record('启枢(无LLM)', bool(r.get('response')))

    # ===== 7. IntentAnalyzer (核心修复验证) =====
    print('\n🧠 7. IntentAnalyzer (修复验证)', flush=True)

    # _extract_json
    r = IntentAnalyzer._extract_json('{"clarity":"clear","intent":"qishu"}')
    record('_extract_json: 正常', r.get('clarity') == 'clear')

    r = IntentAnalyzer._extract_json('```json\n{"clarity":"partial","intent":"chat"}\n```')
    record('_extract_json: 代码块', r.get('intent') == 'chat')

    r = IntentAnalyzer._extract_json('思考... {"clarity":"fuzzy","intent":"qishu","confidence":0.7}')
    record('_extract_json: 混合内容', r.get('intent') == 'qishu')

    # _repair_truncated_json
    r = IntentAnalyzer._repair_truncated_json('{"clarity":"clear","intent":"ningmo",')
    record('_repair_truncated_json', r is not None and r.get('intent') == 'ningmo')

    # _keyword_override
    r = IntentAnalyzer._keyword_override('这个架构用什么技术栈实现？', UserIntent.QISHU)
    record('_keyword_override: 技术→zhenwei', r == UserIntent.ZHENWEI)

    r = IntentAnalyzer._keyword_override('帮我生成完整方案', UserIntent.CESHU)
    record('_keyword_override: 方案→ningmo', r == UserIntent.NINGMO)

    # 完整意图分析 (LLM调用)
    for msg, expected in [
        ('我想做一个小程序帮我记账', 'qishu'),
        ('这个架构用什么技术栈实现？', 'zhenwei'),
        ('帮我生成完整方案', 'ningmo'),
    ]:
        t0 = time.time()
        pid_ia = f'ia_{int(time.time())}_{msg[:4]}'
        try:
            r = await IntentAnalyzer.analyze(pid_ia, msg, '')
            ok = r.intent.value == expected and not r.context.get('fallback', False)
            record(f'意图分析: "{msg[:8]}"→{expected} ({time.time()-t0:.0f}s)', ok,
                   f'实际={r.intent.value} fallback={r.context.get("fallback")}')
            IntentAnalyzer.reset_state(pid_ia)
        except Exception as e:
            record(f'意图分析: "{msg[:8]}"', False, str(e)[:80])

    # ===== 8. 七艺技能 (选3个代表性测试) =====
    print('\n🎭 8. 七艺技能 (抽样)', flush=True)
    for skill_name, input_text in [
        ('caiheng', '记账小程序，花销记录和月度报表'),
        ('ningmo', '记账小程序，花销记录'),
        ('jianyan', '记账小程序，分阶段实现'),
    ]:
        t0 = time.time()
        try:
            skill = SkillRegistry.get_skill(skill_name)
            r = await skill.run(input_text)
            resp = r.get('response', '')
            ok = bool(resp and len(resp.strip()) > 0)
            record(f'{skill_name} ({time.time()-t0:.0f}s)', ok,
                   f'len={len(resp)}' if ok else '空响应')
        except Exception as e:
            record(f'{skill_name} ({time.time()-t0:.0f}s)', False, str(e)[:80])

    # ===== 汇总 =====
    total = time.time() - total_t0
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f'\n{"="*50}', flush=True)
    print(f'  总计: {passed} PASSED, {failed} FAILED, 耗时 {total:.0f}s', flush=True)
    print(f'{"="*50}', flush=True)
    if failed > 0:
        print('失败项:', flush=True)
        for name, ok, detail in results:
            if not ok:
                print(f'  ❌ {name}: {detail[:100]}', flush=True)


asyncio.run(run())
