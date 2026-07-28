import { FormEvent, useState } from "react";

interface GuidingQuestionProps {
  question: string;
}

export function GuidingQuestion({ question }: GuidingQuestionProps) {
  const [thinking, setThinking] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    console.info("Guiding question response:", thinking);
    setSubmitted(true);
  };

  return (
    <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">
        Think About This
      </p>
      <p className="mt-3 text-lg font-semibold text-gray-900 dark:text-gray-100">{question}</p>

      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
        <textarea
          value={thinking}
          onChange={(event) => setThinking(event.target.value)}
          placeholder="Write how you are thinking about this..."
          className="min-h-28 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-purple-300 focus:bg-white focus:ring-2 focus:ring-purple-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-purple-700 dark:focus:bg-gray-900"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            This is logged locally for now. Backend submission can be wired later.
          </span>
          <button
            type="submit"
            className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-2 text-sm font-semibold text-purple-700 transition hover:border-purple-300 hover:bg-purple-100 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300 dark:hover:border-purple-700 dark:hover:bg-purple-900/40"
          >
            Submit Thinking
          </button>
        </div>
      </form>

      {submitted ? (
        <p className="mt-3 text-sm font-medium text-teal-700 dark:text-teal-300">
          Your thinking has been captured for this session.
        </p>
      ) : null}
    </section>
  );
}
