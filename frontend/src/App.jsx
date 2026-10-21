import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import SuggestionChips from "./components/SuggestionChips";
import CategoryMenu from "./components/CategoryMenu";
import { useChat } from "./hooks/useChat";
import NavBar from "./components/NavBar";
import { checkHealth } from "./services/api";
import "./App.css";

export default function App() {
  const {
    messages,
    loading,
    selectedCategory,
    setSelectedCategory,
    sendMessage,
    clearChat,
    goHome,
    refreshLast,
  } = useChat();
  const [online, setOnline] = useState(null);

  useEffect(() => {
    checkHealth().then(setOnline);
  }, []);

  const hasStarted = messages.length > 0;

  const handleRefresh = () => {
    checkHealth().then(setOnline);
    refreshLast();
  };

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">
        Skip to chat
      </a>
      <header className="app__header">
        <div className="app__brand">
          <span className="app__title">CollegePath AI</span>
          <span className={`app__status${online ? "" : " app__status--offline"}`}>
            <span className="app__status-dot" aria-hidden="true" />
            {online === null ? "Checking…" : online ? "Online" : "Offline"}
          </span>
        </div>
        <NavBar
          messages={messages}
          loading={loading}
          onHome={goHome}
          onRefresh={handleRefresh}
          onClear={clearChat}
        />
      </header>

      <main className="app__main" id="main-content">
        {!hasStarted && (
          <div className="hero">
            <h1 className="hero__title">Navigate college admissions with clarity.</h1>
            <p className="hero__subtitle">
              Ask about applications, testing, financial aid, scholarships, gap years, and more —
              every answer is sourced.
            </p>
            <CategoryMenu selected={selectedCategory} onSelect={setSelectedCategory} />
            <SuggestionChips selectedCategory={selectedCategory} onSelect={sendMessage} />
          </div>
        )}

        {hasStarted && (
          <ChatWindow messages={messages} loading={loading} onSelectRelated={sendMessage} />
        )}
      </main>

      <footer className="app__footer">
        <ChatInput onSend={sendMessage} loading={loading} />
      </footer>
    </div>
  );
}
