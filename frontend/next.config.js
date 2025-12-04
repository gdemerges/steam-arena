/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [
      'avatars.steamstatic.com',
      'steamcdn-a.akamaihd.net',
      'media.steampowered.com',
      'cdn.cloudflare.steamstatic.com'
    ],
  },
}

module.exports = nextConfig
