/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dribbble-sidebar': '#1e2432',
        'dribbble-bg': '#f3f4f6',
        'dribbble-accent': '#00acee',
      }
    },
  },
  plugins: [],
}
