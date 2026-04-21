import type { FeedbackOutput } from "../api/client";

interface FeedbackPanelProps {
  feedback: FeedbackOutput;
}

const verdictMap = {
  correct: {
    label: "Correct",
    classes: "border-green-200 bg-green-50 text-green-700",
    symbol: "✓",
  },
  partially_correct: {
    label: "Partially Correct",
    classes: "border-orange-200 bg-orange-50 text-orange-700",
    symbol: "–",
  },
  incorrect: {
    label: "Incorrect",
    classes: "border-red-200 bg-red-50 text-red-700",
    symbol: "✕",
  },
} as const;

const strengthMap = {
  mastered: "bg-green-100 text-green-800",
  developing: "bg-amber-100 text-amber-800",
  needs_revision: "bg-red-100 text-red-800",
} as const;

export function FeedbackPanel({ feedback }: FeedbackPanelProps) {
  const verdict = verdictMap[feedback.verdict];

  return (
    <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
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

      <p className="mt-5 text-base leading-7 text-gray-800">{feedback.feedback}</p>
      <p className="mt-3 text-sm italic leading-6 text-gray-500">{feedback.encouragement}</p>

      {feedback.hint_if_wrong ? (
        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            Hint To Think About
          </p>
          <p className="mt-2 text-sm leading-6 text-blue-900">{feedback.hint_if_wrong}</p>
        </div>
      ) : null}
    </section>
  );
}
