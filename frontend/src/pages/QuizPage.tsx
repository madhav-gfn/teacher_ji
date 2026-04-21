import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FeedbackOutput, QuizQuestion } from "../api/client";
import { apiClient } from "../api/client";
import { FeedbackPanel } from "../components/FeedbackPanel";
import { QuizCard } from "../components/QuizCard";
import { useSessionStore } from "../store/sessionStore";

export function QuizPage() {
  const {
    sessionId,
    quizQuestions,
    currentQuestionIndex,
    setQuizData,
    setCurrentQuestionIndex,
    setFeedbackOutput,
    updateScore,
    addWeakTopic,
    removeWeakTopic,
    setMode,
  } = useSessionStore();

  const [activeFeedback, setActiveFeedback] = useState<FeedbackOutput | null>(null);

  const quizQuery = useQuery({
    queryKey: ["quiz-start", sessionId],
    queryFn: async () => {
      if (!sessionId) {
        throw new Error("Missing session id.");
      }
      return apiClient.startQuiz({ session_id: sessionId });
    },
    enabled: Boolean(sessionId) && quizQuestions.length === 0,
  });

  useEffect(() => {
    if (quizQuery.data) {
      setQuizData(quizQuery.data.questions);
    }
  }, [quizQuery.data, setQuizData]);

  const questions = quizQuestions.length ? quizQuestions : quizQuery.data?.questions ?? [];
  const currentQuestion = questions[currentQuestionIndex];

  const submitAnswer = useMutation({
    mutationFn: async (answer: string) => {
      if (!sessionId || !currentQuestion) {
        throw new Error("Question is not ready.");
      }

      return apiClient.submitAnswer({
        session_id: sessionId,
        question_id: currentQuestion.question_id,
        student_answer: answer,
      });
    },
    onSuccess: (response) => {
      if (!currentQuestion) {
        return;
      }

      const feedback = response.feedback_output;
      setActiveFeedback(feedback);
      setFeedbackOutput(feedback);
      updateScore(response.session_score_so_far);

      if (feedback.concept_strength === "mastered") {
        removeWeakTopic(currentQuestion.concept_tested);
      } else {
        addWeakTopic(currentQuestion.concept_tested);
      }

      const updatedQuestions = questions.map((question) =>
        question.question_id === currentQuestion.question_id
          ? { ...question, evaluation: feedback }
          : question,
      );
      setQuizData(updatedQuestions);
      setCurrentQuestionIndex(currentQuestionIndex);
    },
  });

  useEffect(() => {
    setActiveFeedback(currentQuestion?.evaluation ?? null);
  }, [currentQuestion]);

  const progress = useMemo(() => {
    if (!questions.length) {
      return 33;
    }

    return Math.round(((currentQuestionIndex + 1) / questions.length) * 100);
  }, [currentQuestionIndex, questions.length]);

  if (!sessionId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50 p-6">
        <div className="rounded-2xl border border-gray-100 bg-white p-8 shadow-sm">
          <p className="text-lg font-semibold text-gray-900">No quiz session found.</p>
        </div>
      </div>
    );
  }

  if (quizQuery.isLoading || !currentQuestion) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50 p-6">
        <div className="w-full max-w-xl rounded-3xl border border-gray-100 bg-white p-10 shadow-textbook">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-purple-700">
            Quiz Mode
          </p>
          <h1 className="mt-4 text-3xl font-bold text-gray-950">
            Preparing your quiz based on what you just learned...
          </h1>
          <div className="mt-8 h-3 overflow-hidden rounded-full bg-gray-100">
            <motion.div
              className="h-full rounded-full bg-purple-600"
              initial={{ width: "10%" }}
              animate={{ width: ["25%", "55%", "80%"] }}
              transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY }}
            />
          </div>
          {quizQuery.error ? (
            <p className="mt-4 text-sm text-red-600">{quizQuery.error.message}</p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 rounded-2xl border border-gray-100 bg-white px-6 py-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gray-500">
                Chapter Quiz
              </p>
              <h1 className="mt-2 text-2xl font-bold text-gray-950">
                Question {currentQuestionIndex + 1} of {questions.length}
              </h1>
            </div>
            <span className="rounded-full bg-purple-50 px-4 py-2 text-sm font-semibold text-purple-700">
              {progress}% through quiz
            </span>
          </div>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-purple-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <QuizCard
          question={currentQuestion as QuizQuestion}
          feedback={activeFeedback}
          isSubmitting={submitAnswer.isPending}
          onSubmit={(answer) => submitAnswer.mutate(answer)}
        />

        {activeFeedback ? (
          <div className="mt-5 space-y-5">
            <FeedbackPanel feedback={activeFeedback} />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => {
                  if (currentQuestionIndex >= questions.length - 1) {
                    setMode("results");
                    return;
                  }

                  setCurrentQuestionIndex(currentQuestionIndex + 1);
                  setActiveFeedback(null);
                  setFeedbackOutput(null);
                }}
                className="rounded-xl bg-purple-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-purple-700"
              >
                {currentQuestionIndex >= questions.length - 1 ? "See Results" : "Next Question"}
              </button>
            </div>
          </div>
        ) : null}

        {submitAnswer.error ? (
          <p className="mt-4 text-sm text-red-600">{submitAnswer.error.message}</p>
        ) : null}
      </div>
    </div>
  );
}
