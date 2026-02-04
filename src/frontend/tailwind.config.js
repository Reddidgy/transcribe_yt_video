/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#A8F78B",
                background: "#0D1310",
                surface: "#16201B",
                onSurface: "#FFFFFF",
                textPrimary: "#FFFFFF",
                textSecondary: "#A0B0A8",
                border: "#33403A",
            },
            fontFamily: {
                sans: ['Manrope', 'sans-serif'],
            },
            borderRadius: {
                'sm': '4px',
                'md': '8px',
                'lg': '16px',
            },
            boxShadow: {
                'premium': '0 0 20px 0 rgba(168, 247, 139, 0.1)',
            }
        },
    },
    plugins: [],
}
