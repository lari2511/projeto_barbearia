module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx,html}'
  ],
  theme: {
    extend: {
      colors: {
        'brand-orange': {
          DEFAULT: '#f97316',
          600: '#f97316',
          500: '#fb923c',
          700: '#ea580c'
        },
        'brand-red': '#ff3b30',
        'brand-emerald': {
          DEFAULT: '#10b981',
          500: '#10b981',
          400: '#34d399'
        },
        'panel-bg': '#0f1720',
        'panel-ink': '#e6e6e6'
      },
      borderRadius: {
        '2xl': '1rem',
        'xl-lg': '0.75rem'
      },
      fontFamily: {
        sans: ['Poppins', 'Inter', 'system-ui', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial']
      },
      boxShadow: {
        'panel': '0 10px 30px rgba(0,0,0,0.6)',
        'brand-lg': '0 14px 36px rgba(249,115,22,0.22)'
      }
      ,
      letterSpacing: {
        tightest: '-0.02em',
        tight: '-0.01em',
        wide: '0.02em',
        wider: '0.06em'
      },
      fontSize: {
        'ui-sm': ['13px', '18px'],
        'ui-base': ['15px', '22px'],
        'ui-lg': ['18px', '26px']
      }
    },
  },
  plugins: [],
}
