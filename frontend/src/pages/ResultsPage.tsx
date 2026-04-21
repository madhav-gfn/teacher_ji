import { useEffect, useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { curriculum, getNextChapter, getTopics, subjectMeta } from "../data/curriculum";
import { useSessionStore } from "../store/sessionStore";

function scoreClasses(scorePercent: number) {
  if (scorePercent >= 80) {
    return "text-green-600";
  }
  if (scorePercent >= 60) {
    return "text-amber-600";
  }
  return "text-red-600";
}

export function ResultsPage() {
  const {
    studentId,
    sessionId,
    grade,
    subject,
    chapter,
    topicsCompleted,
    weakTopics,
    sessionScore,
    setSession,
  } = useSessionStore();

  const scorePercent = Math.round(sessionScore * 100);
  const masteredTopics = useMemo(
    () => topicsCompleted.filter((topic) => !weakTopics.includes(topic)),
    [topicsCompleted, weakTopics],
  );

  const allTopics = grade && subject && chapter ? getTopics(grade, subject, chapter) : [];
  const nextChapter = grade && subject && chapter ? getNextChapter(grade, subject, chapter) : null;

  const persistResults = useMutation({
    mutationFn: async () => {
      if (!studentId || !sessionId || !subject || !chapter) {
        return null;
      }

      return apiClient.updateStudentProfile(studentId, {
        session_id: sessionId,
        subject,
        chapter,
        session_score: sessionScore,
        mastered_topics: masteredTopics,
        weak_topics: weakTopics,
        quiz_date: new Date().toISOString().slice(0, 10),
      });
    },
  });

  useEffect(() => {
    if (!persistResults.isIdle) {
      return;
    }

    void persistResults.mutateAsync();
  }, [persistResults]);

  if (!grade || !subject || !chapter || !sessionId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50 p-6">
        <div className="rounded-2xl border border-gray-100 bg-white p-8 shadow-sm">
          <p className="text-lg font-semibold text-gray-900">No results are available yet.</p>
        </div>
      </div>
    );
  }

  const meta = subjectMeta[subject];

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section className="rounded-3xl border border-gray-100 bg-white p-8 shadow-textbook">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-gray-500">
                Session Results
              </p>
              <h1 className="mt-4 text-3xl font-bold text-gray-950">{chapter}</h1>
              <p className={`mt-3 rounded-full px-4 py-2 text-sm font-semibold ${meta.softAccent}`}>
                {meta.label}
              </p>
            </div>

            <div className="rounded-3xl border border-gray-100 bg-gray-50 px-8 py-6 text-center">
              <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Session score</p>
              <p className={`mt-3 text-6xl font-extrabold ${scoreClasses(scorePercent)}`}>
                {scorePercent}%
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-gray-950">Topics mastered</h2>
            <div className="mt-5 flex flex-wrap gap-3">
              {masteredTopics.length ? (
                masteredTopics.map((topic) => (
                  <span
                    key={topic}
                    className="rounded-full border border-green-200 bg-green-50 px-4 py-2 text-sm font-semibold text-green-700"
                  >
                    {topic}
                  </span>
                ))
              ) : (
                <p className="text-sm text-gray-500">Mastered topics will appear after stronger quiz performance.</p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-gray-950">Topics to revise</h2>
            <div className="mt-5 flex flex-wrap gap-3">
              {weakTopics.length ? (
                weakTopics.map((topic) => (
                  <span
                    key={topic}
                    className="rounded-full border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700"
                  >
                    {topic}
                  </span>
                ))
              ) : (
                <p className="text-sm text-gray-500">No weak topics identified in this session.</p>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-gray-950">Topic mastery</h2>
          <div className="mt-5 space-y-4">
            {allTopics.map((topic) => {
              const percent = weakTopics.includes(topic) ? 42 : masteredTopics.includes(topic) ? 90 : 65;
              const barClass = weakTopics.includes(topic) ? "bg-red-500" : "bg-green-500";

              return (
                <div key={topic}>
                  <div className="mb-2 flex items-center justify-between gap-4">
                    <p className="text-sm font-medium text-gray-800">{topic}</p>
                    <span className="text-sm font-semibold text-gray-500">{percent}%</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                    <div className={`h-full rounded-full ${barClass}`} style={{ width: `${percent}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            disabled={weakTopics.length === 0}
            onClick={async () => {
              const firstWeakTopic = weakTopics[0];
              if (!firstWeakTopic) {
                return;
              }

              const response = await apiClient.startSession({
                student_id: studentId,
                grade,
                subject,
                chapter,
                topic: firstWeakTopic,
                custom_topics: weakTopics,
              });

              setSession({
                sessionId: response.session_id,
                chapter: response.chapter,
                currentTopic: response.topic,
                topicsCompleted: [],
                topicsRemaining: response.next_topics,
                teachingOutput: response.teaching_output,
                quizQuestions: [],
                currentQuestionIndex: 0,
                feedbackOutput: null,
                weakTopics,
                sessionScore: 0,
                mode: "teaching",
              });
            }}
            className="rounded-2xl bg-purple-600 px-6 py-4 text-sm font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
          >
            Revise weak topics
          </button>

          <button
            type="button"
            onClick={async () => {
              if (!nextChapter) {
                setSession({ mode: "selection" });
                return;
              }

              const nextTopic = curriculum[subject][grade][nextChapter]?.[0] ?? "Introduction";
              const response = await apiClient.startSession({
                student_id: studentId,
                grade,
                subject,
                chapter: nextChapter,
                topic: nextTopic,
              });

              setSession({
                sessionId: response.session_id,
                chapter: response.chapter,
                currentTopic: response.topic,
                topicsCompleted: [],
                topicsRemaining: response.next_topics,
                teachingOutput: response.teaching_output,
                quizQuestions: [],
                currentQuestionIndex: 0,
                feedbackOutput: null,
                weakTopics: [],
                sessionScore: 0,
                mode: "teaching",
              });
            }}
            className="rounded-2xl border border-gray-200 bg-white px-6 py-4 text-sm font-semibold text-gray-700 transition hover:border-purple-200 hover:text-purple-700"
          >
            {nextChapter ? "Next chapter" : "Back to chapter selection"}
          </button>

          {persistResults.error ? (
            <p className="text-sm text-red-600">{persistResults.error.message}</p>
          ) : (
            <p className="text-sm text-gray-500">
              {persistResults.isPending
                ? "Saving results to student profile..."
                : "Results synced to student profile."}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
