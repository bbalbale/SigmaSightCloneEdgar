const { fontFamily } = require("tailwindcss/defaultTheme")

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
  	container: {
  		center: true,
  		padding: '2rem',
  		screens: {
  			'2xl': '1400px'
  		}
  	},
  	extend: {
  		colors: {
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))',
  				// Position card design tokens
  				bg: 'hsl(0, 0%, 100%)',              // White (light theme)
  				'bg-dark': 'hsl(215, 28%, 17%)',     // slate-800 (dark theme)
  				'bg-hover': 'hsl(210, 20%, 98%)',    // gray-50 (light hover)
  				'bg-hover-dark': 'hsl(215, 25%, 20%)', // slate-750 (dark hover)
  				border: 'hsl(214, 32%, 91%)',        // gray-200 (light)
  				'border-dark': 'hsl(215, 20%, 35%)', // slate-700 (dark)
  				text: 'hsl(222, 47%, 11%)',          // gray-900 (light)
  				'text-dark': 'hsl(0, 0%, 100%)',     // white (dark)
  				'text-muted': 'hsl(215, 16%, 47%)',  // gray-600 (light)
  				'text-muted-dark': 'hsl(215, 20%, 65%)', // slate-400 (dark)
  				positive: 'hsl(158, 64%, 52%)',      // emerald-400
  				negative: 'hsl(0, 72%, 51%)',        // red-400
  				neutral: 'hsl(215, 20%, 65%)',       // slate-400
  			},
  			// Empty state design tokens
  			empty: {
  				bg: 'hsl(210, 20%, 98%)',            // gray-50 (light)
  				'bg-dark': 'hsla(215, 28%, 17%, 0.5)', // slate-800/50 (dark)
  				text: 'hsl(210, 13%, 50%)',          // gray-500 (light)
  				'text-dark': 'hsl(215, 20%, 65%)',   // slate-400 (dark)
  				border: 'hsl(214, 32%, 91%)',        // gray-200 (light)
  				'border-dark': 'hsl(215, 20%, 35%)', // slate-700 (dark)
  			},
  			// Badge design tokens (for section headers)
  			badge: {
  				bg: 'hsl(214, 32%, 91%)',            // gray-200 (light)
  				'bg-dark': 'hsl(215, 20%, 35%)',     // slate-700 (dark)
  				text: 'hsl(215, 16%, 47%)',          // gray-700 (light)
  				'text-dark': 'hsl(215, 20%, 65%)',   // slate-300 (dark)
  			},
  			sigmasight: {
  				primary: '#0066cc',
  				secondary: '#4f46e5',
  				accent: '#06b6d4',
  				success: '#10b981',
  				warning: '#f59e0b',
  				error: '#ef4444',
  				dark: '#1f2937',
  				light: '#f8fafc'
  			},
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		fontFamily: {
  			sans: [
  				'var(--font-sans)',
                    ...fontFamily.sans
                ]
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: 0
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: 0
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
}