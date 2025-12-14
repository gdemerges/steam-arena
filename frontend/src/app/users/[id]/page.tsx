'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getUser,
  getUserGames,
  getUserDashboard,
  getUserPlaytimeByGenre,
  getUserYearlyStats,
  getUserMonthlyStats,
  syncUserProfile,
  syncUserGames,
  SteamUser,
  UserGame,
  YearlyStats,
  MonthlyStats,
} from '@/lib/api'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ClockIcon,
  TrophyIcon,
  Squares2X2Icon,
  ChevronUpIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const COLORS = [
  '#FF6B6B', // Rouge corail
  '#4ECDC4', // Turquoise
  '#FFD93D', // Jaune doré
  '#95E1D3', // Vert menthe
  '#F38181', // Rose saumon
  '#AA96DA', // Violet pastel
  '#FCBF49', // Orange ambré
  '#06D6A0', // Vert émeraude
  '#118AB2', // Bleu océan
  '#EF476F', // Rose vif
  '#FFB703', // Orange lumineux
  '#8338EC', // Violet profond
]

interface UserDashboard {
  user: SteamUser
  stats: {
    total_games: number
    total_playtime: number
    total_playtime_hours: number
    games_played: number
    games_never_played: number
    total_achievements: number
    achievements_unlocked: number
    completion_rate: number
  }
  top_played_games: Array<{
    game: { name: string; app_id: number }
    playtime_forever: number
    playtime_hours: number
  }>
  recent_games: Array<{
    game: { name: string; app_id: number }
    playtime_2weeks: number
    last_played: string
  }>
}

interface GenrePlaytime {
  genre: string
  total_playtime_minutes: number
  total_playtime_hours: number
  game_count: number
  avg_playtime_minutes: number
  percentage: number
}

