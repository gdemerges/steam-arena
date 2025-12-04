/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        steam: {
          dark: '#171a21',
          darker: '#1b2838',
          blue: '#66c0f4',
          'blue-dark': '#1a9fff',
          green: '#5c7e10',
          'green-light': '#a4d007',
        },
      },
    },
  },
  plugins: [],
}
