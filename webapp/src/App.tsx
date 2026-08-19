import { HashRouter, Route, Routes } from "react-router-dom";
import FloatingChat from "./components/FloatingChat";
import { CapabilitiesProvider } from "./lib/capabilities";
import { AppsPage } from "./pages/AppsPage";
import { HelpPage } from "./pages/HelpPage";
import { HomePage } from "./pages/HomePage";
import { LogsPage } from "./pages/LogsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ToolsPage } from "./pages/ToolsPage";
import { Shell } from "./shell/Shell";

export default function App() {
  return (
    <CapabilitiesProvider>
      <HashRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<HomePage />} />
            <Route path="tools" element={<ToolsPage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="apps" element={<AppsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="help" element={<HelpPage />} />
          </Route>
        </Routes>
        <FloatingChat />
      </HashRouter>
    </CapabilitiesProvider>
  );
}
