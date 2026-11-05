import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./query";
import Login from "./pages/Login";
import Recovery from "./pages/Recovery";
import Workspace from "./pages/Workspace";
import "./style.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/recuperar" element={<Recovery />} />
          <Route path="/restablecer" element={<Recovery confirm />} />
          <Route path="*" element={<Workspace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
