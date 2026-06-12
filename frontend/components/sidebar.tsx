"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart2,
  Compass,
  Home,
  Settings,
  Upload,
  User,
  Octagon,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth";

const NAV = [
  { href: "/",                    icon: Home,     label: "홈" },
  { href: "/agents/profiler",     icon: Octagon,  label: "Profiler" },
  { href: "/agents/navigator",    icon: Compass,  label: "Navigator" },
  { href: "/agents/aggregator",   icon: BarChart2,label: "Aggregator" },
  { href: "/agents/indexer",      icon: Upload,   label: "Indexer" },
  { href: "/settings",            icon: Settings, label: "설정" },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="flex h-screen w-[60px] flex-col items-center rounded-r-2xl border-r border-gray-100 bg-white py-5 shadow-sm">
      {/* 로고 */}
      <Link href="/" className="mb-8 flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 hover:bg-violet-700 transition-colors">
        <span className="text-sm font-bold text-white">S</span>
      </Link>

      {/* 네비게이션 */}
      <nav className="flex flex-1 flex-col items-center gap-1">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors ${
                active
                  ? "bg-violet-100 text-violet-600"
                  : "text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              }`}
            >
              <Icon size={18} strokeWidth={active ? 2.2 : 1.8} />
            </Link>
          );
        })}
      </nav>

      {/* 유저 아바타 */}
      {user ? (
        <button
          onClick={logout}
          title={`${user.name} (로그아웃)`}
          className="overflow-hidden rounded-full ring-2 ring-transparent hover:ring-violet-300 transition-all"
        >
          {user.picture ? (
            <Image src={user.picture} alt={user.name} width={36} height={36} className="rounded-full" />
          ) : (
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">
              {user.name[0]}
            </div>
          )}
        </button>
      ) : (
        <a
          href="http://localhost:8000/api/v1/auth/login"
          title="로그인"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-400 hover:bg-violet-100 hover:text-violet-600 transition-colors"
        >
          <User size={16} />
        </a>
      )}
    </aside>
  );
}
