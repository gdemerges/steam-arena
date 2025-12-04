'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getGroup,
  getGroupComparison,
  getGameIntersection,
  syncGroupUsers,
  removeGroupMember,
  GroupDetail,
} from '@/lib/api'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  UserMinusIcon,
  TrophyIcon,
  ClockIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface GameIntersection {
  game_id: string
  app_id: number
  name: string
  owner_count: number
  owners: string[]
  total_playtime: number
  avg_playtime: number
}

interface UserComparison {
  steam_id: string
  persona_name: string
  avatar_url: string
  total_games: number
  total_playtime: number
  total_achievements: number
  games_played: number
}

export default function GroupDetailPage() {
  const params = useParams()
  const groupId = params.id as string

  const [group, setGroup] = useState<GroupDetail | null>(null)
  const [comparison, setComparison] = useState<UserComparison[]>([])
  const [intersection, setIntersection] = useState<GameIntersection[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [activeTab, setActiveTab] = useState<'comparison' | 'intersection'>('comparison')

  const loadData = async () => {
    setLoading(true)
    try {
      const [groupRes, comparisonRes, intersectionRes] = await Promise.all([
        getGroup(groupId),
        getGroupComparison(groupId),
        getGameIntersection(groupId),
      ])
      setGroup(groupRes.data)
      setComparison(comparisonRes.data)
      setIntersection(intersectionRes.data)
    } catch (error) {
      console.error('Failed to load group data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [groupId])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncGroupUsers(groupId)
      await loadData()
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    if (!confirm('Remove this member from the group?')) return
    try {
      await removeGroupMember(groupId, userId)
      await loadData()
    } catch (error) {
      console.error('Failed to remove member:', error)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="card animate-pulse">
          <div className="h-8 bg-gray-700 rounded w-1/3 mb-3"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  if (!group) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">Group not found</p>
        <Link href="/groups" className="btn-primary mt-4 inline-block">
          Back to Groups
        </Link>
      </div>
    )
  }

  const playtimeChartData = comparison.map(u => ({
    name: u.persona_name,
    playtime: Math.round(u.total_playtime / 60),
  }))

  const gamesChartData = comparison.map(u => ({
    name: u.persona_name,
    total: u.total_games,
    played: u.games_played,
  }))

  const achievementsChartData = comparison.map(u => ({
    name: u.persona_name,
    achievements: u.total_achievements,
  }))

  const gamesOwnedByAll = intersection.filter(g => g.owner_count === group.members.length)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <Link href="/groups" className="inline-flex items-center gap-2 text-gray-400 hover:text-white">
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Groups
        </Link>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-secondary flex items-center gap-2"
        >
          <ArrowPathIcon className={`h-5 w-5 ${syncing ? 'animate-spin' : ''}`} />
          Sync All
        </button>
      </div>

      {/* Group Header */}
      <div className="card">
        <h1 className="text-3xl font-bold">{group.name}</h1>
        {group.description && (
          <p className="text-gray-400 mt-2">{group.description}</p>
        )}
        <p className="text-sm text-gray-500 mt-2">
          {group.members.length} member{group.members.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Members */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Members</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {group.members.map((member) => (
            <div key={member.id} className="text-center group relative">
              <Link href={`/users/${member.steam_user.id}`}>
                <img
                  src={member.steam_user.avatar_full_url || member.steam_user.avatar_url || '/default-avatar.png'}
                  alt={member.steam_user.persona_name}
                  className="w-16 h-16 rounded-full mx-auto"
                />
                <p className="text-sm mt-2 truncate">{member.steam_user.persona_name}</p>
              </Link>
              <button
                onClick={() => handleRemoveMember(member.steam_user.id)}
                className="absolute top-0 right-0 p-1 bg-red-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <UserMinusIcon className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('comparison')}
          className={`px-4 py-2 font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'comparison'
              ? 'border-steam-blue text-steam-blue'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Comparison
        </button>
        <button
          onClick={() => setActiveTab('intersection')}
          className={`px-4 py-2 font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'intersection'
              ? 'border-steam-blue text-steam-blue'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Game Intersection
        </button>
      </div>

      {activeTab === 'comparison' ? (
        <div className="space-y-6">
          {/* Playtime Comparison */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <ClockIcon className="h-5 w-5 text-yellow-400" />
              <h2 className="text-xl font-semibold">Playtime Comparison (hours)</h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={playtimeChartData}>
                <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} />
                <YAxis tick={{ fill: '#9ca3af' }} />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
                <Bar dataKey="playtime" fill="#66C0F4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Games Owned */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Squares2X2Icon className="h-5 w-5 text-purple-400" />
              <h2 className="text-xl font-semibold">Games Comparison</h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={gamesChartData}>
                <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} />
                <YAxis tick={{ fill: '#9ca3af' }} />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
                <Legend />
                <Bar dataKey="total" name="Total Games" fill="#a855f7" radius={[4, 4, 0, 0]} />
                <Bar dataKey="played" name="Played" fill="#4ade80" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Achievements */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <TrophyIcon className="h-5 w-5 text-orange-400" />
              <h2 className="text-xl font-semibold">Achievements Comparison</h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={achievementsChartData}>
                <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} />
                <YAxis tick={{ fill: '#9ca3af' }} />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: '8px' }}
                />
                <Bar dataKey="achievements" fill="#fb923c" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Games owned by all */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">
              🎮 Games Everyone Owns ({gamesOwnedByAll.length})
            </h2>
            {gamesOwnedByAll.length === 0 ? (
              <p className="text-gray-400 text-center py-8">
                No games are owned by all members of this group
              </p>
            ) : (
              <div className="space-y-3">
                {gamesOwnedByAll.slice(0, 20).map((game) => (
                  <div
                    key={game.game_id}
                    className="flex items-center justify-between p-3 bg-green-900/20 border border-green-700/30 rounded"
                  >
                    <div>
                      <p className="font-medium">{game.name}</p>
                      <p className="text-sm text-gray-400">
                        Total: {(game.total_playtime / 60).toFixed(0)}h • 
                        Avg: {(game.avg_playtime / 60).toFixed(0)}h per player
                      </p>
                    </div>
                    <div className="text-green-400 font-semibold">
                      {game.owner_count}/{group.members.length}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* All intersections */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">All Shared Games</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-3 font-medium">Game</th>
                    <th className="pb-3 font-medium text-center">Owners</th>
                    <th className="pb-3 font-medium text-right">Total Playtime</th>
                    <th className="pb-3 font-medium text-right">Avg Playtime</th>
                  </tr>
                </thead>
                <tbody>
                  {intersection.slice(0, 50).map((game) => (
                    <tr key={game.game_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                      <td className="py-3">{game.name}</td>
                      <td className="py-3 text-center">
                        <span className={`px-2 py-1 rounded text-sm ${
                          game.owner_count === group.members.length
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-600 text-gray-300'
                        }`}>
                          {game.owner_count}/{group.members.length}
                        </span>
                      </td>
                      <td className="py-3 text-right text-gray-300">
                        {(game.total_playtime / 60).toFixed(0)}h
                      </td>
                      <td className="py-3 text-right text-gray-400">
                        {(game.avg_playtime / 60).toFixed(0)}h
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
