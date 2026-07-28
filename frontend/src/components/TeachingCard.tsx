import { GuidingQuestion } from "./GuidingQuestion";
import { Markdown } from "./Markdown";
import type { Subject, TeachingOutput } from "../api/client";
import { subjectMeta } from "../data/curriculum";

interface TeachingCardProps {
  subject: Subject;
  chapter: string;
  topic: string;
  teachingOutput: TeachingOutput;
  onNext: () => void;
  onExplainDifferently: () => void;
  isAdvancing: boolean;
  isRefreshing: boolean;
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]">
      <path d="M12 3 2.5 20.5h19L12 3Z" />
      <path d="M12 9v5" />
      <circle cx="12" cy="17.25" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

function asParagraphs(value: any): string[] {
  if (Array.isArray(value)) {
    return value.map(String);
  }

  if (typeof value === "string") {
    return value
      .split(/\n+/)
      .map((item) => item.replace(/^\d+[).]\s*/, "").trim())
      .filter(Boolean);
  }

  if (!value) {
    return [];
  }

  return [String(value)];
}

export function TeachingCard({
  subject,
  chapter,
  topic,
  teachingOutput,
  onNext,
  onExplainDifferently,
  isAdvancing,
  isRefreshing,
}: TeachingCardProps) {
  const meta = subjectMeta[subject];
  const explanationSteps = asParagraphs(teachingOutput.explanation);
  const exampleContent =
    subject === "math"
      ? teachingOutput.ncert_example
      : subject === "science"
        ? teachingOutput.real_world_example
        : subject === "custom"
          ? teachingOutput.example
          : teachingOutput.story;
  const keyPoints = teachingOutput.key_points ?? teachingOutput.key_facts;

  return (
    <div className="space-y-5">
      <section className={`rounded-2xl border px-6 py-5 shadow-sm ${meta.accent}`}>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em]">
            {meta.label}
          </span>
          <span className="text-sm font-medium opacity-80">{chapter}</span>
        </div>
        <h1 className="mt-4 text-3xl font-bold">{topic}</h1>
      </section>

      <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">
          The Big Idea
        </p>
        <div className="mt-4 border-l-4 border-purple-600 pl-5">
          <h2 className="text-2xl font-bold text-gray-950 dark:text-white">
            {teachingOutput.headline ?? "Teaching content will appear here."}
          </h2>
        </div>
      </section>

      <section className="rounded-xl border border-gray-100 bg-gray-50 p-6 shadow-sm dark:border-gray-800 dark:bg-gray-800/40">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">Explanation</p>
        <div className="mt-5 space-y-4">
          {explanationSteps.map((step, index) => (
            <div key={`${index + 1}-${step}`} className="flex gap-4">
              <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                {subject === "math" ? (
                  <Markdown className="rounded-xl border border-purple-100 bg-white px-4 py-3 text-sm text-gray-800 dark:border-purple-900 dark:bg-gray-900 dark:text-gray-200">
                    {step}
                  </Markdown>
                ) : (
                  <Markdown className="text-base text-gray-800 dark:text-gray-200">{step}</Markdown>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {exampleContent ? (
        <section className="rounded-xl border border-yellow-100 bg-yellow-50 p-6 shadow-sm dark:border-yellow-900 dark:bg-yellow-950/30">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-yellow-800 dark:text-yellow-300">
            {subject === "custom" ? "From Your Document" : "From Your NCERT Book"}
          </p>
          <Markdown className="mt-3 text-base text-yellow-950 dark:text-yellow-100">{exampleContent}</Markdown>
        </section>
      ) : null}

      {keyPoints?.length ? (
        <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">
            Key Points To Remember
          </p>
          <ul className="mt-4 space-y-2">
            {keyPoints.map((point) => (
              <li key={point} className="flex gap-3 text-base leading-7 text-gray-800 dark:text-gray-200">
                <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-purple-600" />
                <Markdown className="min-w-0 flex-1">{point}</Markdown>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl border border-teal-100 bg-teal-50 p-6 shadow-sm dark:border-teal-900 dark:bg-teal-950/30">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-800 dark:text-teal-300">
          Remember It As
        </p>
        <div className="mt-3 space-y-3">
          {teachingOutput.analogy ? (
            <Markdown className="text-base text-teal-950 dark:text-teal-100">{teachingOutput.analogy}</Markdown>
          ) : null}
          {teachingOutput.mnemonic ? (
            <Markdown className="text-base text-teal-950 dark:text-teal-100">{teachingOutput.mnemonic}</Markdown>
          ) : null}
          {subject === "sst" && teachingOutput.connection_to_present ? (
            <Markdown className="rounded-xl border border-teal-200 bg-white px-4 py-3 text-sm text-gray-700 dark:border-teal-800 dark:bg-gray-900 dark:text-gray-300">
              {teachingOutput.connection_to_present}
            </Markdown>
          ) : null}
          {subject === "sst" && teachingOutput.timeline?.length ? (
            <div className="flex gap-3 overflow-x-auto pb-2">
              {teachingOutput.timeline.map((item) => (
                <div
                  key={`${item.year}-${item.event}`}
                  className="min-w-52 rounded-2xl border border-teal-200 bg-white px-4 py-4 dark:border-teal-800 dark:bg-gray-900"
                >
                  <p className="text-sm font-bold text-teal-700 dark:text-teal-300">{item.year}</p>
                  <p className="mt-2 text-sm leading-6 text-gray-700 dark:text-gray-300">{item.event}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      {(subject === "math" || subject === "custom") && teachingOutput.common_mistake ? (
        <section className="rounded-xl border border-red-100 bg-red-50 p-6 shadow-sm dark:border-red-900 dark:bg-red-950/30">
          <div className="flex items-center gap-3 text-red-700 dark:text-red-300">
            <WarningIcon />
            <p className="text-sm font-semibold uppercase tracking-[0.24em]">
              Common Mistake To Avoid
            </p>
          </div>
          <Markdown className="mt-3 text-base text-red-950 dark:text-red-100">{teachingOutput.common_mistake}</Markdown>
        </section>
      ) : null}

      {subject === "science" && teachingOutput.diagram_description ? (
        <section className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">Diagram</p>
          <div className="mt-4 rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-4 dark:border-gray-700 dark:bg-gray-800/40">
            <Markdown className="text-sm italic text-gray-600 dark:text-gray-400">
              {`Visualize this: ${teachingOutput.diagram_description}`}
            </Markdown>
          </div>
          <p className="mt-3 text-sm font-medium text-teal-700 dark:text-teal-300">Draw in notebook</p>
        </section>
      ) : null}

      {teachingOutput.guiding_question ? (
        <GuidingQuestion question={teachingOutput.guiding_question} />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-100 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <button
          type="button"
          onClick={onNext}
          disabled={isAdvancing}
          className="rounded-xl bg-purple-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
        >
          {isAdvancing ? "Loading next topic..." : "I understand — Next Topic"}
        </button>
        <button
          type="button"
          onClick={onExplainDifferently}
          disabled={isRefreshing}
          className="rounded-xl border border-gray-200 px-5 py-3 text-sm font-semibold text-gray-700 transition hover:border-purple-200 hover:text-purple-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:border-purple-700 dark:hover:text-purple-300 dark:disabled:border-gray-800 dark:disabled:text-gray-600"
        >
          {isRefreshing ? "Rebuilding explanation..." : "Explain differently"}
        </button>
      </div>
    </div>
  );
}
