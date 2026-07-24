"""
Curriculum prerequisite map: which topics a concept depends on.

Structure:
    PREREQUISITES[subject][topic] = [ordered list of prerequisite topics]

This is deliberately separate from `curriculum.py` (which only orders topics
*within* a chapter). This map crosses chapter and grade boundaries - e.g. a
class 7 "Division of fractions" topic depends on class 6 fractions topics.

All keys are lowercase to match case-insensitive lookups in
`get_prerequisites`. Coverage favors the topics that actually appear in
`NCERT_CURRICULUM` (curriculum.py) plus a few common canonical names
(e.g. "percentages") a student or agent might ask about directly.
"""
from __future__ import annotations

PREREQUISITES: dict[str, dict[str, list[str]]] = {
    "math": {
        "fractions as equal parts": ["numbers in daily life", "large numbers and place value"],
        "reading and representing fractions": ["fractions as equal parts"],
        "equivalent fractions": ["fractions as equal parts", "reading and representing fractions"],
        "comparing fractions": ["equivalent fractions"],
        "fractions": ["equivalent fractions", "comparing fractions"],
        "decimals": ["fractions", "large numbers and place value"],
        "multiplication of fractions": ["equivalent fractions", "comparing fractions"],
        "division of fractions": ["multiplication of fractions", "fractions as equal parts"],
        "multiplication of decimals": ["multiplication of fractions", "decimals"],
        "division of decimals": ["division of fractions", "multiplication of decimals"],
        "percentages": ["decimals", "fractions"],
        "understanding zero and negatives": ["numbers in daily life"],
        "integers in daily life": ["understanding zero and negatives"],
        "number line with negative numbers": ["understanding zero and negatives"],
        "comparing integers": ["number line with negative numbers"],
        "introduction to integers": ["understanding zero and negatives", "comparing integers"],
        "addition and subtraction of integers": ["introduction to integers"],
        "multiplication of integers": ["addition and subtraction of integers"],
        "division of integers": ["multiplication of integers"],
        "rational numbers": ["fractions and decimals", "introduction to integers"],
        "properties of rational numbers": ["rational numbers"],
        "representation on number line": ["properties of rational numbers", "number line with negative numbers"],
        "operations on rational numbers": ["properties of rational numbers", "multiplication of integers"],
        "finding rational numbers between two rationals": ["operations on rational numbers"],
        "introduction and solving linear equations": ["operations on rational numbers"],
        "equations with variables on both sides": ["introduction and solving linear equations"],
        "reducing equations to simpler form": ["equations with variables on both sides"],
        "factors and multiples": ["numbers in daily life", "large numbers and place value"],
        "prime and composite numbers": ["factors and multiples"],
        "common factors and common multiples": ["factors and multiples", "prime and composite numbers"],
        "divisibility patterns": ["common factors and common multiples"],
        "perimeter of rectangles and squares": ["large numbers and place value"],
        "area by counting squares": ["perimeter of rectangles and squares"],
        "area of rectangles": ["area by counting squares", "perimeter of rectangles and squares"],
        "solving perimeter and area problems": ["area of rectangles"],
        "points, lines and rays": ["patterns in everyday life"],
        "angles and turns": ["points, lines and rays"],
        "types of angles": ["angles and turns"],
        "parallel and intersecting lines": ["types of angles"],
        "line symmetry": ["shape patterns"],
        "finding lines of symmetry": ["line symmetry"],
        "symmetry in shapes": ["line symmetry", "finding lines of symmetry"],
        "creating symmetric figures": ["symmetry in shapes"],
    },
    "science": {
        "photosynthesis": ["mode of nutrition in plants"],
        "nutrients replenishment in soil": ["photosynthesis"],
        "digestion in humans": ["modes of nutrition in animals"],
        "digestion in grass-eating animals": ["digestion in humans"],
        "basic practices of crop production": ["agricultural practices"],
        "preparation of soil": ["basic practices of crop production"],
        "sowing and irrigation": ["preparation of soil"],
        "protection from weeds and harvesting": ["sowing and irrigation"],
        "useful microorganisms": ["types of microorganisms"],
        "harmful microorganisms": ["types of microorganisms"],
        "food preservation": ["harmful microorganisms"],
        "evaporation and condensation": ["water as solid, liquid, gas"],
        "water cycle": ["evaporation and condensation"],
    },
    "sst": {
        "latitudes and longitudes": ["globes and maps"],
        "standard time": ["latitudes and longitudes"],
        "levels of government": ["what is governance?"],
        "democratic principles": ["levels of government"],
        "panchayati raj system": ["what is governance?", "levels of government"],
        "gram sabha and gram panchayat": ["panchayati raj system"],
        "functions of local government": ["gram sabha and gram panchayat"],
        "municipal corporations": ["levels of government", "panchayati raj system"],
        "municipal councils": ["municipal corporations"],
        "urban administration": ["municipal councils"],
        "new dynasties": ["tracing changes through a thousand years"],
        "administration in the kingdoms": ["new dynasties"],
        "prashastis and land grants": ["administration in the kingdoms"],
        "company establishes power": ["east india company comes east"],
        "company rule expands": ["company establishes power"],
        "the doctrine of lapse": ["company rule expands"],
    },
}


def get_prerequisites(subject: str, topic: str) -> dict:
    """Look up prerequisite topics for a concept.

    Matching is case-insensitive with a substring fallback (mirrors
    `curriculum.get_chapter_topics`), since callers may pass a topic phrased
    slightly differently than the curriculum's canonical wording.
    """
    subject_map = PREREQUISITES.get(subject.strip().lower(), {})
    topic_key = topic.strip().lower()

    if topic_key in subject_map:
        return {"topic": topic, "prerequisites": list(subject_map[topic_key]), "found": True}

    for key, prereqs in subject_map.items():
        if key in topic_key or topic_key in key:
            return {"topic": topic, "prerequisites": list(prereqs), "found": True}

    return {"topic": topic, "prerequisites": [], "found": False}
