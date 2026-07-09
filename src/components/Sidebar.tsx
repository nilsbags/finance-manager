"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", icon: "📊", label: "Dashboard" },
  { href: "/spendings", icon: "🛒", label: "Spendings" },
  { href: "/earnings", icon: "💰", label: "Earnings" },
  { href: "/subscriptions", icon: "🔁", label: "Monthly Subscriptions" },
  { href: "/transactions", icon: "📂", label: "Transactions" },
  { href: "/import", icon: "📥", label: "Import" },
  { href: "/rules", icon: "⚙️", label: "Rules" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-slate-200 bg-white px-3 py-6 sm:block">
      <div className="mb-6 px-3 text-lg font-bold">💸 Finance Manager</div>
      <nav className="space-y-1">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
