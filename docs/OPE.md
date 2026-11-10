# ОПЕ против предопределённости: как исследование стало машиной

> «Один другое не исключает» — исследование Хозяина и код дома — тоже «одно»
> и «другое».

Исходник — исследовательский синтез Хозяина «Человек ≡ ⟨S,E,Uq,Uv⟩» и
«OPE: среда открытого порождения возможностей» (10.11.2026, v0.1).
Тезисы синтеза сверены с первоисточниками (см. «Сверку» ниже): таксономия
новизны — Banzhaf et al. 2016 (вариация/инновация/эмерджентность; у Stepney
«эмерджентность» переименована в «трансформацию», уровни «не жёстко
разделены»), протокол опровержения — POPPER (Huang et al., ICML 2025).
В `polymath/ope.py` это — исполняемая теория, а не эссе.

## Карта «исследование → код»

| Идея исследования | Реализация в доме | Проверка |
|---|---|---|
| Три уровня новизны: вариация / инновация / трансформация (Banzhaf 2016: «эмерджентность»; переименована Stepney в «трансформацию») | `VARIATION` — слово внутри Ω(M0) (честный `FALSIFIED`); `TRANSFORMATION` — новая таблица + новый закон Φ2 | `test_variation_is_honestly_falsified`, `test_transformation_proves_monotone_strict_novelty` |
| Явление, невыразимое моделью | символ вне Σ: `pid1_child_promoted` («ребёнок вырос») — предельная запись | `record.current_model_limit` |
| Ω_t → Discover(ΔΦ) → Ω_{t+1} | `MetaModel.omega(n)` — перебор слов; рост измерен: Ω(4): 33 → 50 (+17) | `test_transformation_...` |
| Монотонность (история не уничтожается) | **теорема**: `includes()` — обход произведения: L(M0) ⊆ L(M1) | `test_includes_rejects_lost_words` |
| Строгая новизна (расширение не пусто) | L(M0) ≠ L(M1): слово с новым символом принято | тот же тест |
| Проверка на опровержение (POPPER: Huang, Jin, Li, Li, Candès, Leskovec — ICML 2025) | протокол `IndependentVerifier._protocol`: предел → verify → монотонность → новизна | дважды, результаты обязаны совпасть |
| Лестница вердиктов UNKNOWN → TESTABLE → PARTIALLY_VERIFIED → REPRODUCED (+ FALSIFIED/INCONCLUSIVE/BLOCKED) | `VERDICT_TABLE` — DFA, 7 состояний × 9 событий, `verify()` рождён | `test_verdict_ladder_passes_theory_exam` |
| Создатель не объявляет доказанным (capability) | генератор без методов вердикта; самовольный вердикт → `BLOCKED` | `test_blocked_self_approval` |
| Независимая проверка | верификатор держит свою копию M0, не мутирующую усыновлением | `test_independent_verifier_keeps_own_copy` |
| PossibilityRecord / FAIR-происхождение | `PossibilityRecord` (схема `OPE/PossibilityRecord/1.0`): observation, limit, predictions, falsification_conditions, provenance, parent_versions, created_capabilities | поля заполнены машиной |
| Эволюция эволюционируемости | усыновление принимает закон **Φ2**: монотонность обязательна для будущих мутаций — закон имеет зубы | `test_phi2_law_has_teeth` |
| Устойчивость: откат без потери истории | `rollback()` → M0; `history` жива; `fork()` — песочница | `test_rollback_and_fork_keep_history` |

## Три запрета Хозяина — исполнены кодом

1. **Не подменять Человека описанием** — `record.identity is None` всегда
   (структурно, поле не заполняется ничем);
2. **Не подменять универсальность унификацией** — любая таблица, прошедшая
   экзамены, — законная модель (`fork`, альтернативные реализации);
3. **Не подменять развитие подгонкой** — развитие = смена Φ (закон метамодели),
   а не перебор параметров; `TRANSFORMATION` обязан менять правила.

## Пределы ОПЕ (Гёдель II — вердикт среды не полон)

`LIMITS_OPE` объявляет 4 границы, среди них: шаблоны мутаций конечны —
генератор не выдумывает молча; воспроизведение внутри одного кода — не внешняя
проверка; Ω измерима лишь до выбранного n; формула H ≡ ⟨S,E,Uq,Uv⟩ —
философская гипотеза Хозяина и проектный принцип, а не доказанный закон.

