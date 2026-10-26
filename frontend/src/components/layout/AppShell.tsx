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
  Database,
} from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { lang, setLang, t, selectedTechId, setSelectedTechId } = useAppState();
  const [technologies, setTechnologies] = useState<TechnologyItem[]>([]);
  const [activeRole, setActiveRole] = useState<UserRole>("analyst");
  const [userName, setUserName] = useState<string>("Rina Kusuma, M.T.");
  const [healthStatus, setHealthStatus] = useState<string>("checking...");

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

  const navItems = [
    { href: "/", label: t.nav.portfolio, icon: LayoutDashboard },
    { href: "/submission", label: t.nav.submission, icon: FileUp },
    { href: "/pipeline", label: t.nav.pipeline, icon: Cpu },
    { href: "/assessment", label: t.nav.assessment, icon: Microscope },
    { href: "/commercialization", label: t.nav.commercialization, icon: TrendingUp },
    { href: "/valuation", label: t.nav.valuation, icon: Calculator },
    { href: "/governance", label: t.nav.governance, icon: ShieldCheck },
    { href: "/reports", label: t.nav.reports, icon: FileText },
    { href: "/methodology", label: t.nav.methodology, icon: BookOpen },
    { href: "/evaluation", label: t.nav.evaluation, icon: FlaskConical },
  ];

  const activeTech = technologies.find((x) => x.id === selectedTechId) || technologies[0];

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 border-r border-slate-200 bg-slate-900 text-slate-100 flex flex-col justify-between">
        <div>
          <div className="border-b border-slate-800 px-5 py-4">
            <div className="flex items-center justify-between">
              <span className="text-lg font-bold tracking-tight text-white">
                {t.appName}
              </span>
              <Badge variant="info" className="bg-blue-900/70 text-blue-200 border-blue-700">
                v1.0 • IDR
              </Badge>
            </div>
            <p className="mt-1 text-xs text-slate-400 leading-snug">{t.appSubtitle}</p>
          </div>

          <nav className="space-y-1 p-3">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="border-t border-slate-800 p-4 text-[11px] text-slate-400 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5 text-emerald-400" />
              PostgreSQL 16 + Vault
            </span>
            <span
              className={`font-semibold uppercase ${
                healthStatus === "ok" ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {healthStatus}
            </span>
          </div>
          <div>WIPO IP Valuation • NASA TRL 1–9 • Saaty AHP</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top Header */}
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              {t.common.activeTechnology}:
            </label>
            <select
              value={selectedTechId || ""}
              onChange={(e) => setSelectedTechId(e.target.value)}
              className="rounded-md border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-900 focus:border-blue-600 focus:outline-none"
            >
              {technologies.map((tech) => (
                <option key={tech.id} value={tech.id}>
                  [{tech.code}] {lang === "id" && tech.title_id ? tech.title_id : tech.title_en}
                </option>
              ))}
            </select>
            {activeTech?.is_synthetic_demo && (
              <Badge variant="warning">{t.fourOutputs.demoBadge}</Badge>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Role Switcher */}
            <div className="flex items-center gap-1.5 text-xs">
              <UserCheck className="h-4 w-4 text-slate-600" />
              <span className="text-slate-500">{t.common.role}:</span>
              <select
                value={activeRole}
                onChange={(e) =>
                  handleRoleSwitch(e.target.value as keyof typeof DEMO_ACCOUNTS)
                }
                className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-800"
              >
                <option value="analyst">Analyst ({userName.split(",")[0]})</option>
                <option value="expert_reviewer">Expert Reviewer</option>
                <option value="admin">Administrator</option>
              </select>
            </div>

            {/* Bilingual Toggle */}
            <div className="flex items-center rounded-md border border-slate-300 bg-slate-100 p-0.5 text-xs">
              <Globe className="ml-1.5 mr-1 h-3.5 w-3.5 text-slate-600" />
              <button
                type="button"
                onClick={() => setLang("en")}
                className={`rounded px-2 py-0.5 font-semibold transition ${
                  lang === "en" ? "bg-blue-700 text-white" : "text-slate-700"
                }`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang("id")}
                className={`rounded px-2 py-0.5 font-semibold transition ${
                  lang === "id" ? "bg-blue-700 text-white" : "text-slate-700"
                }`}
              >
                ID
              </button>
            </div>
          </div>
        </header>

        {/* Page Body */}
        <main className="flex-1 p-6 space-y-6 max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
