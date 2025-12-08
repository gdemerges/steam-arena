'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getGames, getPopularGames, getGenres, Game } from '@/lib/api'
import { MagnifyingGlassIcon, FunnelIcon } from '@heroicons/react/24/outline'

export default function GamesPage() {
  const [games, setGames] = useState<Game[]>([])
  const [popularGames, setPopularGames] = useState<Game[]>([])
  const [genres, setGenres] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedGenre, setSelectedGenre] = useState('')

  // Helper function to get Steam game header image
  const getGameImage = (game: Game) => {
    if (game.header_image) return game.header_image
    if (game.app_id) return `https://cdn.cloudflare.steamstatic.com/steam/apps/${game.app_id}/header.jpg`
    return null
  }

  const loadGames = async () => {
    setLoading(true)
    try {
      const params: { search?: string; genre?: string; limit: number } = { limit: 50 }
      if (search) params.search = search
      if (selectedGenre) params.genre = selectedGenre

      const [gamesRes, popularRes, genresRes] = await Promise.all([
        getGames(params),
        getPopularGames(10),
        getGenres(),
      ])
      setGames(gamesRes.data)
      setPopularGames(popularRes.data)
      setGenres(genresRes.data.map((g: { name: string }) => g.name))
    } catch (error) {
      console.error('Failed to load games:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGames()
  }, [search, selectedGenre])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadGames()
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Games Library</h1>
      </div>

      {/* Search and Filter */}
      <div className="card">
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search games..."
              className="input w-full pl-10"
            />
          </div>
          <div className="relative">
            <FunnelIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <select
              value={selectedGenre}
              onChange={(e) => setSelectedGenre(e.target.value)}
              className="input pl-10 pr-8 min-w-[200px]"
            >
              <option value="">All Genres</option>
              {genres.map((genre) => (
                <option key={genre} value={genre}>
                  {genre}
                </option>
              ))}
            </select>
          </div>
        </form>
      </div>

      {/* Popular Games */}
      {!search && !selectedGenre && popularGames.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">🔥 Popular in Your Library</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {popularGames.map((game) => (
              <Link key={game.id} href={`/games/${game.id}`} className="group">
                <div className="aspect-[460/215] rounded overflow-hidden bg-gray-700">
                  {getGameImage(game) ? (
                    <img
                      src={getGameImage(game)!}
                      alt={game.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-500">
                      No Image
                    </div>
                  )}
                </div>
                <p className="text-sm mt-2 truncate">{game.name}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Games Grid */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">
          {search || selectedGenre ? 'Search Results' : 'All Games'} ({games.length})
        </h2>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="aspect-[460/215] bg-gray-700 rounded"></div>
                <div className="h-4 bg-gray-700 rounded w-3/4 mt-2"></div>
              </div>
            ))}
          </div>
        ) : games.length === 0 ? (
          <p className="text-gray-400 text-center py-12">
            {search || selectedGenre
              ? 'No games found matching your criteria'
              : 'No games in library yet. Add some users to populate games.'}
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {games.map((game) => (
              <Link
                key={game.id}
                href={`/games/${game.id}`}
                className="bg-gray-700/50 rounded-lg overflow-hidden hover:bg-gray-700 transition-colors block"
              >
                <div className="aspect-[460/215] bg-gray-700">
                  {getGameImage(game) ? (
                    <img
                      src={getGameImage(game)!}
                      alt={game.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-500">
                      No Image
                    </div>
                  )}
                </div>
                <div className="p-3">
                  <h3 className="font-medium truncate">{game.name}</h3>
                  {game.developer && (
                    <p className="text-sm text-gray-400 truncate">{game.developer}</p>
                  )}
                  <div className="flex items-center justify-between mt-2">
                    {game.metacritic_score && (
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          game.metacritic_score >= 75
                            ? 'bg-green-500/20 text-green-400'
                            : game.metacritic_score >= 50
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {game.metacritic_score}
                      </span>
                    )}
                    {game.is_free && (
                      <span className="px-2 py-0.5 bg-steam-blue/20 text-steam-blue rounded text-xs">
                        Free
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
