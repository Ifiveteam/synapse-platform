import { create } from "zustand";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

function getInitialTheme(): Theme {
  const saved = localStorage.getItem("theme") as Theme | null;
  if (saved) return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

interface ThemeStore {
  theme: Theme;
  toggle: () => void;
}

export const useThemeStore = create<ThemeStore>()((set, get) => {
  const initial = getInitialTheme();
  applyTheme(initial);

  return {
    theme: initial,
    toggle: () => {
      const next: Theme = get().theme === "light" ? "dark" : "light";
      applyTheme(next);
      localStorage.setItem("theme", next);
      set({ theme: next });
    },
  };
});
