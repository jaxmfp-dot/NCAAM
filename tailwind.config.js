export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        os: {
          bg:      '#070711',
          surface: '#0d0d1f',
          card:    '#0f0f23',
          border:  '#1e1e3f',
          purple:  '#7c3aed',
          'purple-light': '#9d4edd',
          blue:    '#2563eb',
          green:   '#059669',
          amber:   '#d97706',
          red:     '#dc2626',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 10px rgba(124, 58, 237, 0.3)' },
          to:   { boxShadow: '0 0 20px rgba(124, 58, 237, 0.7)' },
        }
      }
    },
  },
  plugins: [],
}
