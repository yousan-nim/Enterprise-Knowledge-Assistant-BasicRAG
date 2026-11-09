import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Folio — A little clarity",
  description:
    "A local knowledge workspace. Ask your documents, explore the evidence, and find a little clarity.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#conversation">
          Skip to conversation
        </a>
        {children}
      </body>
    </html>
  );
}
