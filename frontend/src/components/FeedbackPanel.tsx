import type { FeedbackOutput } from "../api/client";

interface FeedbackPanelProps {
  feedback: FeedbackOutput;
}

const verdictMap = {
  correct: {
    label: "Correct",
    classes: "border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950/30 dark:text-green-300",
    symbol: "✓",
  },
  partially_correct: {
    label: "Partially Correct",
    classes: "border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-900 dark:bg-orange-950/30 dark:text-orange-300",
    symbol: "–",
  },
  incorrect: {
    label: "Incorrect",
    classes: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300",
    symbol: "✕",
  },
} as const;

const strengthMap = {
  mastered: "bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-300",
  developing: "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300",
  needs_revision: "bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300",
} as const;

export function FeedbackPanel({ feedback }: FeedbackPanelProps) {
  const verdict = verdictMap[feedback.verdict];

  return (
    <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div
          className={`inline-flex items-center gap-3 rounded-full border px-4 py-2 text-sm font-semibold ${verdict.classes}`}
        >
          <span className="text-lg">{verdict.symbol}</span>
          <span>{verdict.label}</span>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${
            strengthMap[feedback.concept_strength]
          }`}
        >
          {feedback.concept_strength.replace("_", " ")}
        </span>
      </div>

      <p className="mt-5 text-base leading-7 text-gray-800 dark:text-gray-200">{feedback.feedback}</p>
      <p className="mt-3 text-sm italic leading-6 text-gray-500 dark:text-gray-400">{feedback.encouragement}</p>

      {feedback.hint_if_wrong ? (
        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 dark:border-blue-900 dark:bg-blue-950/30">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-700 dark:text-blue-300">
            Hint To Think About
          </p>
          <p className="mt-2 text-sm leading-6 text-blue-900 dark:text-blue-200">{feedback.hint_if_wrong}</p>
        </div>
      ) : null}
    </section>
  );
}
