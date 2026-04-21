"""
NCERT Curriculum definition and topic-progression helpers.

Structure:
    NCERT_CURRICULUM[subject][class_key][chapter_title] = [ordered list of topics]

All subject names are lowercase to match LearningState["subject"].
"""
from __future__ import annotations

NCERT_CURRICULUM: dict[str, dict[str, dict[str, list[str]]]] = {
    "math": {
        "class6": {
            "Knowing Our Numbers": [
                "Introduction to large numbers",
                "Comparing numbers",
                "Estimation",
                "Roman numerals",
            ],
            "Whole Numbers": [
                "Natural numbers and whole numbers",
                "Number line",
                "Properties of whole numbers",
                "Patterns in whole numbers",
            ],
            "Playing with Numbers": [
                "Factors and multiples",
                "Prime and composite numbers",
                "HCF and LCM",
                "Divisibility rules",
            ],
            "Basic Geometrical Ideas": [
                "Points, lines and line segments",
                "Rays and angles",
                "Triangles",
                "Quadrilaterals and circles",
            ],
        },
        "class7": {
            "Integers": [
                "Introduction to integers",
                "Addition and subtraction of integers",
                "Multiplication of integers",
                "Division of integers",
            ],
            "Fractions and Decimals": [
                "Multiplication of fractions",
                "Division of fractions",
                "Multiplication of decimals",
                "Division of decimals",
            ],
        },
        "class8": {
            "Rational Numbers": [
                "Properties of rational numbers",
                "Representation on number line",
                "Operations on rational numbers",
                "Finding rational numbers between two rationals",
            ],
            "Linear Equations in One Variable": [
                "Introduction and solving linear equations",
                "Equations with variables on both sides",
                "Reducing equations to simpler form",
                "Word problems",
            ],
        },
    },
    "science": {
        "class6": {
            "Food: Where Does It Come From?": [
                "Sources of food",
                "Plant parts as food",
                "Animal products as food",
                "Herbivores, carnivores and omnivores",
            ],
            "Components of Food": [
                "Nutrients in food",
                "Carbohydrates and fats",
                "Proteins and vitamins",
                "Minerals and water",
                "Balanced diet and deficiency diseases",
            ],
            "Fibre to Fabric": [
                "Types of fibres",
                "Plant fibres: cotton and jute",
                "Animal fibres: wool and silk",
                "From fibre to fabric: spinning and weaving",
            ],
            "Sorting Materials into Groups": [
                "Properties of materials",
                "Transparency, solubility and density",
                "Metals and non-metals",
            ],
        },
        "class7": {
            "Nutrition in Plants": [
                "Mode of nutrition in plants",
                "Photosynthesis",
                "Nutrients replenishment in soil",
            ],
            "Nutrition in Animals": [
                "Modes of nutrition in animals",
                "Digestion in humans",
                "Digestion in grass-eating animals",
            ],
        },
        "class8": {
            "Crop Production and Management": [
                "Agricultural practices",
                "Basic practices of crop production",
                "Preparation of soil",
                "Sowing and irrigation",
                "Protection from weeds and harvesting",
            ],
            "Microorganisms": [
                "Types of microorganisms",
                "Useful microorganisms",
                "Harmful microorganisms",
                "Food preservation",
            ],
        },
    },
    "sst": {
        "class6": {
            "What, Where, How and When?": [
                "Sources of history",
                "Finding out about the past",
                "What people ate, wore and where they lived",
                "Names of the land and people",
            ],
            "From Hunting-Gathering to Growing Food": [
                "Hunter-gatherers of the subcontinent",
                "Beginning of farming and herding",
                "A closer look: Mehrgarh",
                "Changes brought by farming",
            ],
            "In the Earliest Cities": [
                "The story of Harappa",
                "What was special about Harappan cities",
                "Life in Harappan cities",
                "Decline of Harappan cities",
            ],
            "The Earth in the Solar System": [
                "The solar system",
                "The moon",
                "The earth: shape and size",
                "Latitudes and longitudes",
            ],
        },
        "class7": {
            "Tracing Changes Through a Thousand Years": [
                "New and old terminologies",
                "Historians and their sources",
                "New social and political groups",
                "Regions and empires",
            ],
            "New Kings and Kingdoms": [
                "New dynasties",
                "Administration in the kingdoms",
                "Prashastis and land grants",
            ],
        },
        "class8": {
            "How, When and Where": [
                "How important are dates in history?",
                "Colonial administration and record keeping",
                "What do official records tell us?",
            ],
            "From Trade to Territory": [
                "East India Company comes east",
                "Company establishes power",
                "Company rule expands",
                "The Doctrine of Lapse",
            ],
        },
    },
}


def _class_key(grade: int) -> str:
    """Convert grade integer to curriculum dict key, e.g. 6 → 'class6'."""
    return f"class{grade}"


def get_chapter_topics(subject: str, grade: int, chapter: str) -> list[str]:
    """Return the ordered topic list for a given subject/grade/chapter.

    Returns an empty list if the chapter is not found in the curriculum.
    Subject matching is case-insensitive; chapter matching is case-insensitive
    and falls back to a substring check.
    """
    subject_data = NCERT_CURRICULUM.get(subject.strip().lower(), {})
    grade_data = subject_data.get(_class_key(grade), {})

    # Exact match first
    if chapter in grade_data:
        return list(grade_data[chapter])

    # Case-insensitive / substring fallback
    chapter_lower = chapter.strip().lower()
    for key, topics in grade_data.items():
        if key.strip().lower() == chapter_lower or chapter_lower in key.strip().lower():
            return list(topics)

    return []


def get_next_topic(
    subject: str,
    grade: int,
    chapter: str,
    completed_topics: list[str],
) -> str | None:
    """Return the first topic in the chapter not yet in completed_topics.

    Returns None when all topics have been covered (chapter complete).
    Comparison is case-insensitive and strips surrounding whitespace.
    """
    all_topics = get_chapter_topics(subject, grade, chapter)
    done = {t.strip().lower() for t in completed_topics}
    for topic in all_topics:
        if topic.strip().lower() not in done:
            return topic
    return None


def get_remaining_topics(
    subject: str,
    grade: int,
    chapter: str,
    completed_topics: list[str],
) -> list[str]:
    """Return all topics not yet covered in a chapter, in order."""
    all_topics = get_chapter_topics(subject, grade, chapter)
    done = {t.strip().lower() for t in completed_topics}
    return [t for t in all_topics if t.strip().lower() not in done]
