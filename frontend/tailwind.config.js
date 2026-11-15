/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          page: '#0d1117',
          card: '#161b22',
          elevated: '#1c2128',
          subtle: '#21262d',
          hover: '#2d333b',
        },
        border: {
          base: '#30363d',
          muted: '#21262d',
          focus: '#4f6ef7',
        },
        accent: {
          DEFAULT: '#4f6ef7',
          light: '#7b95fa',
          dim: 'rgba(79, 110, 247, 0.12)',
          border: 'rgba(79, 110, 247, 0.3)',
        },
        text: {
          primary: '#e6edf3',
          secondary: '#8b949e',
          muted: '#484f58',
          inverse: '#0d1117',
        },
        status: {
          green: '#3fb950',
          greenDim: 'rgba(63, 185, 80, 0.12)',
          amber: '#d29922',
          amberDim: 'rgba(210, 153, 34, 0.12)',
          red: '#f85149',
          redDim: 'rgba(248, 81, 73, 0.12)',
          blue: '#388bfd',
          blueDim: 'rgba(56, 139, 253, 0.12)',
          purple: '#a371f7',
          purpleDim: 'rgba(163, 113, 247, 0.12)',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
      borderRadius: {
        sm: '6px',
        DEFAULT: '8px',
        md: '10px',
        lg: '12px',
      },
    },
  },
  plugins: [],
};
