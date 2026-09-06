import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { BottomNav } from "./BottomNav";

export function AppShell() {
  return (
    <div className="flex min-h-svh">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-4 pb-24 md:p-8 md:pb-8">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  );
}
