import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { ThemeProvider } from "@/components/ThemeProvider";

export const metadata: Metadata = {
  title: "Finance Manager",
  description: "Local-first personal spending tracker",
};

// Runs before paint: dark is the default, only an explicit "light" choice
// stored in localStorage removes the class (avoids a theme flash on load).
const themeInitScript =
  "try{if(localStorage.theme==='light'){document.documentElement.classList.remove('dark')}}catch(e){}";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <ThemeProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="min-w-0 flex-1 px-6 py-8 lg:px-10">
              <div className="mx-auto max-w-7xl">{children}</div>
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
