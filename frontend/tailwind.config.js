/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Arial', 'Helvetica', 'sans-serif'],
      },
      colors: {
        railway: {
          navy: '#102A56',
          blue: '#1F4B99',
          accent: '#2F6FED',
          page: '#F4F7FA',
          secondary: '#EEF3F8',
          border: '#D9E2EC',
          text: '#172033',
          muted: '#64748B'
        }
      }
    },
  },
  plugins: [],
}
