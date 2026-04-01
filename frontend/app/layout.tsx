import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { Activity, Upload, MessageSquare, LayoutDashboard, Heart } from "lucide-react";
import { LogoutButton } from "@/components/auth/LogoutButton";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "UHR — Unified Health Record",
  description: "Centralize e analise seu histórico médico com IA",
};

const navItems = [
  { href: "/dashboard", label: "Painel",      icon: LayoutDashboard },
  { href: "/upload",    label: "Documentos",  icon: Upload },
  { href: "/saude",     label: "Saúde",       icon: Heart },
  { href: "/chat",      label: "Agente IA",   icon: MessageSquare },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.className} min-h-screen bg-gray-50`}>
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
            <Link href="/dashboard" className="flex items-center gap-2 font-semibold text-gray-900">
              <Activity className="h-5 w-5 text-blue-600" />
              UHR
            </Link>
            <nav className="flex items-center gap-1">
              {navItems.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              ))}
              <LogoutButton />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
