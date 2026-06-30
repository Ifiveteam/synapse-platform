import { create } from "zustand";

interface ScrapDetailPanelStore {
  selectedScrapId: string | null;
  open: boolean;
  openScrapPanel: (scrapId: string) => void;
  setOpen: (open: boolean) => void;
}

export const useScrapDetailPanelStore = create<ScrapDetailPanelStore>()((set) => ({
  selectedScrapId: null,
  open: false,
  openScrapPanel: (scrapId) => set({ selectedScrapId: scrapId, open: true }),
  setOpen: (open) =>
    set((state) => ({
      open,
      selectedScrapId: open ? state.selectedScrapId : null,
    })),
}));
