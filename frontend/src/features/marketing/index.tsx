/**
 * Placeholder pages for `features/marketing` (T-043 replaces this folder; ADR-0035).
 * Named exports: LandingPage, PricingPage, TermsPage, PrivacyPage, DisclaimerPage, SecurityPage.
 */
import { ArrowRight, FileSignature, Globe, ListChecks, Lock, Scale, Tag } from "lucide-react";
import { Link } from "react-router-dom";

import { AgentAvatar } from "@/agents";
import { PlaceholderPage } from "@/app";
import { TAGLINE, useBrandName, useDisclaimer } from "@/brand";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, TrustNote, buttonVariants } from "@/design";

const HIGHLIGHTS = [
  { agent: "law" as const, icon: FileSignature, title: "Founding documents", text: "Drafted from your answers, signed online by every founder." },
  { agent: "name" as const, icon: Tag, title: "A name and a domain", text: "Name ideas with live domain checks and the state search link." },
  { agent: "website" as const, icon: Globe, title: "A website", text: "Built, checked and published for you." },
  { agent: "guide" as const, icon: ListChecks, title: "A filing checklist", text: "Every registration step for your state, with deadlines." },
];

export function LandingPage() {
  const brand = useBrandName();
  const disclaimer = useDisclaimer();
  return (
    <div data-page="landing">
      <section className="border-b bg-surface">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 sm:px-6 sm:py-20 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <div className="grid gap-5">
            <p className="inline-flex w-fit items-center gap-2 rounded-full border bg-primary-soft px-3 py-1 text-xs font-medium text-primary">
              <Scale size={14} aria-hidden="true" />
              For founders starting a US company
            </p>
            <h1 className="text-3xl font-semibold leading-tight text-text sm:text-5xl sm:leading-tight">{TAGLINE}</h1>
            <p className="max-w-xl text-lg text-text-muted">
              {brand} gives you a Manager and specialist agents who take you from idea to a formed company: facts, name,
              documents, cap table, website and the filing checklist.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/signup" className={buttonVariants({ size: "lg" })}>
                Get started free
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Link to="/pricing" className={buttonVariants({ size: "lg", variant: "secondary" })}>
                See pricing
              </Link>
            </div>
            <TrustNote kind="disclaimer">{disclaimer}</TrustNote>
          </div>
          <Card raised className="p-5">
            <div className="grid gap-4">
              {HIGHLIGHTS.map((h) => (
                <div key={h.title} className="flex items-start gap-3">
                  <AgentAvatar agent={h.agent} />
                  <div className="grid gap-0.5">
                    <p className="text-sm font-semibold text-text">{h.title}</p>
                    <p className="text-sm text-text-muted">{h.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </section>
      <section className="mx-auto grid max-w-6xl gap-4 px-4 py-12 sm:px-6 md:grid-cols-3">
        {[
          ["Answer a few questions", "Chat with the Manager about your business and your co-founders."],
          ["Review and sign", "Read every document, ask the Law Agent, then sign online."],
          ["Launch", "Publish your website and follow the checklist to file."],
        ].map(([title, text], i) => (
          <Card key={title}>
            <CardHeader>
              <span className="text-sm font-semibold text-primary">Step {i + 1}</span>
              <CardTitle>{title}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>{text}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </section>
      <section className="mx-auto max-w-6xl px-4 pb-14 sm:px-6">
        <TrustNote kind="security">
          Your documents and conversations are private to your company. We never ask for Social Security numbers.
        </TrustNote>
      </section>
    </div>
  );
}

export function PricingPage() {
  return <PlaceholderPage title="Pricing" description="Free, Launch and Team plans." emptyDescription="Plan details are on their way." />;
}

export function TermsPage() {
  return <PlaceholderPage title="Terms of service" emptyDescription="The terms are on their way." />;
}

export function PrivacyPage() {
  return <PlaceholderPage title="Privacy" emptyDescription="The privacy notice is on its way." />;
}

export function DisclaimerPage() {
  const disclaimer = useDisclaimer();
  return <PlaceholderPage title="Disclaimer" description={disclaimer} emptyDescription="The full disclaimer is on its way." />;
}

export function SecurityPage() {
  return <PlaceholderPage title="Security" emptyDescription="How we protect your data is described here soon." icon={Lock} />;
}
