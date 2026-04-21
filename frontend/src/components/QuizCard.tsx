import { useState } from "react";
import type { FeedbackOutput, QuizQuestion } from "../api/client";

interface QuizCardProps {
  question: QuizQuestion;
  feedback: FeedbackOutput | null;
  isSubmitting: boolean;
  onSubmit: (answer: string) => void;
}

const optionLetters = ["A", "B", "C", "D"];

function normalizeOptionText(option: string) {
  return option.replace(/^[A-D][).:\s-]+/i, "").trim();
}

export function QuizCard({ question, feedback, isSubmitting, onSubmit }: QuizCardProps) {
  const [typedAnswer, setTypedAnswer] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const isMcq = question.question_type === "mcq" && question.options?.length === 4;
  const correctAnswer = question.correct_answer.trim().toUpperCase();

  const handleOptionClick = (answer: string) => {
    setSelectedOption(answer);
    onSubmit(answer);
  };

  const optionState = (letter: string) => {
    if (!feedback) {
      return "border-purple-200 bg-white text-gray-900 hover:border-purple-500";
    }

    if (letter === correctAnswer) {
      return "border-green-200 bg-green-500 text-white";
    }

    if (letter === selectedOption && letter !== correctAnswer) {
      return "border-red-200 bg-red-500 text-white";
    }

    return "border-gray-200 bg-gray-50 text-gray-400";
  };

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-textbook">
      <div className="flex items-center justify-between gap-4">
        <span className="rounded-full bg-purple-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-purple-700">
          {question.difficulty}
        </span>
        <span className="text-xs font-medium uppercase tracking-[0.2em] text-gray-500">
          Concept: {question.concept_tested}
        </span>
      </div>

      <h2 className="mt-5 text-2xl font-bold leading-9 text-gray-950">{question.question}</h2>

      {isMcq ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {question.options?.map((option, index) => {
            const letter = optionLetters[index];
            const isSelected = selectedOption === letter;

            return (
              <button
                key={`${letter}-${option}`}
                type="button"
                disabled={isSubmitting || Boolean(feedback)}
                onClick={() => handleOptionClick(letter)}
                className={`flex min-h-24 items-start gap-4 rounded-2xl border px-5 py-4 text-left transition ${optionState(letter)}`}
              >
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-current text-sm font-bold">
                  {isSubmitting && isSelected ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  ) : (
                    letter
                  )}
                </span>
                <span className="text-sm leading-6">{normalizeOptionText(option)}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="mt-6 rounded-2xl border border-amber-100 bg-amber-50 p-5">
          <p className="text-sm font-semibold text-amber-900">
            The backend returned a short-answer question. The board still supports it safely.
          </p>
          <textarea
            value={typedAnswer}
            onChange={(event) => setTypedAnswer(event.target.value)}
            disabled={isSubmitting || Boolean(feedback)}
            className="mt-4 min-h-28 w-full rounded-xl border border-amber-200 bg-white px-4 py-3 text-sm outline-none focus:border-amber-400"
            placeholder="Type your answer"
          />
          <button
            type="button"
            disabled={isSubmitting || Boolean(feedback) || !typedAnswer.trim()}
            onClick={() => onSubmit(typedAnswer.trim())}
            className="mt-4 rounded-xl bg-purple-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
          >
            {isSubmitting ? "Checking answer..." : "Submit Answer"}
          </button>
        </div>
      )}
    </div>
  );
}
