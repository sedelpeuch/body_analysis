import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { TodayPage } from "./routes/today/TodayPage";
import { BodyPage } from "./routes/body/BodyPage";
import { PhotosPage } from "./routes/body-photos/PhotosPage";
import { PhasesPage } from "./routes/phases/PhasesPage";
import { PhaseDetailPage } from "./routes/phases/PhaseDetailPage";
import { NutritionPage } from "./routes/nutrition/NutritionPage";
import { EnergyPage } from "./routes/energy/EnergyPage";
import { TrainingPage } from "./routes/training/TrainingPage";
import { WorkoutDetailPage } from "./routes/training/WorkoutDetailPage";
import { SettingsPage } from "./routes/settings/SettingsPage";

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <TodayPage /> },
      { path: "/corps", element: <BodyPage /> },
      { path: "/corps/photos", element: <PhotosPage /> },
      { path: "/phases", element: <PhasesPage /> },
      { path: "/phases/:id", element: <PhaseDetailPage /> },
      { path: "/nutrition", element: <NutritionPage /> },
      { path: "/energie", element: <EnergyPage /> },
      { path: "/entrainement", element: <TrainingPage /> },
      { path: "/entrainement/:id", element: <WorkoutDetailPage /> },
      { path: "/reglages", element: <SettingsPage /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
