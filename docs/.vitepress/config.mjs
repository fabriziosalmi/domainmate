import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "DomainMate",
  description: "Domain and Security Monitoring System",
  base: '/domainmate/',
  
  head: [
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
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024-present DomainMate'
    },

    search: {
      provider: 'local'
    }
  }
})
