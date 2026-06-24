import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";

import { router } from "@/routes/router";

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster position="bottom-right" richColors duration={3000} />
    </>
  );
}
