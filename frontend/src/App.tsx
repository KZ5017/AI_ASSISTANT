import { useState } from "react";

import { ChatShell } from "./components/ChatShell";

export function App() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  return (
    <main className="app-root" data-theme={theme}>
      <ChatShell theme={theme} onThemeChange={setTheme} />
    </main>
  );
}
