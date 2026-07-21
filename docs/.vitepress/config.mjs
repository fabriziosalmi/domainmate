import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "DomainMate",
  description: "Domain and Security Monitoring System",
  base: '/domainmate/',
  
  head: [
    // Everything this site loads is first-party. 'unsafe-inline' is required
    // because VitePress emits an inline appearance script and inline styles.
    // Applied to the built site only: `vitepress dev` serves HMR over a
    // websocket, which a strict connect-src would block as soon as the dev
    // server is not same-origin (--host, or a custom server.hmr.port).
    ...(process.env.NODE_ENV === 'production'
      ? [
          [
            'meta',
            {
              'http-equiv': 'Content-Security-Policy',
              content:
                "default-src 'self'; script-src 'self' 'unsafe-inline'; " +
                "style-src 'self' 'unsafe-inline'; img-src 'self' data:; " +
                "font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'",
            },
          ],
        ]
      : []),
    ['link', { rel: 'icon', href: '/domainmate/favicon.ico' }]
  ],

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: '/logo.svg',
    
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' },
      { text: 'Guide', link: '/guide/configuration' },
      { text: 'Reference', link: '/reference/architecture' }
    ],

    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'What is DomainMate?', link: '/' },
          { text: 'Getting Started', link: '/getting-started' }
        ]
      },
      {
        text: 'Guide',
        items: [
          { text: 'Configuration', link: '/guide/configuration' },
          { text: 'Monitors', link: '/guide/monitors' },
          { text: 'Notifications', link: '/guide/notifications' },
          { text: 'CLI Usage', link: '/guide/cli' },
          { text: 'API', link: '/guide/api' },
          { text: 'CI/CD Integration', link: '/guide/ci-cd' }
        ]
      },
      {
        text: 'Reference',
        items: [
          { text: 'Architecture', link: '/reference/architecture' },
          { text: 'Troubleshooting', link: '/reference/troubleshooting' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/fabriziosalmi/domainmate' }
    ],

    footer: {
      message: 
        'Released under the MIT License. · <a href="https://fabriziosalmi.github.io/privacy">Privacy &amp; legal</a>',
      copyright: 'Copyright © 2024-present DomainMate'
    },

    search: {
      provider: 'local'
    }
  }
})
