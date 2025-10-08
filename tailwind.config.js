/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx,html}'],
  theme: {
    extend: {
      colors: {
        positive: '#4CAF50',
        neutral: '#9E9E9E',
        negative: '#E53935',
        charcoal: '#2E2E2E',
        dimgray: '#666666',
        offwhite: '#F5F7FA',
        deepaqua: '#16525A',
        midblue: '#137784',
        aqua: '#00C9A7',
        lightaqua: '#5CE4CE',
        paleaqua: '#85FCE8',
      },
    },
  },
  plugins: [],
}
