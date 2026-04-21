import { AnimatePresence, motion } from "framer-motion";
import { SelectionPage } from "./pages/SelectionPage";
import { TeachingPage } from "./pages/TeachingPage";
import { QuizPage } from "./pages/QuizPage";
import { ResultsPage } from "./pages/ResultsPage";
import { useSessionStore } from "./store/sessionStore";

export default function App() {
  const mode = useSessionStore((state) => state.mode);

  const page = (() => {
    switch (mode) {
      case "teaching":
        return <TeachingPage />;
      case "quiz":
        return <QuizPage />;
      case "results":
        return <ResultsPage />;
      default:
        return <SelectionPage />;
    }
  })();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={mode}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
      >
        {page}
      </motion.div>
    </AnimatePresence>
  );
}
