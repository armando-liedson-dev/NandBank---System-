import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";
import { getRouter } from "./router";
import "./styles.css";

const target = document.getElementById("root");
if (!target) throw new Error("O ponto de montagem do NandBank não existe.");
createRoot(target).render(<StrictMode><RouterProvider router={getRouter()} /></StrictMode>);
