/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        navy: '#0B1F33',
        safety: {
          DEFAULT: '#FF7A1A',
          dark: '#E5680F',
          light: '#FFF1E6',
        },
        aqua: '#14B8A6',
        graphite: '#1F2937',
        mist: '#F5F7FA',
      },
      borderRadius: {
        card: '14px',
      },
      boxShadow: {
        card: '0 2px 12px rgba(11, 31, 51, 0.06)',
        pop: '0 8px 28px rgba(11, 31, 51, 0.14)',
      },
      fontFamily: {
        sans: [
          'PingFang SC',
          'Microsoft YaHei',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
