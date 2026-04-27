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
