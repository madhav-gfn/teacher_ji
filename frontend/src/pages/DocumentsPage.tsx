import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, type DocumentDetail } from "../api/client";
import { useSessionStore } from "../store/sessionStore";

export function DocumentsPage() {
  const studentId = useSessionStore((state) => state.studentId);
  const setSession = useSessionStore((state) => state.setSession);
  const setMode = useSessionStore((state) => state.setMode);
  const queryClient = useQueryClient();

  const [grade, setGrade] = useState(8);
  const [title, setTitle] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const documentsQuery = useQuery({
    queryKey: ["documents", studentId],
    queryFn: () => apiClient.listDocuments(),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadDocument(file, title || undefined),
    onSuccess: () => {
      setTitle("");
      void queryClient.invalidateQueries({ queryKey: ["documents", studentId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => apiClient.deleteDocument(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents", studentId] });
    },
  });

  const startFromDocument = useMutation({
    mutationFn: async (doc: DocumentDetail) => {
      const response = await apiClient.startSession({
        document_id: doc.document_id,
        grade,
        topic: doc.topics[0],
        custom_topics: doc.topics,
      });
      return { response, doc };
    },
    onSuccess: ({ response, doc }) => {
      setSession({
        sessionId: response.session_id,
        documentId: doc.document_id,
        grade,
        subject: "custom",
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

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  const handleStudy = async (documentId: string) => {
    const detail = await apiClient.getDocument(documentId);
    startFromDocument.mutate(detail);
  };

  const documents = documentsQuery.data ?? [];

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-10 dark:bg-gray-950">
      <div className="mx-auto max-w-4xl">
        <button
          type="button"
          onClick={() => setMode("selection")}
          className="mb-6 text-sm font-semibold text-purple-700 hover:text-purple-900 dark:text-purple-300 dark:hover:text-purple-200"
        >
          ← Back to NCERT curriculum
        </button>

        <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-textbook dark:border-gray-800 dark:bg-gray-900">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-orange-700 dark:text-orange-300">
            Your Material
          </p>
          <h1 className="mt-3 text-3xl font-extrabold text-gray-950 dark:text-white">
            Upload notes, study them like a chapter.
          </h1>
          <p className="mt-3 max-w-xl text-base leading-7 text-gray-600 dark:text-gray-400">
            Upload a PDF, text, or markdown file. We'll organize it into topics, then teach and
            quiz you from your own material — grounded only in what you uploaded.
          </p>

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragActive(false);
              handleFiles(event.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`mt-8 cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition ${
              dragActive
                ? "border-orange-400 bg-orange-50 dark:border-orange-600 dark:bg-orange-950/30"
                : "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/40"
            }`}
          >
            <p className="text-base font-semibold text-gray-800 dark:text-gray-200">
              {uploadMutation.isPending
                ? "Uploading and organizing your material…"
                : "Drag a file here, or click to browse"}
            </p>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">PDF, TXT, or MD — up to 20 MB</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md"
              className="hidden"
              onChange={(event) => handleFiles(event.target.files)}
            />
          </div>

          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Optional title for this upload"
            className="mt-4 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none transition focus:border-orange-300 focus:ring-2 focus:ring-orange-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-orange-600"
          />

          {uploadMutation.error ? (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">{uploadMutation.error.message}</p>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">Explain at level:</p>
            {[6, 7, 8].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setGrade(item)}
                className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition ${
                  grade === item
                    ? "border-orange-300 bg-orange-50 text-orange-700 dark:border-orange-700 dark:bg-orange-950/40 dark:text-orange-300"
                    : "border-gray-200 text-gray-600 hover:border-orange-200 dark:border-gray-700 dark:text-gray-400 dark:hover:border-orange-700"
                }`}
              >
                Class {item}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-8 rounded-3xl border border-gray-100 bg-white p-8 shadow-textbook dark:border-gray-800 dark:bg-gray-900">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-gray-500 dark:text-gray-400">
            Your Library
          </p>
          {documentsQuery.isLoading ? (
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Loading…</p>
          ) : documents.length === 0 ? (
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
              No uploads yet. Add one above to get started.
            </p>
          ) : (
            <div className="mt-4 space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.document_id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-gray-50 p-5 dark:border-gray-800 dark:bg-gray-800/40"
                >
                  <div>
                    <p className="text-base font-semibold text-gray-950 dark:text-white">{doc.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">
                      {doc.topic_count} topics · {doc.chunk_count} chunks
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={startFromDocument.isPending}
                      onClick={() => void handleStudy(doc.document_id)}
                      className="rounded-xl bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:bg-orange-300"
                    >
                      {startFromDocument.isPending ? "Starting…" : "Study"}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteMutation.mutate(doc.document_id)}
                      className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-600 transition hover:border-red-200 hover:text-red-600 dark:border-gray-700 dark:text-gray-400 dark:hover:border-red-800 dark:hover:text-red-400"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {startFromDocument.error ? (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">{startFromDocument.error.message}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
