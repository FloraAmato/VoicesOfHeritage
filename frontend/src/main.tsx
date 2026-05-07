import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import App from "./App";
import { CollectionView } from "./views/CollectionView";
import { EnvironmentView } from "./views/EnvironmentView";
import { ManuscriptView } from "./views/ManuscriptView";
import { PredictiveView } from "./views/PredictiveView";
import { AlertsView } from "./views/AlertsView";
import { DemoView } from "./views/DemoView";
import { GuidelinesView } from "./views/GuidelinesView";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<CollectionView />} />
          <Route path="ambiente" element={<EnvironmentView />} />
          <Route path="manufatto" element={<ManuscriptView />} />
          <Route path="predittiva" element={<PredictiveView />} />
          <Route path="alert" element={<AlertsView />} />
          <Route path="demo" element={<DemoView />} />
          <Route path="linee-guida" element={<GuidelinesView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
