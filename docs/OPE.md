# ОПЕ против предопределённости: как исследование стало машиной

> «Один другое не исключает» — исследование Хозяина и код дома — тоже «одно»
> и «другое».

Исходник — исследовательский синтез Хозяина «Человек ≡ ⟨S,E,Uq,Uv⟩» и
«OPE: среда открытого порождения возможностей» (10.11.2026, v0.1) со ссылками
на Степни/Banzhaf (Royal Society, 2025: три уровня новизны), POPPER
(ICML, 2025: проверка на опровержение), capability-based security, FAIR,
open-ended evolution. В `polymath/ope.py` это — исполняемая теория, а не эссе.

## Карта «исследование → код»

| Идея исследования | Реализация в доме | Проверка |
|---|---|---|
| Три уровня новизны: вариация / инновация / трансформация | `VARIATION` — слово внутри Ω(M0) (честный `FALSIFIED`); `TRANSFORMATION` — новая таблица + новый закон Φ2 | `test_variation_is_honestly_falsified`, `test_transformation_proves_monotone_strict_novelty` |
| Явление, невыразимое моделью | символ вне Σ: `pid1_child_promoted` («ребёнок вырос») — предельная запись | `record.current_model_limit` |
| Ω_t → Discover(ΔΦ) → Ω_{t+1} | `MetaModel.omega(n)` — перебор слов; рост измерен: Ω(4): 33 → 50 (+17) | `test_transformation_...` |
| Монотонность (история не уничтожается) | **теорема**: `includes()` — обход произведения: L(M0) ⊆ L(M1) | `test_includes_rejects_lost_words` |
| Строгая новизна (расширение не пусто) | L(M0) ≠ L(M1): слово с новым символом принято | тот же тест |
| Проверка на опровержение (POPPER) | протокол `IndependentVerifier._protocol`: предел → verify → монотонность → новизна | дважды, результаты обязаны совпасть |
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

## Воспроизвести

```bash
pytest tests/test_ope.py -q    # 14 экзаменов ОПЕ
polymath ope                   # живой прогон: Ω 33 → 50, Φ2, дом чист
python -c "from polymath.ope import OPE; ope = OPE(); r = ope.discover(('pid1_started','pid1_child_promoted','pid1_verdict')); print(r.verdict, ope.model.version, ope.theory_version)"
# REPRODUCED M0-ПИД1+pid1_child_promoted Φ2
```
