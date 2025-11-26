import { Routes, Route } from "react-router-dom";

import "./App.css";
import { ApiKeyGate } from "./components/common/ApiKeyGate";
import { AppLayout } from "./components/layout/AppLayout";
import { BroadcastDetailPage } from "./pages/BroadcastDetail";
import { BroadcastsPage } from "./pages/Broadcasts";
import { CreateBroadcastPage } from "./pages/CreateBroadcast";
import { DashboardPage } from "./pages/Dashboard";
import { NotFoundPage } from "./pages/NotFound";

const App = () => {
  return (
    <ApiKeyGate>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/broadcasts" element={<BroadcastsPage />} />
          <Route path="/broadcasts/create" element={<CreateBroadcastPage />} />
          <Route path="/broadcasts/:id" element={<BroadcastDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </ApiKeyGate>
  );
};

export default App;
