"use client";

import { useReveal } from "@/hooks/use-reveal";

export function ServicesSection() {
  const { ref, isVisible } = useReveal(0.3);

  return (
    <section
      ref={ref}
      className="flex min-h-screen w-screen shrink-0 snap-start items-center px-6 py-20 md:px-12 lg:px-16"
    >
      <div className="mx-auto w-full max-w-7xl">
        <div
          className={`mb-12 transition-all duration-700 md:mb-16 ${
            isVisible
              ? "translate-y-0 opacity-100"
              : "-translate-y-12 opacity-0"
          }`}
        >
          <h2 className="mb-2 font-sans text-5xl font-light tracking-tight text-foreground md:text-6xl lg:text-7xl">
            Features
          </h2>
          <p className="font-mono text-sm text-foreground/60 md:text-base">
            / What we bring to the table
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-3 md:gap-x-8 lg:gap-x-12">
          {[
            {
              title: "Find Course Material",
              description:
                "Automatically find course material between lectures and assignments and answer your questions.",
              direction: "top",
            },
            {
              title: "Automatic What If Reports",
              description:
                "Can calculate theoritical grade scores for assignments and give back the grade in a class.",
              direction: "top",
            },
            {
              title: "Content On Your Midterm",
              description:
                "Scans your lectures and practice tests to create review material for your midterm exam.",
              direction: "top",
            },
          ].map((service, i) => (
            <ServiceCard
              key={i}
              service={service}
              index={i}
              isVisible={isVisible}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function ServiceCard({
  service,
  index,
  isVisible,
}: {
  service: { title: string; description: string; direction: string };
  index: number;
  isVisible: boolean;
}) {
  const getRevealClass = () => {
    if (!isVisible) {
      switch (service.direction) {
        case "left":
          return "-translate-x-16 opacity-0";
        case "right":
          return "translate-x-16 opacity-0";
        case "top":
          return "-translate-y-16 opacity-0";
        case "bottom":
          return "translate-y-16 opacity-0";
        default:
          return "translate-y-12 opacity-0";
      }
    }
    return "translate-x-0 translate-y-0 opacity-100";
  };

  return (
    <div
      className={`group flex flex-col transition-all duration-700 ${getRevealClass()}`}
      style={{
        transitionDelay: `${index * 150}ms`,
      }}
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="h-px w-8 bg-foreground/30 transition-all duration-300 group-hover:w-12 group-hover:bg-foreground/50" />
        <span className="font-mono text-xs text-foreground/60">
          0{index + 1}
        </span>
      </div>
      <h3 className="mb-2 font-sans text-2xl font-light text-foreground md:text-3xl">
        {service.title}
      </h3>
      <p className="mb-6 max-w-sm text-sm leading-relaxed text-foreground/80 md:text-base">
        {service.description}
      </p>

      {/* Floating Glass Panel Image Container */}
      <div className="relative mt-auto">
        <div
          className="group/image relative aspect-square w-full overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-2xl backdrop-blur-md transition-all duration-500 hover:scale-[1.02] hover:border-white/20 hover:bg-white/10 hover:shadow-[0_20px_60px_-15px_rgba(255,255,255,0.3)]"
          style={{
            transform: "translateZ(50px)",
          }}
        >
          {/* Placeholder for image - you can replace this div with an <img> tag */}
          <div className="flex h-full w-full items-center justify-center bg-linear-to-br from-white/10 to-transparent">
            <span className="font-mono text-xs text-foreground/40">
              Image {index + 1}
            </span>
          </div>

          {/* Glass reflection effect */}
          <div className="pointer-events-none absolute inset-0 bg-linear-to-tr from-transparent via-white/5 to-white/20" />

          {/* Glow effect on hover */}
          <div
            className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition-opacity duration-500 group-hover/image:opacity-100"
            style={{
              background:
                "linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%)",
            }}
          />
        </div>
      </div>
    </div>
  );
}
