/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#00E676", // Verde vibrante da logo FECAP
          dark: "#002B18",    // Tipografia escura "FECAP"
          text: "#0B2513",
        },
        primary: {
          DEFAULT: "#004225", // Verde institucional
          50: "#F0F7F3",
          100: "#D9EBE0",
          200: "#B3D7C1",
          300: "#80BA97",
          400: "#3D9865",
          500: "#004225",
          600: "#00361E",
          700: "#002B18",
          800: "#001F11",
          900: "#00140B",
        },
        fecapBg: "#F4F8F5",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};