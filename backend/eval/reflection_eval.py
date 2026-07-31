"""
Phase 4B: seeded precision/recall eval for the Reflection Agent
(agents/reflection.py).

Rather than re-running the full teach -> reflect pipeline (expensive, and the
subject agent's own output would need a human to grade anyway), this seeds a
small fixed set of seven-key teaching_output payloads against *real* retrieved
NCERT context (fetched live via rag.retriever.retrieve, same as rag_eval.py)
and labels each one by hand as "should pass" or "should fail", covering the
three things reflection is supposed to catch (see agents/prompts.py's
REFLECTION_PROMPT): ungrounded claims, curriculum-inappropriate content, and
wrong pacing for a flagged-weak student. It then calls the exact same prompt
template and model reflection.py uses and checks whether its verdict matches
the label.

"Should fail" is treated as the positive class (that's the case reflection
exists to catch), so:
    precision = TP / (TP + FP)   - of the outputs reflection rejected, how many
                                    actually deserved it
    recall    = TP / (TP + FN)   - of the outputs that actually deserved
                                    rejection, how many reflection caught

Usage:
    python -m eval.reflection_eval
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.prompt_registry import render_versioned  # noqa: E402
from agents.subject_agents import _format_context, call_groq_with_retry  # noqa: E402
from rag.retriever import retrieve  # noqa: E402

REFLECTION_MODEL = "llama-3.1-8b-instant"

_SEEDS = [
    {
        "id": "good_fractions_default",
        "subject": "math",
        "grade": 6,
        "chapter": "Fractions",
        "topic": "Equivalent fractions",
        "student_memory": {},
        "expected_passed": True,
        "defect_type": None,
        "teaching_output": {
            "headline": "Equivalent fractions represent the same value",
            "explanation": (
                "1. A fraction shows part of a whole, like half a guava. "
                "2. Equivalent fractions such as 1/2 and 2/4 name the same amount. "
                "3. Multiply the numerator and denominator by the same number to find an equivalent fraction. "
                "4. Check by simplifying both fractions to see if they match."
            ),
            "ncert_example": "Three guavas together weigh 1 kg; if they are roughly the same size, each weighs about 1/3 kg.",
            "analogy": "It's like cutting a chapati into 2 big pieces or 4 small pieces - you still get the same amount of roti either way.",
            "common_mistake": "Students think 1/2 and 2/4 are different because the numbers look different, forgetting both name the same amount.",
            "guiding_question": "If 1/2 equals 2/4, what would 3/6 simplify to?",
            "topics_covered": ["equivalent fractions"],
        },
    },
    {
        "id": "good_fractions_scaffolded_for_weak",
        "subject": "math",
        "grade": 6,
        "chapter": "Fractions",
        "topic": "Equivalent fractions",
        "student_memory": {"mastery": {"equivalent fractions": 0.3}, "weak_topics": ["equivalent fractions"]},
        "expected_passed": True,
        "defect_type": None,
        "teaching_output": {
            "headline": "Equivalent fractions represent the same value",
            "explanation": (
                "1. First, remember a fraction is just part of a whole - like sharing one guava between people. "
                "2. Equivalent fractions, like 1/2 and 2/4, look different but name the exact same amount. "
                "3. To find one, multiply top and bottom by the same number - never just one of them. "
                "4. Let's check slowly with 1/2: multiply both by 2 to get 2/4, then verify they cover the same part of a whole."
            ),
            "ncert_example": "Three guavas together weigh 1 kg; if they are roughly the same size, each weighs about 1/3 kg.",
            "analogy": "It's like cutting a chapati into 2 big pieces or 4 small pieces - you still get the same amount of roti either way.",
            "common_mistake": "Students think 1/2 and 2/4 are different because the numbers look different, forgetting both name the same amount.",
            "guiding_question": "If 1/2 equals 2/4, what would 3/6 simplify to?",
            "topics_covered": ["equivalent fractions"],
        },
    },
    {
        "id": "good_magnets_default",
        "subject": "science",
        "grade": 6,
        "chapter": "Exploring Magnets",
        "topic": "Poles of a magnet",
        "student_memory": {},
        "expected_passed": True,
        "defect_type": None,
        "teaching_output": {
            "headline": "Every magnet has a north pole and a south pole",
            "explanation": (
                "1. A magnet attracts iron and steel objects. "
                "2. It has two poles - north and south. "
                "3. Like poles repel each other, unlike poles attract. "
                "4. A magnetic compass uses this to always point north-south."
            ),
            "real_world_example": "A compass needle lines up with Earth's magnetic poles to show direction.",
            "analogy": "It's like two friends who only want to sit next to someone they get along with - N and S sit together happily, but N next to N pushes apart.",
            "diagram_description": "A bar magnet with N labeled on one end and S on the other, with curved field lines looping from N to S.",
            "guiding_question": "If you bring two north poles close together, what happens?",
            "topics_covered": ["magnets", "poles"],
        },
    },
    {
        "id": "good_magnets_scaffolded_for_weak",
        "subject": "science",
        "grade": 6,
        "chapter": "Exploring Magnets",
        "topic": "Poles of a magnet",
        "student_memory": {"mastery": {"poles of a magnet": 0.2}, "weak_topics": ["poles of a magnet"]},
        "expected_passed": True,
        "defect_type": None,
        "teaching_output": {
            "headline": "Every magnet has a north pole and a south pole",
            "explanation": (
                "1. Let's start simple - a magnet is a special object that pulls iron and steel toward it. "
                "2. Every magnet, no matter its shape, has exactly two ends, called poles - north and south. "
                "3. Now the important rule: like poles (N-N or S-S) push apart, unlike poles (N-S) pull together. "
                "4. A compass needle is itself a tiny magnet, so its north pole always turns to point toward north."
            ),
            "real_world_example": "A compass needle lines up with Earth's magnetic poles to show direction.",
            "analogy": "It's like two friends who only want to sit next to someone they get along with.",
            "diagram_description": "A bar magnet with N labeled on one end and S on the other, with curved field lines looping from N to S.",
            "guiding_question": "If you bring two north poles close together, what happens?",
            "topics_covered": ["magnets", "poles"],
        },
    },
    {
        "id": "bad_fractions_ungrounded",
        "subject": "math",
        "grade": 6,
        "chapter": "Fractions",
        "topic": "Equivalent fractions",
        "student_memory": {},
        "expected_passed": False,
        "defect_type": "ungrounded",
        "teaching_output": {
            "headline": "Fractions were invented in 1850 by British mathematicians",
            "explanation": (
                "1. Fractions were first written down in London in the year 1850. "
                "2. A fraction must always have a numerator over 100. "
                "3. To add two fractions you always multiply their numerators together. "
                "4. Every valid fraction must have a denominator greater than 10."
            ),
            "ncert_example": "The guava problem shows fractions must always be written as percentages.",
            "analogy": "It's like a pizza cut into a random number of slices, no rule needed.",
            "common_mistake": "There are no common mistakes with fractions.",
            "guiding_question": "In what year were percentages invented?",
            "topics_covered": ["fractions"],
        },
    },
    {
        "id": "bad_magnets_ungrounded",
        "subject": "science",
        "grade": 6,
        "chapter": "Exploring Magnets",
        "topic": "Poles of a magnet",
        "student_memory": {},
        "expected_passed": False,
        "defect_type": "ungrounded",
        "teaching_output": {
            "headline": "A magnet's pulling power doubles every time you cut it in half",
            "explanation": (
                "1. Magnets are made only of pure iron mined in Odisha. "
                "2. Cutting a magnet in half doubles its strength every time. "
                "3. A magnet stops working permanently after exactly 100 uses. "
                "4. Only red and blue magnets have poles - other colours do not."
            ),
            "real_world_example": "Doubling magnets this way is used to build unlimited free energy machines.",
            "analogy": "It's like a photocopier that makes stronger copies each time.",
            "diagram_description": "A magnet being cut in half repeatedly with arrows showing increasing strength.",
            "guiding_question": "How many cuts would it take to make a magnet infinitely strong?",
            "topics_covered": ["magnets"],
        },
    },
    {
        "id": "bad_magnets_curriculum_inappropriate",
        "subject": "science",
        "grade": 6,
        "chapter": "Exploring Magnets",
        "topic": "Poles of a magnet",
        "student_memory": {},
        "expected_passed": False,
        "defect_type": "curriculum_inappropriate",
        "teaching_output": {
            "headline": "Magnetic dipole moments arise from electron spin and orbital angular momentum",
            "explanation": (
                "1. Ferromagnetic domains align under an external H field per the Landau-Lifshitz-Gilbert equation. "
                "2. The hysteresis loop describes remnant magnetization and coercivity. "
                "3. Magnetic flux density is given by B = mu_0 (H + M). "
                "4. The Curie temperature marks the phase transition to a paramagnetic state."
            ),
            "real_world_example": "MRI machines use superconducting magnets generating several tesla of field strength.",
            "analogy": "Like aligning compass needles in a strong uniform field, per classical electrodynamics.",
            "diagram_description": "A B-H hysteresis loop with coercivity and remanence labeled on each axis.",
            "guiding_question": "Derive the magnetization curve from the Langevin function.",
            "topics_covered": ["magnetism", "electromagnetism"],
        },
    },
    {
        "id": "bad_fractions_wrong_difficulty",
        "subject": "math",
        "grade": 6,
        "chapter": "Fractions",
        "topic": "Equivalent fractions",
        "student_memory": {"mastery": {"equivalent fractions": 0.2}, "weak_topics": ["equivalent fractions"]},
        "expected_passed": False,
        "defect_type": "wrong_difficulty",
        "teaching_output": {
            "headline": "Equivalent fractions",
            "explanation": "Multiply the numerator and denominator by the same number. That's it.",
            "ncert_example": "Three guavas together weigh 1 kg; each guava weighs about 1/3 kg.",
            "analogy": "Like a pizza.",
            "common_mistake": "None.",
            "guiding_question": "What is 3/6 in lowest terms?",
            "topics_covered": ["equivalent fractions"],
        },
    },
]


def _fetch_context(subject: str, grade: int, chapter: str, topic: str) -> list[dict]:
    return retrieve(topic, subject, grade, chapter=None, top_k=5)


def run_eval() -> dict:
    results = []
    context_cache: dict[tuple[str, int, str], list[dict]] = {}

    for seed in _SEEDS:
        cache_key = (seed["subject"], seed["grade"], seed["topic"])
        if cache_key not in context_cache:
            context_cache[cache_key] = _fetch_context(
                seed["subject"], seed["grade"], seed["chapter"], seed["topic"]
            )
        context = context_cache[cache_key]

        memory = seed["student_memory"]
        student_memory_json = json.dumps(
            {
                "learning_style": memory.get("learning_style", "text"),
                "mastery_on_this_topic": memory.get("mastery", {}).get(seed["topic"].lower(), "unknown (no prior data)"),
                "flags": ["weak_topic"] if seed["topic"].lower() in {t.lower() for t in memory.get("weak_topics", [])} else ["none"],
            },
            ensure_ascii=False,
        )

        system_prompt, prompt_version = render_versioned(
            "reflection",
            teaching_output=json.dumps(seed["teaching_output"], ensure_ascii=False),
            context=_format_context(context),
            chapter=seed["chapter"],
            topic=seed["topic"],
            grade=seed["grade"],
            student_memory=student_memory_json,
        )

        try:
            decision = call_groq_with_retry(
                REFLECTION_MODEL,
                system_prompt,
                "Audit this teaching output now.",
                prompt_name="reflection",
                prompt_version=prompt_version,
            )
            actual_passed = bool(decision.get("passed", True))
            error = None
        except Exception as exc:  # pragma: no cover - network/API failure path
            actual_passed = None
            error = str(exc)
            decision = {}

        results.append(
            {
                "id": seed["id"],
                "defect_type": seed["defect_type"],
                "expected_passed": seed["expected_passed"],
                "actual_passed": actual_passed,
                "correct": actual_passed == seed["expected_passed"],
                "decision": decision,
                "error": error,
            }
        )

    scored = [r for r in results if r["actual_passed"] is not None]
    # Positive class = "should fail" (expected_passed is False) - that's the
    # case reflection exists to catch.
    tp = sum(1 for r in scored if not r["expected_passed"] and not r["actual_passed"])
    fp = sum(1 for r in scored if r["expected_passed"] and not r["actual_passed"])
    fn = sum(1 for r in scored if not r["expected_passed"] and r["actual_passed"])
    tn = sum(1 for r in scored if r["expected_passed"] and r["actual_passed"])

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None

    return {
        "total": len(results),
        "scored": len(scored),
        "accuracy": round(sum(1 for r in scored if r["correct"]) / len(scored), 2) if scored else None,
        "precision": round(precision, 2) if precision is not None else None,
        "recall": round(recall, 2) if recall is not None else None,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "results": results,
    }


def main() -> None:
    report = run_eval()
    print(f"\nReflection Agent eval - {report['scored']}/{report['total']} scored (API errors excluded)")
    print(f"Accuracy: {report['accuracy']:.0%}" if report["accuracy"] is not None else "Accuracy: n/a")
    print(f"Precision (catching bad output): {report['precision']}")
    print(f"Recall (catching bad output): {report['recall']}")
    cm = report["confusion_matrix"]
    print(f"Confusion matrix: TP={cm['tp']} FP={cm['fp']} FN={cm['fn']} TN={cm['tn']}\n")

    for r in report["results"]:
        mark = "OK" if r["correct"] else "MISS"
        print(
            f"  [{mark}] {r['id']:35s} defect={str(r['defect_type']):22s} "
            f"expected_passed={r['expected_passed']!s:5s} actual_passed={r['actual_passed']}"
        )
        if r["error"]:
            print(f"        error: {r['error']}")


if __name__ == "__main__":
    main()
