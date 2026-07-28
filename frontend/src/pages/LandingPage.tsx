import { SignIn } from "@clerk/react";

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

const pipelineStages = [
  {
    title: "Supervisor",
    detail: "An LLM decision node reads the student's mastery model and picks the next move: teach, revise a prerequisite, quiz, or wrap up.",
  },
  {
    title: "Learning Agent",
    detail: "Math, Science, or Social Studies agent chooses its own tools - searches the NCERT textbook, looks up prerequisites, verifies arithmetic - before answering.",
  },
  {
    title: "Reflection Agent",
    detail: "A second, cheaper model checks the answer is grounded in the retrieved textbook passage, grade-appropriate, and paced right - one bounded retry on failure.",
  },
  {
    title: "Memory Model",
    detail: "Mastery and confidence per topic persist across sessions, so a student who struggled with Division actually gets a refresher before Fractions next time.",
  },
];

const features = [
  {
    title: "Agentic core, not a scripted pipeline",
    detail: "A Supervisor plans the next step, agents choose their own tools, and a Reflection Agent audits the output before the student sees it.",
  },
  {
    title: "Live streaming chat",
    detail: "Token-level SSE streaming on every teaching turn - watch the explanation get written, not a spinner.",
  },
  {
    title: "Real mastery tracking",
    detail: "Per-topic mastery and confidence persist across sessions and actually change what gets taught next.",
  },
  {
    title: "Inspectable by design",
    detail: "Every LLM call is traced (LangSmith) and tagged with the prompt version that produced it - nothing is a black box.",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-stone-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700 dark:text-purple-300">
          Daskalos
        </p>
        <button
          type="button"
          onClick={() => scrollToId("get-started")}
          className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:border-purple-200 hover:text-purple-700 dark:border-gray-700 dark:text-gray-300 dark:hover:border-purple-700 dark:hover:text-purple-300"
        >
          Sign in
        </button>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-16 pt-8 sm:pt-16">
        <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700 dark:text-purple-300">
              NCERT Multi-Agent Learning Platform
            </p>
            <h1 className="mt-5 text-4xl font-extrabold leading-tight text-gray-950 sm:text-5xl dark:text-white">
              A tutor that plans, chooses its tools, and checks its own work.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-gray-600 dark:text-gray-400">
              Not a single prompt bolted onto a textbook. A Supervisor decides what to teach next,
              a Learning Agent chooses when to search the textbook or verify a calculation, and a
              Reflection Agent audits every explanation before it reaches the student - grounded in
              real NCERT content, adapted to what the student has actually mastered.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <button
                type="button"
                onClick={() => scrollToId("get-started")}
                className="rounded-2xl bg-purple-600 px-6 py-4 text-base font-semibold text-white transition hover:bg-purple-700"
              >
                Try it free
              </button>
              <button
                type="button"
                onClick={() => scrollToId("architecture")}
                className="rounded-2xl border border-gray-200 px-6 py-4 text-base font-semibold text-gray-700 transition hover:border-purple-200 hover:text-purple-700 dark:border-gray-700 dark:text-gray-300 dark:hover:border-purple-700 dark:hover:text-purple-300"
              >
                See how it works
              </button>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <figure className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-textbook dark:border-gray-800 dark:bg-gray-900">
              <img
                src="/screenshots/selection-page.jpg"
                alt="Chapter selection screen: pick a grade, subject, and chapter"
                className="w-full"
              />
              <figcaption className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                Pick a grade, subject, and chapter to begin.
              </figcaption>
            </figure>
            <figure className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-textbook dark:border-gray-800 dark:bg-gray-900">
              <img
                src="/screenshots/teaching-page.jpg"
                alt="Teaching screen: structured explanation card alongside a live chat panel"
                className="w-full"
              />
              <figcaption className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                A structured lesson card, streamed live, with a chat panel alongside it.
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      <section id="architecture" className="border-y border-gray-100 bg-white px-6 py-16 dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700 dark:text-purple-300">
            How a turn actually works
          </p>
          <h2 className="mt-3 max-w-2xl text-3xl font-bold text-gray-950 dark:text-white">
            Four agents, one loop, per turn.
          </h2>

          <div className="mt-10 grid gap-4 lg:grid-cols-4">
            {pipelineStages.map((stage, index) => (
              <div key={stage.title} className="flex items-start gap-4 lg:flex-col lg:items-stretch">
                <div className="flex flex-col items-center lg:hidden">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white">
                    {index + 1}
                  </span>
                  {index < pipelineStages.length - 1 ? (
                    <span className="mt-1 h-full w-px flex-1 bg-gray-200 dark:bg-gray-700" />
                  ) : null}
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5 dark:border-gray-800 dark:bg-gray-800/60">
                  <span className="hidden h-9 w-9 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white lg:flex">
                    {index + 1}
                  </span>
                  <h3 className="mt-3 text-lg font-bold text-gray-950 dark:text-white">{stage.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">{stage.detail}</p>
                </div>
                {index < pipelineStages.length - 1 ? (
                  <span className="mt-3 hidden justify-center text-2xl text-gray-300 lg:flex dark:text-gray-600">
                    →
                  </span>
                ) : null}
              </div>
            ))}
          </div>
          <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
            A failing Reflection check routes back to the same Learning Agent with the critique
            attached - capped at one retry, so a turn always terminates.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700 dark:text-purple-300">
          Why it's built this way
        </p>
        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900"
            >
              <h3 className="text-lg font-bold text-gray-950 dark:text-white">{feature.title}</h3>
              <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">{feature.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="get-started" className="border-t border-gray-100 bg-white px-6 py-16 dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-8 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-md text-center lg:text-left">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700 dark:text-purple-300">
              Try it free
            </p>
            <h2 className="mt-3 text-3xl font-bold text-gray-950 dark:text-white">
              Sign in to start a chapter.
            </h2>
            <p className="mt-3 text-base leading-7 text-gray-600 dark:text-gray-400">
              No credit card, no setup. Pick a grade and chapter and the Supervisor takes it from
              there.
            </p>
          </div>
          <div className="w-full max-w-sm">
            <SignIn />
          </div>
        </div>
      </section>
    </div>
  );
}
