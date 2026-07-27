import { ClerkProvider, Show, SignIn, useAuth } from "@clerk/react";
import React, { useEffect, type ReactNode } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { ErrorBoundary } from "./ErrorBoundary";
import { setAuthTokenGetter } from "./api/authToken";
import { useSessionStore } from "./store/sessionStore";
import "./index.css";

const queryClient = new QueryClient();

const clerkPublishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
if (!clerkPublishableKey) {
  throw new Error("Missing VITE_CLERK_PUBLISHABLE_KEY environment variable");
}

function AuthBridge({ children }: { children: ReactNode }) {
  const { getToken, userId } = useAuth();
  const setSession = useSessionStore((state) => state.setSession);

  useEffect(() => {
    setAuthTokenGetter(getToken);
    return () => setAuthTokenGetter(null);
  }, [getToken]);

  useEffect(() => {
    if (userId) {
      setSession({ studentId: userId });
    }
  }, [userId, setSession]);

  return <>{children}</>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ClerkProvider publishableKey={clerkPublishableKey} afterSignOutUrl="/">
        <QueryClientProvider client={queryClient}>
          <Show when="signed-in">
            <AuthBridge>
              <App />
            </AuthBridge>
          </Show>
          <Show when="signed-out">
            <div className="flex min-h-screen items-center justify-center">
              <SignIn />
            </div>
          </Show>
        </QueryClientProvider>
      </ClerkProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);