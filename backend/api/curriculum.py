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
            "Patterns in Mathematics": [
                "Patterns in everyday life",
                "Number patterns",
                "Shape patterns",
                "Growing patterns",
            ],
            "Lines and Angles": [
                "Points, lines and rays",
                "Angles and turns",
                "Types of angles",
                "Parallel and intersecting lines",
            ],
            "Number Play": [
                "Numbers in daily life",
                "Large numbers and place value",
                "Digit puzzles",
                "Number patterns",
            ],
            "Data Handling and Presentation": [
                "Collecting data",
                "Organising data",
                "Pictographs and bar graphs",
                "Interpreting data",
            ],
            "Prime Time": [
                "Factors and multiples",
                "Prime and composite numbers",
                "Common factors and common multiples",
                "Divisibility patterns",
            ],
            "Perimeter and Area": [
                "Perimeter of rectangles and squares",
                "Area by counting squares",
                "Area of rectangles",
                "Solving perimeter and area problems",
            ],
            "Fractions": [
                "Fractions as equal parts",
                "Reading and representing fractions",
                "Equivalent fractions",
                "Comparing fractions",
            ],
            "Playing with Constructions": [
                "Drawing circles",
                "Constructing line segments",
                "Constructing perpendiculars",
                "Using ruler and compass",
            ],
            "Symmetry": [
                "Line symmetry",
                "Finding lines of symmetry",
                "Symmetry in shapes",
                "Creating symmetric figures",
            ],
            "The Other Side of Zero": [
                "Understanding zero and negatives",
                "Integers in daily life",
                "Number line with negative numbers",
                "Comparing integers",
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
              "The Wonderful World of Science": [
                          "Science as exploration",
                          "Asking questions and curiosity",
                          "Understanding the natural world"
              ],
              "Diversity in the Living World": [
                          "Variety of plants and animals",
                          "Grouping plants and animals",
                          "Features of different living things"
              ],
              "Mindful Eating: A Path to a Healthy Body": [
                          "Nutrients in food",
                          "Balanced diet",
                          "Healthy eating habits"
              ],
              "Exploring Magnets": [
                          "Discovery of magnets",
                          "Magnetic and non-magnetic materials",
                          "Poles of a magnet"
              ],
              "Measurement of Length and Motion": [
                          "Standard units of measurement",
                          "Measuring length",
                          "Types of motion"
              ],
              "Materials Around Us": [
                          "Properties of materials",
                          "Sorting materials into groups",
                          "States of matter"
              ],
              "Temperature and its Measurement": [
                          "Hot and cold",
                          "Measuring temperature",
                          "Thermometers"
              ],
              "A Journey through States of Water": [
                          "Water as solid, liquid, gas",
                          "Evaporation and condensation",
                          "Water cycle"
              ],
              "Methods of Separation in Everyday Life": [
                          "Mixtures and pure substances",
                          "Methods of separation",
                          "Reversible and irreversible changes"
              ],
              "Living Creatures: Exploring their Characteristics": [
                          "Characteristics of living beings",
                          "Habitat and adaptation",
                          "Living and non-living things"
              ],
              "Nature's Treasures": [
                          "Natural resources",
                          "Conservation of resources",
                          "Importance of forests"
              ],
              "Beyond Earth": [
                          "The solar system",
                          "Stars and constellations",
                          "Space exploration"
              ]
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
              "Locating Places on the Earth": [
                          "Globes and maps",
                          "Latitudes and longitudes",
                          "Standard time"
              ],
              "Oceans and Continents": [
                          "Major oceans of the world",
                          "Continents and their features",
                          "Earth's surface"
              ],
              "Landforms and Life": [
                          "Mountains, plateaus, and plains",
                          "Life in different landforms",
                          "Adaptation to environment"
              ],
              "Timeline and Sources of History": [
                          "Understanding timelines",
                          "Archaeological sources",
                          "Literary sources"
              ],
              "India, That Is Bharat": [
                          "Geographical features of India",
                          "Unity in diversity",
                          "The concept of Bharat"
              ],
              "The Beginnings of Indian Civilisation": [
                          "Early humans in India",
                          "The Indus Valley Civilisation",
                          "Vedic period"
              ],
              "India's Cultural Roots": [
                          "Languages and literature",
                          "Art and architecture",
                          "Religions and philosophies"
              ],
              "Unity in Diversity, or 'Many in the One'": [
                          "Cultural diversity of India",
                          "Festivals and traditions",
                          "Shared values and heritage"
              ],
              "Family and Community": [
                          "Role of the family",
                          "Types of communities",
                          "Living together"
              ],
              "Grassroots Democracy - Part 1 Governance": [
                          "What is governance?",
                          "Levels of government",
                          "Democratic principles"
              ],
              "Grassroots Democracy - Part 2 Local Government in Rural Areas": [
                          "Panchayati Raj system",
                          "Gram Sabha and Gram Panchayat",
                          "Functions of local government"
              ],
              "Grassroots Democracy - Part 3 Local Government in Urban Areas": [
                          "Municipal Corporations",
                          "Municipal Councils",
                          "Urban administration"
              ],
              "The Value of Work": [
                          "Different types of work",
                          "Dignity of labour",
                          "Economic value of work"
              ],
              "Economic Activities Around Us": [
                          "Primary, secondary, tertiary sectors",
                          "Agriculture and industries",
                          "Services and trade"
              ]
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
