/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        // Base — zinc scale
        canvas:  '#09090b',   // zinc-950
        surface: '#18181b',   // zinc-900
        raised:  '#27272a',   // zinc-800
        border:  '#3f3f46',   // zinc-700
        'border-subtle': '#27272a',

        // Text — readable on dark
        'text-primary':   '#fafafa',   // zinc-50  — headlines, values
        'text-secondary': '#a1a1aa',   // zinc-400 — body
        'text-muted':     '#71717a',   // zinc-500 — supporting
        'text-dim':       '#52525b',   // zinc-600 — labels, meta

        // Semantic
        indigo: {
          DEFAULT: '#818cf8',
          dim:    'rgba(129,140,248,0.1)',
          border: 'rgba(129,140,248,0.3)',
        },
        green: {
          DEFAULT: '#4ade80',
          dim:    'rgba(74,222,128,0.1)',
          border: 'rgba(74,222,128,0.25)',
        },
        red: {
          DEFAULT: '#f87171',
          dim:    'rgba(248,113,113,0.1)',
          border: 'rgba(248,113,113,0.25)',
        },
        amber: {
          DEFAULT: '#fbbf24',
          dim:    'rgba(251,191,36,0.1)',
          border: 'rgba(251,191,36,0.25)',
        },
        blue: {
          DEFAULT: '#60a5fa',
          dim:    'rgba(96,165,250,0.1)',
          border: 'rgba(96,165,250,0.25)',
        },
        purple: {
          DEFAULT: '#c084fc',
          dim:    'rgba(192,132,252,0.1)',
          border: 'rgba(192,132,252,0.25)',
        },
      },
    },
  },
  plugins: [],
}
