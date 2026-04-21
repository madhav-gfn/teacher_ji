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
    <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500">
        Think About This
      </p>
      <p className="mt-3 text-lg font-semibold text-gray-900">{question}</p>

      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
        <textarea
          value={thinking}
          onChange={(event) => setThinking(event.target.value)}
          placeholder="Write how you are thinking about this..."
          className="min-h-28 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-purple-300 focus:bg-white focus:ring-2 focus:ring-purple-100"
        />
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-gray-500">
            This is logged locally for now. Backend submission can be wired later.
          </span>
          <button
            type="submit"
            className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-2 text-sm font-semibold text-purple-700 transition hover:border-purple-300 hover:bg-purple-100"
          >
            Submit Thinking
          </button>
        </div>
      </form>

      {submitted ? (
        <p className="mt-3 text-sm font-medium text-teal-700">
          Your thinking has been captured for this session.
        </p>
      ) : null}
    </section>
  );
}