export default function UserDetailPage() {
  const params = useParams()
  const userId = params.id as string

  const [user, setUser] = useState<SteamUser | null>(null)
  const [dashboard, setDashboard] = useState<UserDashboard | null>(null)
  const [games, setGames] = useState<UserGame[]>([])
  const [genreData, setGenreData] = useState<GenrePlaytime[]>([])
  const [yearlyStats, setYearlyStats] = useState<YearlyStats[]>([])
  const [monthlyStats, setMonthlyStats] = useState<MonthlyStats[]>([])
  const [selectedStatsYear, setSelectedStatsYear] = useState(new Date().getFullYear())
  const [viewMode, setViewMode] = useState<'yearly' | 'monthly'>('yearly')
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [sortBy, setSortBy] = useState<'playtime' | 'recent' | 'name'>('playtime')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [showPlaytimeModal, setShowPlaytimeModal] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [userRes, dashboardRes, gamesRes, genreRes, yearlyRes] = await Promise.all([
        getUser(userId),
        getUserDashboard(userId),
        getUserGames(userId, { limit: 500, sort_by: 'playtime' }),
        getUserPlaytimeByGenre(userId),
        getUserYearlyStats(userId).catch(() => ({ data: [] })),
      ])
      setUser(userRes.data)
      setDashboard(dashboardRes.data)
      setGames(gamesRes.data)
      setGenreData(genreRes.data)
      setYearlyStats(yearlyRes.data)
      
      // Load monthly stats for current year
      loadMonthlyStats(selectedStatsYear)
    } catch (error) {
      console.error('Failed to load user data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadMonthlyStats = async (year: number) => {
    try {
      const monthlyRes = await getUserMonthlyStats(userId, year).catch(() => ({ data: [] }))
      setMonthlyStats(monthlyRes.data)
    } catch (error) {
      console.error('Failed to load monthly stats:', error)
    }
  }

  useEffect(() => {
    loadData()
  }, [userId])

  // Sort games based on current sort settings
  const sortedGames = [...games].sort((a, b) => {
    let comparison = 0
    switch (sortBy) {
      case 'playtime':
        comparison = (a.playtime_forever || 0) - (b.playtime_forever || 0)
        break
      case 'recent':
        comparison = (a.playtime_2weeks || 0) - (b.playtime_2weeks || 0)
        break
      case 'name':
        comparison = (a.game?.name || '').localeCompare(b.game?.name || '')
        break
    }
    return sortOrder === 'desc' ? -comparison : comparison
  })

  const handleSort = (column: 'playtime' | 'recent' | 'name') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const SortIcon = ({ column }: { column: 'playtime' | 'recent' | 'name' }) => {
    if (sortBy !== column) return null
    return sortOrder === 'desc' ? (
      <ChevronDownIcon className="h-4 w-4 inline ml-1" />
    ) : (
      <ChevronUpIcon className="h-4 w-4 inline ml-1" />
    )
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncUserProfile(userId)
      await syncUserGames(userId)
      await loadData()
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="card animate-pulse">
          <div className="flex items-center gap-6">
            <div className="w-24 h-24 bg-gray-700 rounded-full"></div>
            <div className="flex-1">
              <div className="h-8 bg-gray-700 rounded w-1/3 mb-3"></div>
              <div className="h-4 bg-gray-700 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">User not found</p>
        <Link href="/users" className="btn-primary mt-4 inline-block">
          Back to Users
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <Link href="/users" className="inline-flex items-center gap-2 text-gray-400 hover:text-white">
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Users
        </Link>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-secondary flex items-center gap-2"
        >
          <ArrowPathIcon className={`h-5 w-5 ${syncing ? 'animate-spin' : ''}`} />
          Sync
        </button>
      </div>

      {/* User Profile Card */}
      <div className="card">
        <div className="flex items-center gap-6">
          <img
            src={user.avatar_full_url || user.avatar_url || '/default-avatar.png'}
            alt={user.persona_name}
            className="w-24 h-24 rounded-full"
          />
          <div className="flex-1">
            <h1 className="text-3xl font-bold">{user.persona_name}</h1>
            <p className="text-gray-400">Steam ID: {user.steam_id}</p>
            {user.country_code && (
              <p className="text-gray-500">Country: {user.country_code}</p>
            )}
            <a
              href={user.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-steam-blue hover:underline text-sm"
            >
              View Steam Profile →
            </a>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <Squares2X2Icon className="h-8 w-8 text-purple-400" />
            <div>
              <p className="text-sm text-gray-400">Games</p>
              <p className="text-2xl font-bold">{dashboard?.stats?.total_games || 0}</p>
            </div>
          </div>
        </div>
        <button 
          onClick={() => setShowPlaytimeModal(true)}
          className="card hover:bg-gray-700/50 transition-colors cursor-pointer text-left w-full"
        >
          <div className="flex items-center gap-3">
            <ClockIcon className="h-8 w-8 text-yellow-400" />
            <div>
              <p className="text-sm text-gray-400">Playtime</p>
              <p className="text-2xl font-bold">{(dashboard?.stats?.total_playtime_hours || 0).toFixed(0)}h</p>
            </div>
          </div>
        </button>
        <div className="card">
          <div className="flex items-center gap-3">
            <TrophyIcon className="h-8 w-8 text-orange-400" />
            <div>
              <p className="text-sm text-gray-400">Achievements</p>
              <p className="text-2xl font-bold">{dashboard?.stats?.achievements_unlocked || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-green-500/20 flex items-center justify-center">
              <span className="text-green-400 font-bold">%</span>
            </div>
            <div>
              <p className="text-sm text-gray-400">Completion</p>
              <p className="text-2xl font-bold">{(dashboard?.stats?.completion_rate || 0).toFixed(1)}%</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most Played Games */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Most Played Games</h2>
          <div className="space-y-3">
            {(dashboard?.top_played_games || []).slice(0, 5).map((item, index) => (
              <div key={index} className="flex items-center gap-3">
                <span className="text-gray-500 w-6 text-center">{index + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="truncate">{item.game.name}</p>
                  <p className="text-sm text-gray-400">
                    {(item.playtime_forever / 60).toFixed(1)} hours
                  </p>
                </div>
                <div className="w-24 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-steam-blue h-2 rounded-full"
                    style={{
                      width: `${Math.min(100, (item.playtime_forever / (dashboard?.top_played_games[0]?.playtime_forever || 1)) * 100)}%`
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Playtime by Genre */}
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Playtime by Genre</h2>
          {genreData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={genreData.slice(0, 8)}
                  dataKey="total_playtime_hours"
                  nameKey="genre"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ genre, percent }) => `${genre} (${(percent * 100).toFixed(0)}%)`}
                >
                  {genreData.slice(0, 8).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-12">No genre data available</p>
          )}
        </div>
      </div>

      {/* Yearly/Monthly Stats */}
      {(yearlyStats.length > 0 || monthlyStats.length > 0) && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">📅 Évolution du Temps de Jeu</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('yearly')}
                className={`px-4 py-2 rounded transition-colors ${
                  viewMode === 'yearly'
                    ? 'bg-steam-blue text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                Annuel
              </button>
              <button
                onClick={() => setViewMode('monthly')}
                className={`px-4 py-2 rounded transition-colors ${
                  viewMode === 'monthly'
                    ? 'bg-steam-blue text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                Mensuel
              </button>
              {viewMode === 'monthly' && (
                <select
                  value={selectedStatsYear}
                  onChange={(e) => {
                    const year = Number(e.target.value)
                    setSelectedStatsYear(year)
                    loadMonthlyStats(year)
                  }}
                  className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map(year => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Yearly View */}
          {viewMode === 'yearly' && yearlyStats.length > 0 && (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={yearlyStats}>
                  <XAxis dataKey="year" tick={{ fill: '#9ca3af' }} />
                  <YAxis tick={{ fill: '#9ca3af' }} label={{ value: 'Heures', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
                  <Tooltip
                    contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                    formatter={(value: number) => [`${value.toFixed(0)} h`, 'Temps de jeu']}
                  />
                  <Bar dataKey="total_playtime_hours" fill="#66C0F4" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {yearlyStats.map((stat) => (
                  <div key={stat.year} className="border border-gray-700 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-lg font-bold text-steam-blue">{stat.year}</h3>
                      <span className="text-2xl font-bold">{stat.total_playtime_hours.toFixed(0)}h</span>
                    </div>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between text-gray-400">
                        <span>Jeux joués:</span>
                        <span className="font-semibold text-white">{stat.games_played_count}</span>
                      </div>
                      <div className="flex justify-between text-gray-400">
                        <span>Nouveaux jeux:</span>
                        <span className="font-semibold text-green-400">{stat.new_games_count}</span>
                      </div>
                      {stat.most_played_game && (
                        <div className="mt-2 pt-2 border-t border-gray-700">
                          <p className="text-xs text-gray-500 mb-1">Jeu le plus joué:</p>
                          <p className="text-sm font-medium truncate">{stat.most_played_game.name}</p>
                          <p className="text-xs text-steam-blue">{stat.most_played_game.playtime_hours}h</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Monthly View */}
          {viewMode === 'monthly' && monthlyStats.length > 0 && (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={monthlyStats.slice().reverse()}>
                  <XAxis dataKey="month_name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#9ca3af' }} label={{ value: 'Heures', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
                  <Tooltip
                    contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                    formatter={(value: number) => [`${value.toFixed(0)} h`, 'Temps de jeu']}
                  />
                  <Bar dataKey="total_playtime_hours" fill="#4ECDC4" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {monthlyStats.map((stat) => (
                  <div key={`${stat.year}-${stat.month}`} className="border border-gray-700 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-sm font-bold text-green-400">{stat.month_name}</h3>
                      <span className="text-xl font-bold">{stat.total_playtime_hours.toFixed(0)}h</span>
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between text-gray-400">
                        <span>Jeux joués:</span>
                        <span className="font-semibold text-white">{stat.games_played_count}</span>
                      </div>
                      <div className="flex justify-between text-gray-400">
                        <span>Nouveaux:</span>
                        <span className="font-semibold text-green-400">{stat.new_games_count}</span>
                      </div>
                      {stat.most_played_game && (
                        <div className="mt-2 pt-2 border-t border-gray-700">
                          <p className="text-xs text-gray-500 mb-1">Plus joué:</p>
                          <p className="text-xs font-medium truncate" title={stat.most_played_game.name}>
                            {stat.most_played_game.name}
                          </p>
                          <p className="text-xs text-green-400">{stat.most_played_game.playtime_hours}h</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* No data message */}
          {viewMode === 'monthly' && monthlyStats.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400 mb-2">Aucune donnée mensuelle disponible pour {selectedStatsYear}</p>
              <p className="text-sm text-gray-500">Créez des snapshots et calculez les stats depuis la page Admin</p>
            </div>
          )}
        </div>
      )}

      {/* Games List */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Game Library ({games.length} games)</h2>
          <div className="flex gap-2">
            <button
              onClick={() => handleSort('playtime')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                sortBy === 'playtime'
                  ? 'bg-steam-blue text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Total Playtime <SortIcon column="playtime" />
            </button>
            <button
              onClick={() => handleSort('recent')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                sortBy === 'recent'
                  ? 'bg-steam-blue text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Last 2 Weeks <SortIcon column="recent" />
            </button>
            <button
              onClick={() => handleSort('name')}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                sortBy === 'name'
                  ? 'bg-steam-blue text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Name <SortIcon column="name" />
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Game</th>
                <th 
                  className="pb-3 font-medium text-right cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('playtime')}
                >
                  Total Playtime <SortIcon column="playtime" />
                </th>
                <th 
                  className="pb-3 font-medium text-right cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('recent')}
                >
                  Last 2 Weeks <SortIcon column="recent" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedGames.map((item) => (
                <tr key={item.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      {item.game.app_id && (
                        <img
                          src={item.game.header_image || `https://cdn.cloudflare.steamstatic.com/steam/apps/${item.game.app_id}/header.jpg`}
                          alt={item.game.name}
                          className="w-16 h-8 object-cover rounded"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none'
                          }}
                        />
                      )}
                      <span className="truncate">{item.game.name}</span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-gray-300">
                    {(item.playtime_forever / 60).toFixed(1)} hrs
                  </td>
                  <td className="py-3 text-right text-gray-400">
                    {item.playtime_2weeks > 0
                      ? `${(item.playtime_2weeks / 60).toFixed(1)} hrs`
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Playtime Equivalences Modal */}
      {showPlaytimeModal && (
        <div 
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setShowPlaytimeModal(false)}
        >
          <div 
            className="bg-gray-800 rounded-lg p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-yellow-400 mb-2">🎮 Temps de Jeu Total</h2>
                <p className="text-4xl font-bold text-white">{(dashboard?.stats?.total_playtime_hours || 0).toFixed(0)} heures</p>
              </div>
              <button 
                onClick={() => setShowPlaytimeModal(false)}
                className="text-gray-400 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-purple-400 mb-3">📚 Si tu avais étudié à la place...</h3>
                <ul className="space-y-2 text-gray-300">
                  <li>• Tu aurais pu apprendre <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 20)}</span> nouvelles langues (20h par langue)</li>
                  <li>• Ou obtenir <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 100)}</span> certificats professionnels (100h chacun)</li>
                  <li>• Ou lire environ <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 8)}</span> livres (8h par livre)</li>
                </ul>
              </div>

              <div className="bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-blue-400 mb-3">🌍 Équivalents voyage...</h3>
                <ul className="space-y-2 text-gray-300">
                  <li>• Tu aurais pu faire <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 24)}</span> tours du monde en avion (24h par tour)</li>
                  <li>• Ou regarder le lever du soleil <span className="font-bold text-white">{(dashboard?.stats?.total_playtime_hours || 0).toFixed(0)}</span> fois</li>
                  <li>• Ou marcher de Paris à Marseille <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 140)}</span> fois (140h de marche)</li>
                </ul>
              </div>

              <div className="bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-green-400 mb-3">💪 Si tu avais fait du sport...</h3>
                <ul className="space-y-2 text-gray-300">
                  <li>• Tu aurais couru environ <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) * 10)}</span> km (10 km/h)</li>
                  <li>• Ou brûlé <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) * 500).toLocaleString()}</span> calories (500 cal/h)</li>
                  <li>• Ou fait <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) * 600).toLocaleString()}</span> pompes (600 par heure)</li>
                </ul>
              </div>

              <div className="bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-red-400 mb-3">🎬 Équivalents divertissement...</h3>
                <ul className="space-y-2 text-gray-300">
                  <li>• Tu aurais pu regarder <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 2)}</span> films entiers (2h par film)</li>
                  <li>• Ou <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 0.75)}</span> épisodes de série (45 min par épisode)</li>
                  <li>• Ou écouter l'intégrale de Beethoven <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 80)}</span> fois (80h)</li>
                </ul>
              </div>

              <div className="bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-orange-400 mb-3">😴 Temps de sommeil...</h3>
                <ul className="space-y-2 text-gray-300">
                  <li>• C'est l'équivalent de <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 8)}</span> nuits de sommeil (8h par nuit)</li>
                  <li>• Soit <span className="font-bold text-white">{Math.floor((dashboard?.stats?.total_playtime_hours || 0) / 24)}</span> jours complets sans interruption</li>
                  <li>• Ou <span className="font-bold text-white">{((dashboard?.stats?.total_playtime_hours || 0) / 24 / 365).toFixed(2)}</span> années de ta vie</li>
                </ul>
              </div>

              <div className="bg-gradient-to-r from-purple-600/30 to-pink-600/30 rounded-lg p-4 border border-purple-500/50">
                <p className="text-center text-lg text-gray-200">
                  <span className="font-bold text-white">Mais bon...</span> le plaisir que tu as eu n'a pas de prix ! 🎮✨
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
