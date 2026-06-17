/** @type {import('tailwindcss').Config} */
// YATS Tailwind config — compiled via the standalone CLI (no Node runtime needed).
// See assets/README.md for the build commands.
module.exports = {
  content: [
    './modules/**/templates/**/*.html',
    './modules/**/static/**/*.js',
    './sites/**/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // Brand colours carried over from the old Bootstrap 2 theme.
        brand: {
          DEFAULT: '#0088cc',
          dark: '#006dcc',
          light: '#33a3d6',
        },
      },
      width: {
        sidebar: '16rem',          // expanded sidebar (matches md:ml-64)
        'sidebar-collapsed': '4rem', // icon-only sidebar (matches md:ml-16)
      },
    },
  },
  plugins: [],
}
