"use client";

import { MagneticButton } from "@/components/magnetic-button";
import { useReveal } from "@/hooks/use-reveal";
import { Github } from "lucide-react";

export function AboutSection({
  scrollToSection,
}: {
  scrollToSection?: (index: number) => void;
}) {
  const { ref, isVisible } = useReveal(0.3);

  return (
    <section
      ref={ref}
      className="flex h-screen w-screen shrink-0 snap-start items-center px-4 pt-20 md:px-12 md:pt-0 lg:px-16"
    >
      <div className="mx-auto w-full max-w-7xl">
        <div className="grid gap-8 md:grid-cols-2 md:gap-16 lg:gap-24">
          {/* Left side - Story */}
          <div>
            <div
              className={`mb-6 transition-all duration-700 md:mb-12 ${
                isVisible
                  ? "translate-y-0 opacity-100"
                  : "-translate-y-12 opacity-0"
              }`}
            >
              <h2 className="mb-3 font-sans text-3xl font-light leading-[1.1] tracking-tight text-foreground md:mb-4 md:text-6xl lg:text-7xl">
                Ready To
                <br />
                Get Started?
                <br />
              </h2>
            </div>

            <div
              className={`space-y-3 transition-all duration-700 md:space-y-4 ${
                isVisible
                  ? "translate-y-0 opacity-100"
                  : "translate-y-8 opacity-0"
              }`}
              style={{ transitionDelay: "200ms" }}
            >
              <p className="max-w-md text-sm leading-relaxed text-foreground/90 md:text-xl">
                We're a team of designers, developers, data analysts, but most
                importantly students.
              </p>
              <p className="max-w-md text-sm leading-relaxed text-foreground/90 font-bold md:text-xl">
                Built by students, for students.
              </p>
            </div>
          </div>

          {/* Right side - Installation instructions */}
          <div className="flex flex-col justify-center">
            <div
              className={`transition-all duration-700 ${
                isVisible
                  ? "translate-y-0 opacity-100"
                  : "translate-y-12 opacity-0"
              }`}
              style={{ transitionDelay: "300ms" }}
            >
              <p className="text-center text-2xl font-light leading-relaxed text-foreground md:text-4xl lg:text-5xl">
                Follow the GitHub directory's directions for installation.
              </p>
            </div>
          </div>
        </div>

        <div
          className={`mt-8 flex flex-wrap gap-3 transition-all duration-700 md:mt-16 md:gap-4 ${
            isVisible ? "translate-y-0 opacity-100" : "translate-y-12 opacity-0"
          }`}
          style={{ transitionDelay: "750ms" }}
        >
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-foreground/10">
              <Github className="h-5 w-5 text-foreground" />
            </div>
            <MagneticButton
              size="lg"
              variant="primary"
              onClick={() =>
                window.open("https://github.com/OBress/CanvAI", "_blank")
              }
            >
              Open The Github
            </MagneticButton>
          </div>
        </div>
      </div>
    </section>
  );
}
