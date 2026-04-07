/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00D4FF',
          50: '#E6FBFF',
          100: '#B3F3FF',
          200: '#80EBFF',
          300: '#4DE3FF',
          400: '#1ADBFF',
          500: '#00D4FF',
          600: '#00A8CC',
          700: '#007D99',
          800: '#005266',
          900: '#002733',
        },
        violet: {
          DEFAULT: '#7C3AED',
          500: '#7C3AED',
          600: '#6D28D9',
          700: '#5B21B6',
        },
        mint: {
          DEFAULT: '#06FFA5',
          500: '#06FFA5',
          600: '#00CC84',
        },
        rose: {
          DEFAULT: '#FF4D6D',
          500: '#FF4D6D',
        },
        amber: {
          DEFAULT: '#FFB800',
          500: '#FFB800',
        },
        space: {
          950: '#030310',
          900: '#050515',
          850: '#070720',
          800: '#0A0A25',
          750: '#0D0D30',
          700: '#10103A',
          600: '#141450',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'nebula': 'radial-gradient(ellipse at 20% 50%, rgba(124,58,237,0.15) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(0,212,255,0.1) 0%, transparent 60%)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'gradient-shift': 'gradientShift 8s ease infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'spin-slow': 'spin 8s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0,212,255,0.3)',
        'glow-violet': '0 0 20px rgba(124,58,237,0.3)',
        'glow-mint': '0 0 20px rgba(6,255,165,0.3)',
        'glass': '0 8px 32px rgba(0,0,0,0.4)',
        'glass-lg': '0 16px 48px rgba(0,0,0,0.5)',
        'inner-glow': 'inset 0 1px 0 rgba(255,255,255,0.1)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
