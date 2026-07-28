import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { getChapters, getTopics, subjectMeta } from "../data/curriculum";
import { useSessionStore } from "../store/sessionStore";
import { useStagedLoadingLabel } from "../hooks/useStagedLoadingLabel";

// Named after the real turn this request runs through server-side
// (agents/graph.py: Supervisor -> Learning Agent's tool loop -> Reflection
// Agent), not decorative copy - see useStagedLoadingLabel.
const SESSION_START_STAGES = [
  "Checking what you already know…",
  "Deciding what to teach first…",
  "Looking up the textbook…",
  "Verifying the explanation…",
] as const;

function SigmaIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-8 w-8 fill-none stroke-current stroke-[1.7]">
      <path d="M18 4H7l6 8-6 8h11" />
    </svg>
  );
}

function FlaskIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-8 w-8 fill-none stroke-current stroke-[1.7]">
      <path d="M10 3v5l-5 9a2 2 0 0 0 1.76 3h10.48A2 2 0 0 0 19 17l-5-9V3" />
      <path d="M8 14h8" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-8 w-8 fill-none stroke-current stroke-[1.7]">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
    </svg>
  );
}

type NcertSubject = "math" | "science" | "sst";

const subjectCards: Array<{ subject: NcertSubject; icon: JSX.Element }> = [
  { subject: "math", icon: <SigmaIcon /> },
  { subject: "science", icon: <FlaskIcon /> },
  { subject: "sst", icon: <GlobeIcon /> },
];

