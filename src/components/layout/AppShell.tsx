"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppState } from "@/lib/i18n";
import {
  apiClient,
  DEMO_ACCOUNTS,
  ensureAuthenticated,
  getSavedSession,
  loginWithCredentials,
} from "@/lib/api-client";
import type { TechnologyItem, UserRole } from "@/lib/api-types";
import { Badge } from "@/components/ui/primitives";
import {
  LayoutDashboard,
  FileUp,
  Cpu,
  Microscope,
  TrendingUp,
  Calculator,
  ShieldCheck,
  FileText,
  BookOpen,
  FlaskConical,
  Globe,
  UserCheck,
  Menu,
  X,
} from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { lang, setLang, t, selectedTechId, setSelectedTechId } = useAppState();
  const [technologies, setTechnologies] = useState<TechnologyItem[]>([]);
  const [activeRole, setActiveRole] = useState<UserRole>("analyst");
  const [userName, setUserName] = useState<string>("Rina Kusuma, M.T.");
  const [healthStatus, setHealthStatus] = useState<string>("checking...");
  const [menuOpen, setMenuOpen] = useState<boolean>(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const refreshContext = async () => {
    try {
      const session = await ensureAuthenticated("analyst");
      setActiveRole(session.user.role);
      setUserName(session.user.full_name);

      const [techs, health] = await Promise.all([
        apiClient.listTechnologies(),
        apiClient.getHealth(),
      ]);
      setTechnologies(techs);
      setHealthStatus(health.status || "ok");
      if (techs.length > 0 && (!selectedTechId || !techs.some((x) => x.id === selectedTechId))) {
        setSelectedTechId(techs[0].id);
      }
    } catch (e: any) {
      setHealthStatus("degraded");
    }
  };

  useEffect(() => {
    const existing = getSavedSession();
    if (existing) {
      setActiveRole(existing.user.role);
      setUserName(existing.user.full_name);
    }
    refreshContext();
  }, []);

  const handleRoleSwitch = async (roleKey: keyof typeof DEMO_ACCOUNTS) => {
    try {
      const creds = DEMO_ACCOUNTS[roleKey];
      const session = await loginWithCredentials(creds.username, creds.password);
      setActiveRole(session.user.role);
      setUserName(session.user.full_name);
      window.dispatchEvent(new CustomEvent("techval-role-changed"));
    } catch (err) {
      console.error("Failed to switch role:", err);
    }
  };

  const navGroups = [
    {
      label: t.nav.groupMain,
      items: [
        { href: "/", label: t.nav.portfolio, icon: LayoutDashboard },
        { href: "/submission", label: t.nav.submission, icon: FileUp },
        { href: "/pipeline", label: t.nav.pipeline, icon: Cpu },
      ],
    },
    {
      label: t.nav.groupResults,
      items: [
        { href: "/assessment", label: t.nav.assessment, icon: Microscope },
        { href: "/commercialization", label: t.nav.commercialization, icon: TrendingUp },
        { href: "/valuation", label: t.nav.valuation, icon: Calculator },
        { href: "/reports", label: t.nav.reports, icon: FileText },
      ],
    },
    {
      label: t.nav.groupMore,
      items: [
        { href: "/governance", label: t.nav.governance, icon: ShieldCheck },
        { href: "/methodology", label: t.nav.methodology, icon: BookOpen },
        { href: "/evaluation", label: t.nav.evaluation, icon: FlaskConical },
      ],
    },
  ];

  const activeTech = technologies.find((x) => x.id === selectedTechId) || technologies[0];

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {menuOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <div>
            <div className="text-xl font-bold tracking-tight text-blue-700">{t.appName}</div>
            <p className="mt-0.5 text-xs text-slate-500">{t.appSubtitle}</p>
          </div>
          <button
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="space-y-5 px-3 pb-6">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="px-3 pb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                {group.label}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={isActive ? "page" : undefined}
                      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-blue-50 text-blue-700"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                      }`}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              aria-label="Open menu"
              className="rounded-lg border border-slate-200 p-2 text-slate-700 hover:bg-slate-100 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <label htmlFor="tech-select" className="sr-only">
              {t.common.activeTechnology}
            </label>
            <select
              id="tech-select"
              value={selectedTechId || ""}
              onChange={(e) => setSelectedTechId(e.target.value)}
              className="min-w-0 max-w-[16rem] truncate rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200 sm:max-w-md"
            >
              {technologies.map((tech) => (
                <option key={tech.id} value={tech.id}>
                  {lang === "id" && tech.title_id ? tech.title_id : tech.title_en}
                </option>
              ))}
            </select>
            {activeTech?.is_synthetic_demo && (
              <Badge variant="warning" className="hidden sm:inline-flex">
                {t.fourOutputs.demoBadge}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="role-select" className="sr-only">
              {t.common.role}
            </label>
            <div className="flex items-center gap-1.5">
              <UserCheck className="hidden h-4 w-4 text-slate-500 sm:block" />
              <select
                id="role-select"
                value={activeRole}
                onChange={(e) => handleRoleSwitch(e.target.value as keyof typeof DEMO_ACCOUNTS)}
                className="rounded-xl border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-800"
              >
                <option value="analyst">Analyst ({userName.split(",")[0]})</option>
                <option value="expert_reviewer">Expert Reviewer</option>
                <option value="admin">Administrator</option>
              </select>
            </div>

            <div className="flex items-center rounded-xl border border-slate-300 bg-slate-100 p-0.5 text-sm">
              <Globe className="ml-2 mr-1 h-4 w-4 text-slate-500" />
              {(["en", "id"] as const).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  aria-pressed={lang === code}
                  className={`rounded-lg px-2.5 py-1.5 font-semibold transition ${
                    lang === code ? "bg-blue-600 text-white" : "text-slate-700 hover:bg-white"
                  }`}
                >
                  {code.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </header>

        {healthStatus === "degraded" && (
          <div className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-sm text-amber-900">
            {lang === "id"
              ? "Server sedang bermasalah. Beberapa data mungkin tidak tampil."
              : "The server is having trouble. Some data may not show."}
          </div>
        )}

        <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 p-4 sm:p-8">{children}</main>
      </div>
    </div>
  );
}