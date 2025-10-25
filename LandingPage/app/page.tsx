"use client";

import { Shader, ChromaFlow, Swirl } from "shaders/react";
import { CustomCursor } from "@/components/custom-cursor";
import { GrainOverlay } from "@/components/grain-overlay";
import { WorkSection } from "@/components/privacy-section";
import { ServicesSection } from "@/components/features-section";
import { AboutSection } from "@/components/about-section";
import { ContactSection } from "@/components/contact-section";
import { MagneticButton } from "@/components/magnetic-button";
import { useRef, useEffect, useState } from "react";
import { useTypingAnimation } from "@/hooks/use-typing-animation";

export default function Home() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [currentSection, setCurrentSection] = useState(0);
  const [isLoaded, setIsLoaded] = useState(false);
  const touchStartY = useRef(0);
  const touchStartX = useRef(0);
  const shaderContainerRef = useRef<HTMLDivElement>(null);
  const scrollThrottleRef = useRef<number | undefined>(undefined);

  // Words for typing animation
  const animatedText = useTypingAnimation({
    words: [
      "Assistant",
      "Companion",
      "Helper",
      "Tutor",
      "Guide",
      "Mentor",
      "Coach",
      "Advisor",
    ],
    typingSpeed: 100,
    deletingSpeed: 50,
    pauseDuration: 2000,
  });

  useEffect(() => {
    const checkShaderReady = () => {
      if (shaderContainerRef.current) {
        const canvas = shaderContainerRef.current.querySelector("canvas");
        if (canvas && canvas.width > 0 && canvas.height > 0) {
          setIsLoaded(true);
          return true;
        }
      }
      return false;
    };

    if (checkShaderReady()) return;

    const intervalId = setInterval(() => {
      if (checkShaderReady()) {
        clearInterval(intervalId);
      }
    }, 100);

    const fallbackTimer = setTimeout(() => {
      setIsLoaded(true);
    }, 1500);

    return () => {
      clearInterval(intervalId);
      clearTimeout(fallbackTimer);
    };
  }, []);

  const scrollToSection = (index: number) => {
    if (scrollContainerRef.current) {
      const sectionWidth = scrollContainerRef.current.offsetWidth;
      scrollContainerRef.current.scrollTo({
        left: sectionWidth * index,
        behavior: "smooth",
      });
      setCurrentSection(index);
    }
  };

  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      touchStartY.current = e.touches[0].clientY;
      touchStartX.current = e.touches[0].clientX;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (Math.abs(e.touches[0].clientY - touchStartY.current) > 10) {
        e.preventDefault();
      }
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touchEndY = e.changedTouches[0].clientY;
      const touchEndX = e.changedTouches[0].clientX;
      const deltaY = touchStartY.current - touchEndY;
      const deltaX = touchStartX.current - touchEndX;

      if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 50) {
        if (deltaY > 0 && currentSection < 4) {
          scrollToSection(currentSection + 1);
        } else if (deltaY < 0 && currentSection > 0) {
          scrollToSection(currentSection - 1);
        }
      }
    };

    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener("touchstart", handleTouchStart, {
        passive: true,
      });
      container.addEventListener("touchmove", handleTouchMove, {
        passive: false,
      });
      container.addEventListener("touchend", handleTouchEnd, { passive: true });
    }

    return () => {
      if (container) {
        container.removeEventListener("touchstart", handleTouchStart);
        container.removeEventListener("touchmove", handleTouchMove);
        container.removeEventListener("touchend", handleTouchEnd);
      }
    };
  }, [currentSection]);

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();

        if (!scrollContainerRef.current) return;

        scrollContainerRef.current.scrollBy({
          left: e.deltaY,
          behavior: "instant",
        });

        const sectionWidth = scrollContainerRef.current.offsetWidth;
        const newSection = Math.round(
          scrollContainerRef.current.scrollLeft / sectionWidth
        );
        if (newSection !== currentSection) {
          setCurrentSection(newSection);
        }
      }
    };

    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener("wheel", handleWheel, { passive: false });
    }

    return () => {
      if (container) {
        container.removeEventListener("wheel", handleWheel);
      }
    };
  }, [currentSection]);

  useEffect(() => {
    const handleScroll = () => {
      if (scrollThrottleRef.current) return;

      scrollThrottleRef.current = requestAnimationFrame(() => {
        if (!scrollContainerRef.current) {
          scrollThrottleRef.current = undefined;
          return;
        }

        const sectionWidth = scrollContainerRef.current.offsetWidth;
        const scrollLeft = scrollContainerRef.current.scrollLeft;
        const newSection = Math.round(scrollLeft / sectionWidth);

        if (
          newSection !== currentSection &&
          newSection >= 0 &&
          newSection <= 4
        ) {
          setCurrentSection(newSection);
        }

        scrollThrottleRef.current = undefined;
      });
    };

    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener("scroll", handleScroll, { passive: true });
    }

    return () => {
      if (container) {
        container.removeEventListener("scroll", handleScroll);
      }
      if (scrollThrottleRef.current) {
        cancelAnimationFrame(scrollThrottleRef.current);
      }
    };
  }, [currentSection]);

  return (
    <main className="relative h-screen w-full overflow-hidden bg-background">
      <CustomCursor />
      <GrainOverlay />

      <div
        ref={shaderContainerRef}
        className={`fixed inset-0 z-0 transition-opacity duration-700 ${
          isLoaded ? "opacity-100" : "opacity-0"
        }`}
        style={{ contain: "strict" }}
      >
        <Shader className="h-full w-full">
          <Swirl
            colorA="#303841"
            colorB="#3A4750"
            speed={0.4}
            detail={0.5}
            blend={35}
            coarseX={20}
            coarseY={20}
            mediumX={15}
            mediumY={15}
            fineX={10}
            fineY={10}
          />
          <ChromaFlow
            baseColor="#00ADB5"
            upColor="#3A4750"
            downColor="#252C33"
            leftColor="#303841"
            rightColor="#33BFCA"
            intensity={0.7}
            radius={2.5}
            momentum={35}
            maskType="alpha"
            opacity={0.85}
          />
        </Shader>
        <div
          className="absolute inset-0 transition-colors duration-300"
          style={{
            backgroundColor: "rgba(48, 56, 65, 0.65)",
          }}
        />
      </div>

      <nav
        className={`fixed left-0 right-0 top-0 z-50 flex items-center justify-between px-6 py-6 transition-opacity duration-700 md:px-12 ${
          isLoaded ? "opacity-100" : "opacity-0"
        }`}
      >
        <button
          onClick={() => scrollToSection(0)}
          className="flex items-center gap-2 transition-transform hover:scale-105"
        >
          <div className="flex h-10 w-15 items-center justify-center rounded-lg bg-foreground/15 backdrop-blur-md transition-all duration-300 hover:scale-110 hover:bg-foreground/25">
            <span className="font-sans text-xl font-bold text-foreground">
              Canv
            </span>
          </div>
          <span className="font-sans text-xl font-semibold tracking-tight text-foreground">
            AI
          </span>
        </button>

        <div className="hidden items-center gap-8 md:flex">
          {["Home", "Features", "Privacy", "Install", "Contact"].map(
            (item, index) => (
              <button
                key={item}
                onClick={() => scrollToSection(index)}
                className={`group relative font-sans text-sm font-medium transition-all duration-300 ${
                  currentSection === index
                    ? "text-foreground scale-125"
                    : "text-foreground/80 hover:text-foreground scale-100"
                }`}
              >
                {item}
                <span
                  className={`absolute -bottom-1 left-0 h-px bg-foreground transition-all duration-300 ${
                    currentSection === index
                      ? "w-full"
                      : "w-0 group-hover:w-full"
                  }`}
                />
              </button>
            )
          )}
        </div>

        <div className="flex items-center gap-4">
          <MagneticButton
            variant="secondary"
            onClick={() => scrollToSection(4)}
          >
            Install Today
          </MagneticButton>
        </div>
      </nav>

      <div
        ref={scrollContainerRef}
        data-scroll-container
        className={`relative z-10 flex h-screen overflow-x-auto overflow-y-hidden transition-opacity duration-700 ${
          isLoaded ? "opacity-100" : "opacity-0"
        }`}
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {/* Hero Section */}
        <section className="flex min-h-screen w-screen shrink-0 items-center px-6 pt-24 pb-16 md:px-12 md:pb-24">
          <div className="mx-auto w-full max-w-7xl">
            <div className="grid gap-8 md:grid-cols-2 md:gap-32 lg:gap-40">
              {/* Left side - Hero content */}
              <div className="flex flex-col justify-center">
                <div className="mb-4 inline-block w-fit animate-in fade-in slide-in-from-bottom-4 rounded-full border border-foreground/20 bg-foreground/15 px-3 py-1 backdrop-blur-md duration-700">
                  <p className="font-mono text-xs text-foreground/90">
                    Full AI Integration
                  </p>
                </div>
                <h1 className="mb-6 animate-in fade-in slide-in-from-bottom-8 font-sans text-6xl font-light leading-[1.1] tracking-tight text-foreground duration-1000 md:text-7xl lg:text-8xl">
                  <span className="text-balance">
                    Your
                    <br />
                    <span className="whitespace-nowrap">
                      Personal{" "}
                      <span className="underline decoration-2 underline-offset-4">
                        {animatedText}
                      </span>
                      <span className="animate-pulse">|</span>
                    </span>
                  </span>
                </h1>
                <p className="mb-8 max-w-xl animate-in fade-in slide-in-from-bottom-4 text-lg leading-relaxed text-foreground/90 duration-1000 delay-200 md:text-xl">
                  <span className="text-pretty">
                    Welcome to the future of using Canvas.
                  </span>
                </p>
                <div className="flex animate-in fade-in slide-in-from-bottom-4 flex-col gap-4 duration-1000 delay-300 sm:flex-row sm:items-center">
                  <MagneticButton
                    size="lg"
                    variant="primary"
                    onClick={() =>
                      window.open(
                        "https://v0.app/templates/R3n0gnvYFbO",
                        "_blank"
                      )
                    }
                  >
                    Open The Github
                  </MagneticButton>
                  <MagneticButton
                    size="lg"
                    variant="secondary"
                    onClick={() => scrollToSection(2)}
                  >
                    View Demo
                  </MagneticButton>
                </div>
              </div>

              {/* Right side - Stats with creative layout */}
              <div className="flex flex-col justify-center space-y-6 md:space-y-12">
                {[
                  {
                    value: "+50%",
                    label: "Efficiency",
                    sublabel: "In Canvas Learning",
                    direction: "right",
                  },
                  {
                    value: "24/7",
                    label: "Support",
                    sublabel: "Always Available",
                    direction: "left",
                  },
                  {
                    value: "2hr",
                    label: "A Week",
                    sublabel: "Saved In Time",
                    direction: "right",
                  },
                ].map((stat, i) => {
                  const getRevealClass = () => {
                    if (!isLoaded) {
                      return stat.direction === "left"
                        ? "-translate-x-16 opacity-0"
                        : "translate-x-16 opacity-0";
                    }
                    return "translate-x-0 opacity-100";
                  };

                  return (
                    <div
                      key={i}
                      className={`flex items-baseline gap-4 border-l border-foreground/30 pl-4 transition-all duration-700 md:gap-8 md:pl-8 ${getRevealClass()}`}
                      style={{
                        transitionDelay: `${300 + i * 150}ms`,
                        marginLeft: i % 2 === 0 ? "0" : "auto",
                        maxWidth: i % 2 === 0 ? "100%" : "85%",
                      }}
                    >
                      <div className="text-3xl font-light text-foreground md:text-6xl lg:text-7xl">
                        {stat.value}
                      </div>
                      <div>
                        <div className="font-sans text-base font-light text-foreground md:text-xl">
                          {stat.label}
                        </div>
                        <div className="font-mono text-xs text-foreground/60">
                          {stat.sublabel}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-in fade-in duration-1000 delay-500">
            <div className="flex items-center gap-2">
              <p className="font-mono text-xs text-foreground/80">
                Scroll to explore
              </p>
              <div className="flex h-6 w-12 items-center justify-center rounded-full border border-foreground/20 bg-foreground/15 backdrop-blur-md">
                <div className="h-2 w-2 animate-pulse rounded-full bg-foreground/80" />
              </div>
            </div>
          </div>
        </section>

        <ServicesSection />
        <WorkSection />
        <AboutSection scrollToSection={scrollToSection} />
        <ContactSection />
      </div>

      <style jsx global>{`
        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </main>
  );
}