## Сверка с первоисточниками (ритуал дома: каждый внешний тезис имеет строку)

Ошибка волны 9: тезисы были приняты за чистую монету — теперь алгоритм: пока
тезис не имеет строки здесь, он не входит в дом. Сверка 12.11.2026:

| Тезис из исследования | Первоисточник | Вердикт сверки |
|---|---|---|
| Обзор «Towards origins of virtual artificial life» существует; «система, удовлетворяющая всем требованиям, пока не продемонстрирована» | Stepney S. Philosophical Transactions B, 380(1936):20240298, 02.10.2025, DOI 10.1098/rstb.2024.0298 — [royalsocietypublishing.org](https://royalsocietypublishing.org/rstb/article/380/1936/20240298/235116); цитата подтверждена дословно | ✅ подтверждено |
| Таксономия «вариация/инновация/трансформация» у Banzhaf | Banzhaf et al. 2016, Theory in Biosciences 135(3):131–161 — уровни названы «вариация, инновация, эмерджентность»; Stepney (OEE4, «Modelling and measuring open-endedness») переименовывает «эмерджентность → трансформация» и оговаривает «типы не жёстко разделены» — [workshops.alife.org](http://workshops.alife.org/oee4/papers/stepney-oee4-camera-ready.pdf) | ⚠️ уточнено: «трансформация» — переименованное «эмерджентность»; у обзора 2025 — своя тройка уровней «требования/дизайн/реализация» |
| POPPER: агенты проектируют фальсификационные эксперименты, контроль ошибки I рода | Huang, Jin, Li, Li, Candès, Leskovec. «Automated Hypothesis Validation with Agentic Sequential Falsifications», ICML 2025, arXiv:2502.09858 — [arxiv.org](https://arxiv.org/abs/2502.09858); абстракт подтверждён дословно («strict Type-I error control») | ✅ подтверждено |
| «Roll the dice & look before you leap» — ICML 2025 Outstanding Paper | Nagarajan et al., arXiv:2504.15266, ICML 2025 — [icml.cc](https://icml.cc/virtual/2025/poster/45769), [cs.cmu.edu](https://www.cs.cmu.edu/~aditirag/icml2025.html) («Outstanding Paper Award») | ✅ подтверждено |
| Robin — мультиагентная система научных открытий (Nature 2026) | Ghareeb et al., Nature, DOI 10.1038/s41586-026-10652-y — [nature.com](https://www.nature.com/articles/s41586-026-10652-y); DOI совпал | ✅ подтверждено |
| «Unifying AI-assisted scientific discovery» (2026) | Patterns 7(10):101660, сентябрь 2026 — «Unifying AI-Assisted Scientific Discovery Around Exploration, Hypothesis Generation, and Testing» | ✅ подтверждено (название/журнал) |
| WCAG 2.2 — четыре проверяемых принципа | W3C TR WCAG22 (12.12.2024): perceivable, operable, understandable, robust (POUR) — [w3.org](https://www.w3.org/TR/WCAG22/) | ✅ подтверждено |
| Capability-based security, FAIR/FAIR4RS, local-first (Ink & Switch), ActivityPub | общеизвестные инженерные практики; в этой волне в первоисточник не сверялись — отмечено честно, сверка продолжится следующей волной | ⏳ вне сверки этой волны |

Итог: два уточнения атрибуции (таксономия, три уровня обзора), всё остальное
подтверждено первоисточниками. Ритуал закреплён тестом
`test_ope_doc_carries_provenance_table`: документ без таблицы сверки не входит
в дом.

## Воспроизвести

```bash
pytest tests/test_ope.py -q    # 14 экзаменов ОПЕ
polymath ope                   # живой прогон: Ω 33 → 50, Φ2, дом чист
python -c "from polymath.ope import OPE; ope = OPE(); r = ope.discover(('pid1_started','pid1_child_promoted','pid1_verdict')); print(r.verdict, ope.model.version, ope.theory_version)"
# REPRODUCED M0-ПИД1+pid1_child_promoted Φ2
```
