module.exports = {
  content: ["./src/**/*.{ts,tsx,css,html}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Geist"', '"Geist Fallback"', "system-ui", "sans-serif"]
      },
      colors: {
        accent: "var(--color-accent)",
        background: "var(--color-dark-primary)"
      },
      borderRadius: {
        xl: "calc(var(--radius-base) + 0.5rem)"
      }
    }
  },
  corePlugins: {
    preflight: false
  }
};
