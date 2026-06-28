/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F4EFE5',
        'paper-deep': '#EBE4D5',
        surface: '#FBF8F1',
        ink: '#1F1B16',
        'ink-2': '#4A413A',
        'ink-3': '#7A726A',
        'ink-4': '#A89F93',
        rule: '#D9D2C5',
        'rule-soft': '#E8E1D1',
        terracotta: '#B85C38',
        'terracotta-deep': '#8C4326',
        'terracotta-wash': '#F1DDCD',
        sage: '#5B7C45',
        'sage-wash': '#DDE6CF',
        amber: '#B07A2C',
        'amber-wash': '#EFD9B2',
      },
      fontFamily: {
        display: ['Newsreader', 'Georgia', 'serif'],
        body: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        hand: ['Caveat', 'cursive'],
      },
    },
  },
  plugins: [],
}

