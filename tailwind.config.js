/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx,html}"],
  theme: {
    extend: {
      colors: {
        happyblue: "#72CAE3",
        happygreen: "#8BDEA2",
        photoblue: "#D0F5FF",
        calmblue: "#A9CEF4",
        whiteblue: "#EFFFFD",
        cadetblue: "#2B2D42",
        backblue: "#D4E6F7",
      },
    },
  },
  plugins: [],
};
