import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: 'hsl(25, 100%, 97%)',
          100: 'hsl(25, 95%, 92%)',
          200: 'hsl(25, 90%, 82%)',
          300: 'hsl(25, 85%, 70%)',
          400: 'hsl(25, 80%, 58%)',
          500: 'hsl(25, 75%, 48%)',
          600: 'hsl(25, 80%, 40%)',
          700: 'hsl(25, 85%, 32%)',
          800: 'hsl(25, 90%, 24%)',
          900: 'hsl(25, 95%, 16%)',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
