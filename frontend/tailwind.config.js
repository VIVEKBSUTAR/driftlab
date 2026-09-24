/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: {
          lowest: '#0a0e16',
          base: '#0f131c',
          low: '#181c24',
          container: '#1c2028',
          high: '#262a33',
          highest: '#31353e',
          bright: '#353942',
        },
        border: {
          subtle: '#1e293b',
          muted: '#262f3f',
          outline: '#3c4a42',
          focus: '#3b82f6',
        },
        telemetry: {
          emerald: '#10b981',
          emeraldLight: '#4edea3',
          indigo: '#6366f1',
          indigoLight: '#c0c1ff',
          violet: '#a855f7',
          violetLight: '#ddb7ff',
          amber: '#f59e0b',
          rose: '#ef4444',
          roseLight: '#ffb4ab',
        },
      },
      fontFamily: {
        sans: ['Geist', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