export function SelectionPage() {
  const studentId = useSessionStore((state) => state.studentId);
  const setSession = useSessionStore((state) => state.setSession);
  const setMode = useSessionStore((state) => state.setMode);

  const [grade, setGrade] = useState<number | null>(null);
  const [subject, setSubject] = useState<NcertSubject | null>(null);
  const [chapter, setChapter] = useState("");

  const chapters = useMemo(() => getChapters(grade, subject), [grade, subject]);

  const startSession = useMutation({
    mutationFn: () => {
      if (!grade || !subject || !chapter) {
        throw new Error("Please complete all three steps before starting.");
      }

      const chapterTopics = getTopics(grade, subject, chapter);
      const topic = chapterTopics[0] ?? "Introduction";

      return apiClient.startSession({
        grade,
        subject,
        chapter,
        topic,
      });
    },
    onSuccess: (response) => {
      setSession({
        sessionId: response.session_id,
        grade: response.subject ? grade : null,
        subject: response.subject,
        chapter: response.chapter,
        currentTopic: response.topic,
        topicsCompleted: [],
        topicsRemaining: response.next_topics,
        teachingOutput: response.teaching_output,
        quizQuestions: [],
        currentQuestionIndex: 0,
        weakTopics: [],
        sessionScore: 0,
        feedbackOutput: null,
        mode: "teaching",
      });
    },
  });

  const startSessionLabel = useStagedLoadingLabel(SESSION_START_STAGES, startSession.isPending);

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-10 dark:bg-gray-950">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-center">
        <div className="grid w-full gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-textbook dark:border-gray-800 dark:bg-gray-900">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700 dark:text-purple-300">
              NCERT Multi-Agent Learning Platform
            </p>
            <h1 className="mt-5 max-w-xl text-4xl font-extrabold leading-tight text-gray-950 sm:text-5xl dark:text-white">
              Structured teaching boards for focused chapter learning.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-gray-600 dark:text-gray-400">
              Choose the class, subject, and chapter. The board will guide topic-by-topic
              teaching, then move into feedback-rich quizzing.
            </p>

            <button
              type="button"
              onClick={() => setMode("documents")}
              className="mt-6 flex w-full items-center justify-between rounded-2xl border border-orange-100 bg-orange-50 px-6 py-4 text-left transition hover:border-orange-200 dark:border-orange-900 dark:bg-orange-950/40 dark:hover:border-orange-700"
            >
              <div>
                <p className="text-sm font-semibold text-orange-800 dark:text-orange-300">
                  Have your own notes or a PDF instead?
                </p>
                <p className="mt-1 text-sm text-orange-700/80 dark:text-orange-400/80">
                  Upload your own material and study it the same way.
                </p>
              </div>
              <span className="text-lg font-semibold text-orange-700 dark:text-orange-300">→</span>
            </button>

            <div className="mt-10 space-y-8">
              <section>
                <div className="mb-4 flex items-center gap-3">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white">
                    1
                  </span>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Select grade</h2>
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  {[6, 7, 8].map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => {
                        setGrade(item);
                        setSubject(null);
                        setChapter("");
                      }}
                      className={`rounded-2xl border p-6 text-left transition ${
                        grade === item
                          ? "border-purple-200 bg-purple-50 shadow-sm dark:border-purple-800 dark:bg-purple-950/40"
                          : "border-gray-200 bg-white hover:border-purple-200 hover:bg-purple-50/60 dark:border-gray-700 dark:bg-gray-900 dark:hover:border-purple-800 dark:hover:bg-purple-950/20"
                      }`}
                    >
                      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">
                        Grade
                      </p>
                      <p className="mt-3 text-3xl font-bold text-gray-950 dark:text-white">{item}</p>
                    </button>
                  ))}
                </div>
              </section>

              {grade ? (
                <section>
                  <div className="mb-4 flex items-center gap-3">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white">
                      2
                    </span>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Select subject</h2>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    {subjectCards.map((item) => {
                      const meta = subjectMeta[item.subject];
                      const isActive = subject === item.subject;
                      return (
                        <button
                          key={item.subject}
                          type="button"
                          onClick={() => {
                            setSubject(item.subject);
                            setChapter("");
                          }}
                          className={`rounded-2xl border p-5 text-left transition ${
                            isActive
                              ? `${meta.accent} shadow-sm`
                              : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:border-gray-600"
                          }`}
                        >
                          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/80 dark:bg-black/20">
                            {item.icon}
                          </div>
                          <p className="mt-4 text-lg font-semibold">{meta.label}</p>
                        </button>
                      );
                    })}
                  </div>
                </section>
              ) : null}

              {subject ? (
                <section>
                  <div className="mb-4 flex items-center gap-3">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-purple-600 text-sm font-bold text-white">
                      3
                    </span>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Select chapter</h2>
                  </div>
                  <select
                    value={chapter}
                    onChange={(event) => setChapter(event.target.value)}
                    className="w-full rounded-2xl border border-gray-200 bg-white px-5 py-4 text-base text-gray-900 outline-none transition focus:border-purple-300 focus:ring-2 focus:ring-purple-100 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-purple-700"
                  >
                    <option value="">Choose a chapter</option>
                    {chapters.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </section>
              ) : null}
            </div>
          </div>

          <div className="flex flex-col justify-between rounded-3xl border border-gray-100 bg-white p-8 shadow-textbook dark:border-gray-800 dark:bg-gray-900">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-gray-500 dark:text-gray-400">
                Session Setup
              </p>
              <div className="mt-6 space-y-4">
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5 dark:border-gray-800 dark:bg-gray-800/60">
                  <p className="text-xs uppercase tracking-[0.22em] text-gray-500 dark:text-gray-400">Grade</p>
                  <p className="mt-2 text-lg font-semibold text-gray-950 dark:text-white">
                    {grade ? `Class ${grade}` : "Not selected"}
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5 dark:border-gray-800 dark:bg-gray-800/60">
                  <p className="text-xs uppercase tracking-[0.22em] text-gray-500 dark:text-gray-400">Subject</p>
                  <p className="mt-2 text-lg font-semibold text-gray-950 dark:text-white">
                    {subject ? subjectMeta[subject].label : "Not selected"}
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5 dark:border-gray-800 dark:bg-gray-800/60">
                  <p className="text-xs uppercase tracking-[0.22em] text-gray-500 dark:text-gray-400">Chapter</p>
                  <p className="mt-2 text-lg font-semibold text-gray-950 dark:text-white">
                    {chapter || "Not selected"}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-8">
              <button
                type="button"
                onClick={() => startSession.mutate()}
                disabled={!grade || !subject || !chapter || startSession.isPending}
                className="w-full rounded-2xl bg-purple-600 px-6 py-4 text-base font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
              >
                {startSession.isPending ? startSessionLabel : "Start Learning"}
              </button>
              {startSession.error ? (
                <p className="mt-3 text-sm text-red-600 dark:text-red-400">{startSession.error.message}</p>
              ) : null}
              <p className="mt-4 text-sm leading-6 text-gray-500 dark:text-gray-400">
                Student profile key: <span className="font-semibold text-gray-700 dark:text-gray-300">{studentId}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
