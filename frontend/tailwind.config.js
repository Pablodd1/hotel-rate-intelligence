/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        ember: {
          deep: '#06122E',
          navy: '#0D255B',
          royal: '#1744A6',
          blue: '#2563EB',
          sky: '#3B82F6',
          canvas: '#F2F6FD',
          card: '#FFFFFF',
          border: '#DCE7F8',
          subtle: '#E8F0FE',
        },
      },
      boxShadow: {
        emberShell: '0 24px 60px rgba(4, 15, 42, 0.35)',
        emberCard: '0 8px 24px rgba(15, 38, 92, 0.06)',
        emberSidebar: '0 20px 50px rgba(3, 10, 30, 0.45)',
      },
    },
  },
  plugins: [],
}
