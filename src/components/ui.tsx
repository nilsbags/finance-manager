"use client";

import { useState, type ReactNode } from "react";

/** Bordered card, the basic building block of every page. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-4 ${className}`}>{children}</div>
  );
}

/**
 * Big-number metric card with an optional month-over-month delta.
 * `deltaColor="inverse"` flips the good/bad colouring (spending more is bad).
 */
export function MetricCard({
  label,
  value,
  delta,
  deltaColor = "normal",
  boxed = true,
}: {
  label: string;
  value: string;
  delta?: string | null;
  deltaColor?: "normal" | "inverse";
  boxed?: boolean;
}) {
  const negative = delta?.startsWith("-") ?? false;
  const good = deltaColor === "inverse" ? negative : !negative;
  const inner = (
    <div>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-[2rem] font-bold leading-tight">{value}</div>
      {delta != null && (
        <div className={`mt-1 text-sm font-medium ${good ? "text-green-600" : "text-red-600"}`}>
          {negative ? "↓" : "↑"} {delta}
        </div>
      )}
    </div>
  );
  return boxed ? <Card>{inner}</Card> : inner;
}

/** Collapsible section, the Streamlit `st.expander` equivalent. */
export function Expander({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details
      className="group rounded-xl border border-slate-200 bg-white open:pb-4"
      open={defaultOpen}
    >
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-700 hover:text-slate-900">
        {title}
      </summary>
      <div className="px-4">{children}</div>
    </details>
  );
}

/** Info / success / warning note (st.info, st.success, st.warning). */
export function Notice({
  kind = "info",
  children,
}: {
  kind?: "info" | "success" | "warning";
  children: ReactNode;
}) {
  const styles = {
    info: "border-sky-200 bg-sky-50 text-sky-900",
    success: "border-green-200 bg-green-50 text-green-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
  }[kind];
  return <div className={`rounded-lg border px-4 py-3 text-sm ${styles}`}>{children}</div>;
}

export function Button({
  children,
  onClick,
  variant = "secondary",
  disabled = false,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const styles = {
    primary: "bg-slate-900 text-white hover:bg-slate-700",
    secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
    danger: "bg-red-600 text-white hover:bg-red-500",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${styles}`}
    >
      {children}
    </button>
  );
}

export function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-600">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-500 focus:outline-none";

export function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label?: string }[] | string[];
  onChange: (value: string) => void;
}) {
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <Labeled label={label}>
      <select className={inputClass} value={value} onChange={(e) => onChange(e.target.value)}>
        {opts.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label ?? o.value}
          </option>
        ))}
      </select>
    </Labeled>
  );
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <Labeled label={label}>
      <input
        type="text"
        className={inputClass}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </Labeled>
  );
}

export function Checkbox({
  label,
  checked,
  onChange,
  disabled = false,
  help,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  help?: string;
}) {
  return (
    <label
      className={`flex items-start gap-2 text-sm ${disabled ? "opacity-40" : "cursor-pointer"}`}
      title={help}
    >
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 accent-slate-900"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="font-medium text-slate-700">{label}</span>
    </label>
  );
}

/** On/off switch (st.toggle). */
export function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
      <span
        role="switch"
        aria-checked={checked}
        onClick={(e) => {
          e.preventDefault();
          onChange(!checked);
        }}
        className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
          checked ? "bg-slate-900" : "bg-slate-300"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </span>
      {label}
    </label>
  );
}

export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  help,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  help?: string;
}) {
  return (
    <Labeled label={`${label}: ${value}`}>
      <input
        type="range"
        className="w-full accent-slate-900"
        title={help}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </Labeled>
  );
}

/** Horizontal pill radio group (the period switcher). */
export function RadioPills({
  options,
  value,
  onChange,
}: {
  options: readonly string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            value === opt ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

/** Toggleable chips, the st.multiselect stand-in (empty selection = all). */
export function MultiSelectChips({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}) {
  const toggle = (opt: string) =>
    onChange(selected.includes(opt) ? selected.filter((s) => s !== opt) : [...selected, opt]);
  return (
    <div className="text-sm">
      <span className="mb-1 block font-medium text-slate-600">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => {
          const active = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(opt)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                active
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-300 bg-white text-slate-600 hover:border-slate-500"
              }`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function Tabs({ tabs }: { tabs: { label: string; content: ReactNode }[] }) {
  const [active, setActive] = useState(0);
  return (
    <div>
      <div className="mb-4 flex gap-4 border-b border-slate-200">
        {tabs.map((tab, i) => (
          <button
            key={tab.label}
            type="button"
            onClick={() => setActive(i)}
            className={`-mb-px border-b-2 px-1 pb-2 text-sm font-medium transition-colors ${
              i === active
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs[active].content}
    </div>
  );
}

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="mb-1 text-3xl font-bold">{children}</h1>;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="mb-3 mt-8 text-xl font-semibold">{children}</h2>;
}

export function Caption({ children }: { children: ReactNode }) {
  return <p className="text-sm text-slate-500">{children}</p>;
}
