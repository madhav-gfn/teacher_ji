import type { Subject } from "../api/client";

export const curriculum: Record<Subject, Record<number, Record<string, string[]>>> = {
  math: {
    6: {
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
      Fractions: [
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
      Symmetry: [
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
    7: {
      Integers: [
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
    8: {
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
  science: {
    6: {
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
    7: {
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
    8: {
      "Crop Production and Management": [
        "Agricultural practices",
        "Basic practices of crop production",
        "Preparation of soil",
        "Sowing and irrigation",
        "Protection from weeds and harvesting",
      ],
      Microorganisms: [
        "Types of microorganisms",
        "Useful microorganisms",
        "Harmful microorganisms",
        "Food preservation",
      ],
    },
  },
  sst: {
    6: {
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
    7: {
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
    8: {
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
};

export const subjectMeta: Record<
  Subject,
  { label: string; accent: string; softAccent: string }
> = {
  math: {
    label: "Mathematics",
    accent: "text-purple-700 bg-purple-50 border-purple-100",
    softAccent: "bg-purple-50 text-purple-700",
  },
  science: {
    label: "Science",
    accent: "text-teal-700 bg-teal-50 border-teal-100",
    softAccent: "bg-teal-50 text-teal-700",
  },
  sst: {
    label: "Social Studies",
    accent: "text-amber-700 bg-amber-50 border-amber-100",
    softAccent: "bg-amber-50 text-amber-700",
  },
};

export function getChapters(grade: number | null, subject: Subject | null): string[] {
  if (!grade || !subject) {
    return [];
  }

  return Object.keys(curriculum[subject][grade] ?? {});
}

export function getTopics(
  grade: number | null,
  subject: Subject | null,
  chapter: string | null,
): string[] {
  if (!grade || !subject || !chapter) {
    return [];
  }

  return curriculum[subject][grade]?.[chapter] ?? [];
}

export function getNextChapter(
  grade: number,
  subject: Subject,
  chapter: string,
): string | null {
  const chapters = getChapters(grade, subject);
  const currentIndex = chapters.findIndex((item) => item === chapter);
  if (currentIndex === -1 || currentIndex === chapters.length - 1) {
    return null;
  }

  return chapters[currentIndex + 1];
}
